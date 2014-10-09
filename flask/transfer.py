
from flask import jsonify
from flask import request
from flask import Flask
import json
import os
import requests
import urllib
import ConfigParser
from pymongo import MongoClient

app = Flask(__name__)

 

config = ConfigParser.ConfigParser()
config.read('config.ini')

token = config.get("globus", "access_token")

headers = {"Authorization": "Globus-Goauthtoken %s" % token, "Content-Type": "application/json"}


source = config.get("globus", "source",)
transfer_api_url = config.get("globus", "api_url")
destinations = config.get("globus", "destinations").split(',')

try:
    mongo_host = config.get("mongo", "mongo_host")
    mongo_user = config.get("mongo", "mongo_user")
    mongo_pass = config.get("mongo", "mongo_pass")
    mongo_database = config.get("mongo", "mongo_database")

    client = MongoClient(mongo_host)
    db = client[mongo_database]
    db.authenticate(mongo_user, mongo_pass)
    collection = db['replication']
except Exception as e:
    print "Could not connect to Mongo DB: " + str(e)
    exit -1

# TODO: Automate cred generation

# Get the Token from globus oauth API as follows:
#
# curl --user your_globus_username 'https://nexus.api.globusonline.org/goauth/token?grant_type=client_credentials'
#
# (From the output JSON grab the 'access_token' field)
transfer_template = """{
  "submission_id": "%s", 
  "DATA_TYPE": "transfer", 
  "sync_level": null, 
  "source_endpoint": "%s", 
  "label": "%s", 
  "length": 1, 
  "destination_endpoint": "%s", 
  "DATA": [
    {
      "source_path": "%s", 
      "destination_path": "%s", 
      "verify_size": null, 
      "recursive": %s, 
      "DATA_TYPE": "transfer_item"
    }

  ]
}"""


def replicate(source, dest, filepath):
    """
    Use the Globus Transfer API to do replication
    https://transfer.api.globusonline.org/v0.10/doc/
    """
    # import pdb; pdb.set_trace()
    r = requests.get(transfer_api_url + '/submission_id', headers=headers)
    # TODO: output validation 
    submission_id = r.json()['value']
    source_endpoint = source
    label = "SDF replication testing"
    destination_endpoint = dest
    source_path = filepath
    destination_path = os.path.basename(filepath)
    if os.path.isdir(filepath):
        recursive = "true"
    else:
        recursive = "false"

    post_body = transfer_template % (submission_id, 
                                     source_endpoint, 
                                     label, 
                                     destination_endpoint,
                                     source_path,
                                     destination_path,
                                     recursive)
    # This will clean up the JSON
    payload=json.dumps(json.loads(post_body))
    r = requests.post(transfer_api_url + '/transfer', data=payload, headers=headers)

    output = r.json()
    if r.status_code < 200 or r.status_code > 299:
        raise Exception(output['message'])


    return output["task_id"]

@app.route("/")
def base():
    return jsonify({"status": "OK", 
                    "name": "replicant", 
                    "version": "0.0.1", 
                    "urls": ["/transfer"],
                    "output": "",
                    "error": ""})

@app.route("/update", methods=['GET'])
def update():
    import pdb; pdb.set_trace()
    status = "OK"
    error = ""
    filepath = request.args.get('file', '')
    output = []
    try:
        if filepath == '':
            raise Exception("No filename supplied")

        spec = {"file": filepath}

        doc = collection.find_one(spec)
        if doc == None:
            raise Exception("No doc found in mongo")

        for site_name in doc['sites'].keys():
            site = doc['sites'][site_name]
            # TODO: Check other end states in Globus
            if site['task_id'] and (site['status']!='SUCCEEDED'):
                r = requests.get(transfer_api_url + '/task/' + site['task_id'], headers=headers)
                r_out = r.json()
                output.append(r_out)
                dest_key = "sites." + site_name + ".status"
                update_doc = {
                    "$set": {
                        dest_key: r_out['status']
                    }
                }
                collection.update(spec, update_doc, upsert=True)

    except Exception as e:
        status = "ERROR"
        error = str(e)

    return jsonify({"status": status, 
                    "source": source + ":" + filepath,
                    "output": output,
                    "error": error})



@app.route("/transfer", methods=['GET'])
def transfer():
    filepath = request.args.get('file', '')
    status = "OK"
    output = ""
    error = ""
    transfer_ids=[]


    try:
        if filepath == '':
            raise Exception("No filename supplied")

        dirname = os.path.dirname(filepath)
        filename = os.path.basename(filepath)
    
        if not os.path.exists(filepath):
            raise Exception("File Not Found")


        # Update Mongo entry:
        st = os.stat(filepath)
        spec = {"file": filepath}
        doc = {
            "$set": {
                "source": source,
                "ctime": st.st_ctime,
                "size": st.st_size,
                "sites": {
                    source: {
                        "task_id": None,
                        "status": "source",
                    }
                }
            }
        }
        collection.update(spec, doc, upsert=True)
        # Fire off transfer(s)


        for dest in destinations:
            dest_key = "sites." + dest
            try:

                t_id = replicate(source, dest, filepath)
                
                doc = {
                    "$set": {
                        dest_key:  {
                            "task_id": t_id,
                            "status": "started",
                        }
                    }
                }
                collection.update(spec, doc, upsert=True)
            except Exception as e:
                # log message
                print str(e)
                t_id = None
                doc = {
                    "$set": {
                        dest_key:  {
                            "task_id": None,
                            "status": "failed",
                        }
                    }
                }
                collection.update(spec, doc, upsert=True)
            transfer_ids.append((dest, t_id))

        output = "Transfer submitted"

    except Exception as e:
        status = "ERROR"
        error = str(e)



    return jsonify({"status": status, 
                    "source": source + ":" + filepath,
                    "destinations": destinations, 
                    "transfer_ids": transfer_ids,
                    "output": output,
                    "error": error})



if __name__ == "__main__":
    app.debug = True
    app.run()