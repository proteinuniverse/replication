#!/bin/sh

PID=/global/scratch2/sd/canon/lsyncd.pid

kill $(cat $PID)

lsyncd ./lrepl.lua
