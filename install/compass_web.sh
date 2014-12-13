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
    fastesturl $LOCAL_REPO_HUAWEI $LOCAL_REPO_US
    if [[ "$?" != "0" ]]; then
        echo "failed to determine the fastest local repo source"
        exit 1
    fi
    read -r LOCAL_REPO_SOURCE</tmp/url
    LOCAL_REPO_DIR=`dirname $LOCAL_REPO_SOURCE`
    download ${LOCAL_REPO_DIR}/local_repo.tar.gz local_repo.tar.gz unzip /tmp/repo || exit $?
    mv -f /tmp/repo/local_repo/* /var/www/compass_web/v2/
    if [[ "$?" != "0" ]]; then
	echo "failed to setup local repo"
	exit 1
    fi
    donwload ${LOCAL_REPO_DIR}/centos_repo.tar.gz centos_repo.tar.gz unzip /var/www/compass_web/v2/ || exit $?
    download ${LOCAL_REPO_DIR}/ubuntu_repo.tar.gz ubuntu_repo.tar.gz unzip /var/www/compass_web/v2/ || exit $?
    download ${LOCAL_REPO_DIR}/gem_repo.tar.gz gem_repo.tar.gz unzip /var/www/compass_web/v2/ || exit $?
    download ${LOCAL_REPO_DIR}/cirros-0.3.2-x86_64-disk.img cirros-0.3.2-x86_64-disk.img copy /var/www/compass_web/v2/ || exit $?
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
