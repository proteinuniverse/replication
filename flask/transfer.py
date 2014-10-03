
from flask import Flask
from flask import jsonify
from flask import request
import os
import requests
import urllib

app = Flask(__name__)

 

# TODO: parse config
source = "shreyas#laptop"
destinations = [ "nersc#pdsf", "nersc#dtn" ]
transfer_api_url = "https://transfer.api.globusonline.org/v0.10"
token = ""

transfer_template="""{
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
    headers={"Authorization": "Globus-Goauthtoken %s" % token}
    r = requests.get(transfer_api_url+'/submission_id', headers=headers)
    # TODO: output validation 
    submission_id = r.json()['value']
    source_endpoint = source
    label = "SDF replication testing"
    destination_endpoint = dest
    source_path = filepath
    destination_path = os.path.basename(filepath)
    if os.path.isdir(filepath):
        recursive = "false"
    else
        recursive = "true"

    post_body = transfer_template % (submission_id, 
                                     source_endpoint, 
                                     label, 
                                     destination_endpoint,
                                     source_path,
                                     destination_path,
                                     recursive)
    # This will clean up the JSON
    payload=json.dumps(json.loads(post_body))
    r = requests.post(transfer_api_url + '/transfer', data=, headers=headers)

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

    try:
        if filepath == '':
            raise Exception("No filename supplied")

        dirname = os.path.dirname(filepath)
        filename = os.path.basename(filepath)
    
        if os.path.exists(filepath):
            output = "Replicating file"
        else:
            raise Exception("File Not Found")
        # Fire off transfer(s)

    transfer_ids = []

    for dest in destinations:
        t_id = replicate(source, dest, filepath)
        transfer_ids.append(t_id) 

    except Exception, e:
        status = "ERROR"
        error = str(e)



    return jsonify({"status": status, 
                    "source": source + ":" + filepath,
                    "destinations": destinations, 
                    "transfer_ids": transfer_ids,
                    "output": output,
                    "error": error})


@app.route("/delete", methods=['GET'])
def delete():



if __name__ == "__main__":
    app.debug = True
    app.run()