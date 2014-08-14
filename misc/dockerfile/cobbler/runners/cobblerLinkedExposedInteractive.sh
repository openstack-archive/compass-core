#!/bin/bash

#This assumes the configured cobbler container is tagged as cobbler:config

sudo docker run -t -i --name cobblerlink -p 8080:80 -p 67:67 -p 69:69 -p 25150:25150 -p 25151:25151 cobbler:config
