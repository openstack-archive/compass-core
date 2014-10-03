#!/bin/bash

cd /var/www/compass_web/v2/
wget -nH -r http://12.234.32.44/compass_repo/
wget -nH -r http://12.234.32.44/gem_repo/
wget -nH http://12.234.32.44/cirros-0.3.2-x86_64-disk.img
