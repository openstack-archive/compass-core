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

sudo cp -rf $WEB_HOME/public/* /var/www/compass_web/
sudo cp -rf $WEB_HOME/v2 /var/www/compass_web/

if [[ $LOCAL_REPO = "y" ]]; then
    echo "setting up local repo"
    mkdir -p /tmp/repo
    if [[ "$REGION" == "asia" ]]; then
        download $LOCAL_REPO_ASIA local_repo.tar.gz unzip /tmp/repo || exit $?
    else
        download https://s3-us-west-1.amazonaws.com/compass-local-repo/local_repo.tar.gz local_repo.tar.gz unzip /tmp/repo || exit $?
    fi
    mv -f /tmp/repo/local_repo/* /var/www/compass_web/v2/
    if [[ "$?" != "0" ]]; then
	echo "failed to setup local repo"
	exit 1
    fi
fi

sudo service httpd restart
sleep 10

echo "Checking if httpd is running"
sudo service httpd status
if [[ "$?" == "0" ]]; then
    echo "httpd is running"
else
    echo "httpd is not running"
    exit 1
fi
