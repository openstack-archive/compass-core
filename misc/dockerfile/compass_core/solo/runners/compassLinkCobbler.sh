#!/bin/bash

#This command assumes that the configured compass images is tagged as compass:config
#it needs to be passed the name of the container running configured cobbler.

echo attaching compass to $1

sudo docker run -d -p 80:80 -p 445:445 -p 5672:5672 -p 6379:6379 -p 514:514 -p 123:123 -p 4369:4369 -p 25151:25151 -p 3306:3306 --link $1:cobbler compass:config
