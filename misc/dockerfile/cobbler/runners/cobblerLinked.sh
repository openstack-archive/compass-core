#!/bin/bash

#This assumes the configured cobbler container is tagged as cobbler:config
 
sudo docker run -d --name cobblerlink -p 67:67 -p 69:69 -p 80:80 -p 25150:25150 -p 25151:25151 cobbler:config
