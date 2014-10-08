## Flask REST service for file replication

## Install Requirements
```
pip install -r requirements.txt
```

## Run
```
python flask.py
```

## Test
```
curl -X GET http://127.0.0.1:5000/transfer?file=/path/to/file_or_dir
```