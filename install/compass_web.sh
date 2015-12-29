#!/bin/bash
# Move files to their respective locations

### BEGIN OF SCRIPT ###
echo "setup compass configuration"
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
source $DIR/install.conf
if [ -f $DIR/env.conf ]; then
    source $DIR/env.conf
else
    echo "failed to load environment"
    exit 1
fi
source $DIR/install_func.sh

mkdir -p /var/www/compass_web
rm -rf /var/www/compass_web/*

#sudo cp -rf $WEB_HOME/public/* /var/www/compass_web/
#sudo cp -rf $WEB_HOME/v2 /var/www/compass_web/

sudo mkdir -p /var/www/compass_web/v2.5
sudo cp -rf $WEB_HOME/v2.5/target/* /var/www/compass_web/v2.5/

sudo systemctl restart httpd.service
sleep 10

echo "Checking if httpd is running"
sudo systemctl status httpd.service
if [[ "$?" == "0" ]]; then
    echo "httpd is running"
else
    echo "httpd is not running"
    exit 1
fi
