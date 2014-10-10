## Flask REST service for file replication

## Install Requirements
```
pip install -r requirements.txt
```

## Run
```
python transfer.py
```

## Test
```
# Get the Token from globus oauth API as follows:
#

curl --user your_globus_username 'https://nexus.api.globusonline.org/goauth/token?grant_type=client_credentials'
#
# (From the output JSON grab the 'access_token' field)

export TOKEN=<your_access_token>

curl -H "Authorization: Globus-Goauthtoken $TOKEN" -X GET http://127.0.0.1:5000/transfer?file=/path/to/file_or_dir

curl -H "Authorization: Globus-Goauthtoken $TOKEN" -X GET http://127.0.0.1:5000/update?file=/path/to/file_or_dir

curl -H "Authorization: Globus-Goauthtoken $TOKEN" -X GET http://127.0.0.1:5000/delete?file=/path/to/file_or_dir

curl -H "Authorization: Globus-Goauthtoken $TOKEN" -X GET http://127.0.0.1:5000/
```