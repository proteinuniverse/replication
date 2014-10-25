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


## API

Common Terms
  * file refers to the relative path of the file to be replicated, deleted, etc.  It is relative to the base directory on the source end-point.
  For example, if the base was /data and /data/file1 was being replicated, then the file would be /file1.

### status

/api/status (GET) - Gets the status of all files for the authenicated user.  No paramters.

### register

/api/register (POST) - Registers a new replication group.  Parameters: group and destinations.
   Format for destinations:  Comma seperated list of end-points of the form <alias>|<gloubus endpoint>:<path>
   Example destinations=pnnl|pic#dtn:test/,lbnl|nersc#dtn:/global/scratch2/sd/canon/test/

### mkdir

/api/mkdir (GET) - Create a new directory.  Parameter: file, source, group
   file is the pathname
   source is the alias name for the source location
   group is the replication group

### transfer
/api/transfer (POST) - Replicate a file. Parameters: file, source, size, ctime, group

### delete
/api/delete (GET) - Delete a file or directory. Parameter: file
   file is the pathname to the file to be deleted
   The other parameters are stored in mongo.

