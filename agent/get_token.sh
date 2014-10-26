#!/bin/sh

TOKEN=$( curl --user scanon  'https://nexus.api.globusonline.org/goauth/token?grant_type=client_credentials' |sed 's/.*\"access_token\": \"//'|sed 's/\".*//')

echo $TOKEN > ~/.repl_token
