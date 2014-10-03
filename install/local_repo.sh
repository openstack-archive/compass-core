#!/bin/bash

mkdir -p /tmp/repo/
cd /tmp/repo/
wget https://s3-us-west-1.amazonaws.com/compass-local-repo/local_repo.tar.gz
tar -xzvf local_repo.tar.gz
mv local_repo/* /var/www/compass_web/v2/
