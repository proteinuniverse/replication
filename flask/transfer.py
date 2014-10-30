
from flask import jsonify
from flask import request
from flask import Flask
from flask import g
from flask import render_template
from flask import make_response
from flask import redirect
from flask import url_for
from flask.ext.cors import cross_origin
import json
import os
import requests
from requests.auth import HTTPBasicAuth
import urllib
import ConfigParser
import uuid
import time
from pymongo import MongoClient
from bson.json_util import dumps

app = Flask(__name__,static_url_path='/project/bigdata/demo/static')


config = ConfigParser.ConfigParser(allow_no_value=True)
config.read('config.ini')

groups={}
defgroup='default'
defsource='lbnl'

def register_group(group,list):
    groups[group]={}
    for entry in list.split(','):
        (dest,tmp)=entry.split('|')
        (ept,base)=tmp.split(':')
        groups[group][dest]={}
        groups[group][dest]['endpt']=ept
        groups[group][dest]['base']=base

# Popluate some parameters
#
transfer_api_url = config.get("globus", "api_url")
port = config.get("server", "port")
register_group(defgroup,config.get("globus", "destinations"))
test_mode=0
if config.has_option("server","test_mode"): 
     test_mode = int(config.get("server", "test_mode"))
     print "Setting Test Mode to %d"%(test_mode)

# Connect to mongo
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

def get_user():
    user_info = getattr(g, 'user_info', None)
    if user_info:
        return user_info['un']
    else:
        return None

#def remote_makedir(group,dest, filepath):
def remote_makedir(dest, filepath):
    mkdir_template = """{
      "path": "%s/%s",
      "DATA_TYPE": "mkdir"
    }"""

    if test_mode==1:
      print "Debug: "+dest
      return str(uuid.uuid4())
    post_body = mkdir_template % (dest['base'],filepath)
    # This will clean up the JSON
    payload=json.dumps(json.loads(post_body))

    enc_dest = urllib.quote(dest['endpt'])

    r = requests.post(transfer_api_url + '/endpoint/%s/mkdir' % enc_dest, data=payload, headers=g.headers)
    if r.status_code<200 or r.status_code>299:
        message = r.json()['message']
        raise Exception(message)
    else:
        return r.json()['message']



def replicate(source, dest, file):
    """
    Use the Globus Transfer API to do replication
    https://transfer.api.globusonline.org/v0.10/doc/
    """

    if test_mode==1:
      return str(uuid.uuid4())
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
    source_endpoint = source['endpt']
    label = "SDF replication testing"
    destination_endpoint = dest['endpt']
    source_path = "%s/%s"%(source['base'],file)
    destination_path = "%s/%s"%(dest['base'],file)
    recursive = "false"
    #if os.path.isdir(filepath):
    #    recursive = "true"

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
      return str(uuid.uuid4())
    r = requests.get(transfer_api_url + '/submission_id', headers=g.headers)
    endpoint = dest['endpt']
    submission_id = r.json()['value']
    label = "SDF delete testing"
    recursive="false"
    path = dest['base']+filepath
    #if os.path.isdir(filepath):
    #    recursive = "true"

    post_body = delete_template % (submission_id, 
                                   endpoint,
                                   recursive, 
                                   label, 
                                   path)
    # This will clean up the JSON
    payload=json.dumps(json.loads(post_body))
    r = requests.post(transfer_api_url + '/delete', data=payload, headers=g.headers)

    output = r.json()
    if r.status_code < 200 or r.status_code > 299:
        raise Exception(output['message'])


    return output["task_id"]

def update_all():
    for doc in collection.find({'status':{ '$ne': 'COMPLETED'}}):
        # Do update
        print "Updating "+doc['file']
        newstatus="COMPLETED"
        for site_name in doc['sites'].keys():
            site = doc['sites'][site_name]
            if 'status' not in site:
                continue
            if 'task_id' in site and site['task_id'] and (site['status']!='SUCCEEDED') and (site['status']!='deleted'):
                status=get_status(site['task_id'])
                dest_key = "sites." + site_name + ".status"
                site['status']=status
                update_doc = {
                    "$set": {
                        dest_key: status
                    }
                }
                collection.update({'_id':doc['_id']}, update_doc, upsert=True)
            if (site['status'] != 'SUCCEEDED') and (site['status'].upper()!='DELETED' and (site['status'].upper()!='SOURCE')):
                print site['status']
                newstatus='INPROGRESS'
        print doc['file']+' '+newstatus
        update_doc = {
            "$set": {
                'status': newstatus
            }
        }
        collection.update({'_id':doc['_id']}, update_doc, upsert=True)
   
def parse_token(token):
    items = token.split('|')
    header_info = {}
    for item in items:
        (key, val) = item.split('=')
        header_info[key] = val
    return header_info 

def authenticate(username, password):
    globus_auth_url = 'https://nexus.api.globusonline.org/goauth/token?grant_type=client_credentials'
    r = requests.get(globus_auth_url, auth=HTTPBasicAuth(username, password))
    if r.status_code >= 200 and r.status_code <=299:
        return r.json()['access_token']
    else:
        return None

@app.before_request
def before_request():
    # Do common stuff before each request. In this case we can check for headers
    g.authenticated = False
    auth_header = request.headers.get("Authorization") or request.cookies.get("Authorization")
    if auth_header and auth_header.startswith("Globus-Goauthtoken"):
        g.headers = {"Authorization": "%s" % auth_header, "Content-Type": "application/json"}
        # We can also verify the header if needed
        g.token = auth_header.split()[1]
        g.user_info = parse_token(g.token)
        g.authenticated = True

    if request.path.startswith("/api") and not g.authenticated:
        response = jsonify({"status": "ERROR", 
                        "output": "",
                        "error": "Missing Authorization headers"})
        response.status_code = 403
        return response

@app.route('/',methods=['GET'])
def status_page(name=None):
    entries = json.loads(dumps(collection.find()))
    response={}
    try:
       #update_all()
       response=render_template('status.html', entries=entries, username=get_user())
       return response
    except Exception as e:
       return 'ERROR '+str(e)

@app.route('/login',methods=['GET', 'POST'])
def login():
    error = None
    headers = None
    if request.method == 'POST':
        token = authenticate(request.form['username'],
                             request.form['password'])
        if token:    
            response = redirect(url_for('status_page'))
            response.set_cookie('Authorization', 'Globus-Goauthtoken %s' % token)
            return response
        else:
            error = 'Invalid username/password'
    # the code below is executed if the request method
    # was GET or the credentials were invalid
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    response = redirect(url_for('status_page'))
    response.set_cookie('Authorization', expires=0)
    return response

    
@app.route('/api/status', methods=['GET'])
def status_json(name=None):
    user = get_user()
    update_all()
    return dumps(collection.find({'user':user}))

@app.route('/statusall', methods=['GET'])
@cross_origin() # allow all origins all methods.
def status_jsonall(name=None):
    #update_all()
    return dumps(collection.find({}))

@app.route("/api", methods=['GET'])
def base_api():
    output = json.loads(dumps(collection.find()))
    return jsonify({"status": "OK", 
                    "name": "replicant", 
                    "version": "0.0.1", 
                    "urls": ["/transfer", "/update", "/delete", "/mkdir","/status","/register"],
                    "output": output,
                    "error": ""})

@app.route("/api/register", methods=['GET','POST'])
def register():
    status = "OK"
    status_code = 200
    error = ""
    group = request.args.get('group', '')
    output = []
    destinations = ""
    user = get_user()

# TODO: Only return the user's groups
    if request.method=='GET':
         return jsonify(groups)
       

    try: 
        if group == '':
            raise Exception("No group supplied")
        group="%s:%s"%(user,str(group))
        if 'destinations' not in request.form:
            raise Exception("No destinations list supplied")
        destinations = str(request.form['destinations'])
        register_group(group,destinations)
    except Exception as e:
        message = str(e)
        output.append({"status": "ERROR", "message": message})


    
    response = jsonify({"status": "OK", 
                    "group": group,
                    "destinations": destinations,
                    "output": output,
                    "error": ""})
    response.status_code = status_code
    return response

@app.route("/api/mkdir", methods=['GET'])
def makedir():
    user = get_user()
    status = "OK"
    status_code = 200
    error = ""
    filepath = request.args.get('file', '')
    source = request.args.get('source', '')
    ctime = request.args.get('ctime', '')
    group = request.args.get('group', defgroup)
    output = []

    if (group != defgroup):
        group="%s:%s"%(user,str(group))
    destinations=groups[group].keys()

    for dest in destinations:
        if dest == source:
          continue
        try: 
            dst = groups[group][dest]
            message = remote_makedir(dst,filepath)
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
    user = get_user()
    status = "OK"
    status_code = 200
    error = ""
    filepath = request.args.get('file', '')
    output = ""
    source = ""
    transfer_ids=[]
    spec = {"file": filepath, "user": user}

    try:
        if filepath == '':
            raise Exception("No filename supplied")
        spec = {"file": filepath, "user": user}

        entry = collection.find_one(spec)
        if entry==None:
           raise Exception("Invalid filename supplied")
        source = entry['source']
        if 'replgroup' in entry:
            group=entry['replgroup']
        else:
             group=defgroup
        destinations=groups[group].keys()
        for dest in destinations:
            if source == dest:
                continue
            dest_key = "sites." + dest
            dst = groups[group][dest]
            t_id = remote_del(dst, filepath)
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

    user = get_user()

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

        newstatus='COMPLETE'
        for site_name in doc['sites'].keys():
            site = doc['sites'][site_name]
            # TODO: Check other end states in Globus
            if site['task_id'] and (site['status']!='SUCCEEDED') and (site['status']!='deleted'):
                status=get_status(site['task_id'])
                dest_key = "sites." + site_name + ".status"
                if status!='SUCCESS':
                    newstatus="INPROGRESS" 
                update_doc = {
                    "$set": {
                        dest_key: status
                    }
                }
                collection.update(spec, update_doc, upsert=True)
        update_doc = {
            "$set": {
                status: newstatus
            }
        }
        collection.update(spec, update_doc, upsert=True)

    except Exception as e:
        status = "ERROR"
        error = str(e)
        status_code = 500

    response = jsonify({"status": status, 
                    "file": filepath,
                    "output": output,
                    "error": error})
    response.status_code = status_code
    return response


@app.route("/api/transfer", methods=['POST'])
def transfer():

    user = get_user()

    filepath = request.args.get('file', '')
    ctime = request.args.get('ctime', '')
    size = request.args.get('size', '')
    source = request.args.get('source', defsource)
    group = request.args.get('group', defgroup)
    status = "OK"
    status_code = 200
    output = ""
    error = ""
    destinations = ""
    transfer_ids=[]

    try:
        if (group != defgroup):
            group="%s:%s"%(user,str(group))

        if group not in groups:
            raise Exception("Group not recognized")
        destinations=groups[group].keys()

        if filepath == '':
            raise Exception("No filename supplied")

        if source == '':
            raise Exception("No source supplied")

        if source not in destinations:
            raise Exception("Source not recognized")


        # Update Mongo entry:
        spec = {"file": filepath, "user": user}
        doc = {
            "$set": {
                "user": user,
                "source": source,
                "ctime": ctime,
                "size": size,
                "replgroup": group,
                "status": 'INPROGRESS',
                "sites": {
                    source: {
                        "task_id": None,
                        "status": "SOURCE",
                    }
                }
            }
        }
        collection.update(spec, doc, upsert=True)
        # Fire off transfer(s)

        for dest in destinations:
            if source == dest:
              continue
            dest_key = "sites." + dest
            try:
                src=groups[group][source] 
                dst=groups[group][dest] 
                t_id = replicate(src, dst, filepath)
                
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
                print "Debug transfer: "+str(e)
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
                    "source": source + ":" + filepath,
                    "destinations": destinations, 
                    "transfer_ids": transfer_ids,
                    "output": output,
                    "error": error})
    response.status_code = status_code
    return response

if __name__ == "__main__":
    app.debug = True
    app.run(port=int(port))
