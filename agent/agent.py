#!/usr/bin/env python

import json
import os
import requests
import urllib
import ConfigParser
import time
import sys
from bson.json_util import dumps
import pyinotify
from multiprocessing import Process

config = ConfigParser.ConfigParser()
config.read('config.ini')

url = config.get("repl", "api-url")
base = config.get("agent", "base")
group = config.get("agent", "group")
source = config.get("agent", "source")
header={'Authorization':''}

wm = pyinotify.WatchManager()  # Watch Manager
mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE | pyinotify.IN_CLOSE_WRITE  # watched events

def transfer(file):
     try:
         st=os.stat(base+file)
         r = requests.post(url + 'transfer?file=%s&source=%s&group=%s&size=%s&ctime=%s' % (file,source,group,st.st_size,st.st_ctime), headers=header) 
         print dumps(r.json(),indent=2)
     except Exception as e:
         print str(e)

def rmkdir(file):
     try:
         st=os.stat(base+file)
         r = requests.get(url + 'mkdir?file=%s&source=%s&group=%s&ctime=%s' % (file,source,group,st.st_ctime), headers=header) 
         print dumps(r.json(),indent=2)
     except Exception as e:
         print str(e)

def delete(file):
     try:
         r = requests.get(url + 'delete?file=%s&source=%s&group=%s' % (file,source,group), headers=header)
         print dumps(r.json(),indent=2)
     except Exception as e:
         print str(e)
     

def status():
     r = requests.get(url + 'status' , headers=header) 
     print dumps(r.json(),indent=2)

# inotify handler
#
class EventHandler(pyinotify.ProcessEvent):
    def process_IN_CLOSE_WRITE(self, event):
        file=event.pathname.replace(base,'')
        print "Close Write:", file
        transfer(file)

    def process_IN_CREATE(self, event):
        if event.dir == True:
          wm.add_watch(event.pathname, mask, rec=True)
          dir=event.pathname.replace(base,'')
          print "Mkdir:", dir 
          rmkdir(dir)

    def process_IN_DELETE(self, event):
        file=event.pathname.replace(base,'')
        print "Removing:", file
        delete(file)

def update():
    while True:
       status()
       time.sleep(60)


if __name__ == "__main__":
#    args=sys.argv[1:]
#    if len(args)>1 and args[0]=='transfer':
#        transfer(args[1])
#    if len(args)>1 and args[0]=='delete':
#        delete(args[1])
#    if len(args)>0 and args[0]=='status':
#        status()
    tok=open(os.getenv("HOME")+"/.repl_token")
    token=tok.read()
    header['Authorization']='Globus-Goauthtoken '+token
    p = Process(target=update)
    p.start()
    handler = EventHandler()
    notifier = pyinotify.Notifier(wm, handler)

    for root, dirnames, filenames in os.walk(base):
        print root
        wdd = wm.add_watch(root, mask, rec=True)

    notifier.loop()
