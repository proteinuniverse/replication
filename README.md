replication
===========

Data Replication Infrastructure Demo


Dependencies
============

This makes use of:
* GlobusOnline
* Lsyncd (https://code.google.com/p/lsyncd/).  
* MongoDB

Before using, you will need to modify config.ini to specify the mongo login information
and specify the various GO endpoints.  You will also need to make sure you have authorized
the various end points and configured globus to use an ssh key.  Finally, you will need to
modify lrepl.lua to specify which directory to watch and the location of the transfer scripts.

Usage 
=====

lsyncd ./lrepl.lua

Then create files in the watch directory.
