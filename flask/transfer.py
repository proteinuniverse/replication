
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
source = config.get("globus", "source",)
transfer_api_url = config.get("globus", "api_url")

# TODO: parse dest from config
destinations = config.get("globus", "destinations").split(',')
mongo_host = config.get("mongo", "mongo_host")
mongo_user = config.get("mongo", "mongo_user")
mongo_pass = config.get("mongo", "mongo_pass")
mongo_database = config.get("mongo", "mongo_database")

# Don't use special chars in password with this syntax - URIs arent happy.
mongo_uri = "mongodb://%s:%s@%s/%s" % (mongo_user, mongo_pass, mongo_host, mongo_database)

client = MongoClient(uri)


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
    headers={"Authorization": "Globus-Goauthtoken %s" % token, "Content-Type": "application/json"}
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
        # Fire off transfer(s)


        for dest in destinations:
            try:
                t_id = replicate(source, dest, filepath)
            except Exception as e:
                # log message
                print str(e)
                t_id = None
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