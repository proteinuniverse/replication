
from flask import jsonify
from flask import request
from flask import Flask
from flask import g
from flask import render_template
import json
import os
import requests
import urllib
import ConfigParser
from pymongo import MongoClient
from bson.json_util import dumps

app = Flask(__name__)

test_mode=0 

config = ConfigParser.ConfigParser()
config.read('config.ini')

trans={}
basepath={}
src = config.get("globus", "source",)
source = src.split('|')[1]
transfer_api_url = config.get("globus", "api_url")

(alias,endpt)=src.split('|')
trans[alias]=endpt
trans[endpt]=alias
dsts = config.get("globus", "destinations").split(',')
destinations=[]
for dest in dsts:
  (alias,tmp)=dest.split('|')
  (endpt,base)=tmp.split(':')
  trans[alias]=endpt
  trans[endpt]=alias
  basepath[endpt]=base
  destinations.append(endpt)
  #destinations = config.get("globus", "destinations").split(',')

try:
    mongo_host = config.get("mongo", "mongo_host")
    mongo_user = config.get("mongo", "mongo_user")
    mongo_pass = config.get("mongo", "mongo_pass")
    mongo_database = config.get("mongo", "mongo_database")

    client = MongoClient(mongo_host)
    db = client[mongo_database]
    if mongo_user != '':
      db.authenticate(mongo_user, mongo_pass)
    collection = db['replication']
except Exception as e:
    print "Could not connect to Mongo DB: " + str(e)
    exit -1



def remote_makedir(dest, filepath):
    mkdir_template = """{
      "path": "%s",
      "DATA_TYPE": "mkdir"
    }"""

    if test_mode==1:
      return 1
    post_body = mkdir_template % filepath
    # This will clean up the JSON
    payload=json.dumps(json.loads(post_body))

    enc_dest = urllib.quote(dest)

    r = requests.post(transfer_api_url + '/endpoint/%s/mkdir' % enc_dest, data=payload, headers=g.headers)
    if r.status_code<200 or r.status_code>299:
        message = r.json()['message']
        raise Exception(message)
    else:
        return r.json()['message']



def replicate(source, dest, filepath):
    """
    Use the Globus Transfer API to do replication
    https://transfer.api.globusonline.org/v0.10/doc/
    """

    if test_mode==1:
      return 1
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
    r = requests.get(transfer_api_url + '/submission_id', headers=g.headers)
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
    r = requests.post(transfer_api_url + '/transfer', data=payload, headers=g.headers)

    output = r.json()
    if r.status_code < 200 or r.status_code > 299:
        raise Exception(output['message'])


    return output["task_id"]

def remote_del(dest, filepath):
    delete_template = """{
        "submission_id": "%s", 
        "endpoint": "%s", 
        "recursive": %s, 
        "DATA_TYPE": "delete", 
        "label": "%s", 
        "length": 1, 
        "ignore_missing": true, 
        "DATA": [
            {
                "path": "%s", 
                "DATA_TYPE": "delete_item"
            }
        ]
    }"""

    if test_mode==1:
      return 1
    r = requests.get(transfer_api_url + '/submission_id', headers=g.headers)
    endpoint = dest
    submission_id = r.json()['value']
    label = "SDF delete testing"
    path = os.path.basename(filepath)
    if os.path.isdir(filepath):
        recursive = "true"
    else:
        recursive = "false"

    post_body = delete_template % (submission_id, 
                                   endpoint,
                                   recursive, 
                                   label, 
                                   path)
    # This will clean up the JSON
    payload=json.dumps(json.loads(post_body))
    print "Debug: %s"%(endpoint)
    r = requests.post(transfer_api_url + '/delete', data=payload, headers=g.headers)

    output = r.json()
    if r.status_code < 200 or r.status_code > 299:
        raise Exception(output['message'])


    return output["task_id"]

def parse_token(token):
    items = token.split('|')
    header_info = {}
    for item in items:
        (key, val) = item.split('=')
        header_info[key] = val
    return header_info 


@app.before_request
def before_request():
    # Do common stuff before each request. In this case we can check for headers
    if request.path.startswith("/api"):

        if request.headers.has_key('Authorization') and request.headers['Authorization'].startswith("Globus-Goauthtoken"):
            g.headers = {"Authorization": "%s" % request.headers['Authorization'], "Content-Type": "application/json"}
            # We can also verify the header if needed
            g.token = request.headers['Authorization'].split()[1]
            g.user_info = parse_token(g.token)

        else:
            response = jsonify({"status": "ERROR", 
                            "output": "",
                            "error": "Missing Authorization headers"})
            response.status_code = 403
            return response

@app.route('/')
def status_page(name=None):
    entries = json.loads(dumps(collection.find()))
    response={}
    try:
       response=render_template('status.html', entries=entries)
       return response
    except Exception as e:
       return 'ERROR '+str(e)
    
@app.route('/api/status')
def status_json(name=None):
    return dumps(collection.find())

@app.route("/api")
def base_api():
    output = json.loads(dumps(collection.find()))
    return jsonify({"status": "OK", 
                    "name": "replicant", 
                    "version": "0.0.1", 
                    "urls": ["/transfer", "/update", "/delete", "/mkdir","/status"],
                    "output": output,
                    "error": ""})

@app.route("/api/mkdir", methods=['GET'])
def makedir():
    status = "OK"
    status_code = 200
    error = ""
    filepath = request.args.get('file', '')
    output = []

    for dest in destinations:
        try: 
            message = remote_makedir(dest, filepath)
            output.append({dest: {"status": "OK", "message": message}})
        except Exception as e:
            message = str(e)
            output.append({dest: {"status": "ERROR", "message": message}})


    
    response = jsonify({"status": "OK", 
                    "output": output,
                    "error": ""})
    response.status_code = status_code
    return response


@app.route("/api/delete", methods=['GET'])
def delete():
    # import pdb; pdb.set_trace()
    user = g.user_info['un']
    status = "OK"
    status_code = 200
    error = ""
    filepath = request.args.get('file', '')
    output = ""
    transfer_ids=[]
    spec = {"file": filepath, "user": user}

    try:
        if filepath == '':
            raise Exception("No filename supplied")
        for dest in destinations:
            dest_key = "sites." + trans[dest]
            t_id = remote_del(dest, basepath[dest]+'/'+filepath)
            transfer_ids.append((dest, t_id))
            doc = {
                "$set": {
                    dest_key:  {
                        "task_id": t_id,
                        "status": "deleting",
                    }
                }
            }
            collection.update(spec, doc, upsert=True)

    except Exception as e:
        status = "ERROR"
        error = str(e)
        status_code = 500


    response = jsonify({"status": status, 
                    "source": source + ":" + filepath, 
                    "transfer_ids": transfer_ids,
                    "output": output,
                    "error": error})
    response.status_code = status_code
    return response

def get_status(task_id):
    print "Updating for %s"%(task_id)
    if test_mode==1:
      return 'SUCCEEDED'
    r = requests.get(transfer_api_url + '/task/' + task_id, headers=g.headers)
    r_out = r.json()
    #output.append(r_out)
    if r_out['status']=='SUCCEEDED' and r_out['type']=='DELETE':
      return 'DELETED'
    return r_out['status']


@app.route("/api/update", methods=['GET'])
def update():

    user = g.user_info['un']

    status = "OK"
    status_code = 200
    error = ""
    filepath = request.args.get('file', '')
    output = []
    try:
        if filepath == '':
            raise Exception("No filename supplied")

        spec = {"file": filepath, "user": user}

        doc = collection.find_one(spec)
        if doc == None:
            raise Exception("No doc found in mongo")

        for site_name in doc['sites'].keys():
            site = doc['sites'][site_name]
            # TODO: Check other end states in Globus
            if site['task_id'] and (site['status']!='SUCCEEDED') and (site['status']!='deleted'):
                status=get_status(site['task_id'])
                dest_key = "sites." + site_name + ".status"
                update_doc = {
                    "$set": {
                        dest_key: status
                    }
                }
                collection.update(spec, update_doc, upsert=True)

    except Exception as e:
        status = "ERROR"
        error = str(e)
        status_code = 500

    response = jsonify({"status": status, 
                    "source": source + ":" + filepath,
                    "output": output,
                    "error": error})
    response.status_code = status_code
    return response


@app.route("/api/transfer", methods=['GET'])
def transfer():

    user = g.user_info['un']

    filepath = request.args.get('file', '')
    ctime = request.args.get('ctime', '')
    size = request.args.get('size', '')
    status = "OK"
    status_code = 200
    output = ""
    error = ""
    transfer_ids=[]


    try:
        if filepath == '':
            raise Exception("No filename supplied")

        #dirname = os.path.dirname(filepath)
        #filename = os.path.basename(filepath)
    
        # TODO - make this work for remote sources
        #if not os.path.exists(filepath):
        #    raise Exception("File Not Found")


        # Update Mongo entry:
        # TODO - make this work for remote sources

        #st = os.stat(filepath)
        spec = {"file": filepath, "user": user}
        doc = {
            "$set": {
                "user": user,
                "source": trans[source],
                "ctime": ctime,
                "size": size,
                "sites": {
                    trans[source]: {
                        "task_id": None,
                        "status": "source",
                    }
                }
            }
        }
        collection.update(spec, doc, upsert=True)
        # Fire off transfer(s)


        for dest in destinations:
            dest_key = "sites." + trans[dest]
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
        status_code = 500


    response = jsonify({"status": status, 
                    "source": trans[source] + ":" + filepath,
                    "destinations": destinations, 
                    "transfer_ids": transfer_ids,
                    "output": output,
                    "error": error})
    response.status_code = status_code
    return response


if __name__ == "__main__":
    app.debug = True
    app.run()
