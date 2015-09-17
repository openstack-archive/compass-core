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
    download -u "${LOCAL_REPO_US}/gem_repo.tar.gz" -u "${LOCAL_REPO_HUAWEI}/gem_repo.tar.gz" gem_repo.tar.gz unzip /var/www/compass_web/v2 || exit $?
    download -u "${LOCAL_REPO_US}/cirros-0.3.2-x86_64-disk.img" -u "${LOCAL_REPO_HUAWEI}/cirros-0.3.2-x86_64-disk.img" cirros-0.3.2-x86_64-disk.img copy /var/www/compass_web/v2 || exit $?
    if [[ $SUPPORT_CENTOS_6_5 = "y" ]]; then
	mkdir -p /var/www/compass_web/v2/yum.repos.d/centos/6.5
	download -u "${LOCAL_REPO_US}/centos/6.5/centos_repo.tar.gz" -u "${LOCAL_REPO_HUAWEI}/centos/6.5/centos_repo.tar.gz" CentOS-6.5-x86_64.tar.gz unzip /var/www/compass_web/v2/yum.repos.d/centos/6.5 || exit $?
    fi
    if [[ $SUPPORT_CENTOS_6_6 = "y" ]]; then
	mkdir -p /var/www/compass_web/v2/yum.repos.d/centos/6.6
	download -u "${LOCAL_REPO_US}/centos/6.6/centos_repo.tar.gz" -u "${LOCAL_REPO_HUAWEI}/centos/6.6/centos_repo.tar.gz" CentOS-6.6-x86_64.tar.gz unzip /var/www/compass_web/v2/yum.repos.d/centos/6.6 || exit $?
    fi
    if [[ $SUPPORT_CENTOS_7_0 = "y" ]]; then
	mkdir -p /var/www/compass_web/v2/yum.repos.d/centos/7.0
	download -u "${LOCAL_REPO_US}/centos/7.0/centos_repo.tar.gz" -u "${LOCAL_REPO_HUAWEI}/centos/7.0/centos_repo.tar.gz" CentOS-7.0-x86_64.tar.gz unzip /var/www/compass_web/v2/yum.repos.d/centos/7.0 || exit $?
    fi
    if [[ $SUPPORT_UBUNTU_12_04 = "y" ]]; then
	mkdir -p /var/www/compass_web/v2/apt.repos.d/ubuntu/12.04
	download -u "${LOCAL_REPO_US}/ubuntu/12.04/ubuntu_repo.tar.gz" -u "${LOCAL_REPO_HUAWEI}/ubuntu/12.04/ubuntu_repo.tar.gz" Ubuntu-12.04-x86_64.tar.gz unzip /var/www/compass_web/v2/apt.repos.d/ubuntu/12.04 || exit $?
    fi
    if [[ $SUPPORT_UBUNTU_14_04 = "y" ]]; then
	mkdir -p /var/www/compass_web/v2/apt.repos.d/ubuntu/14.04
	download -u "${LOCAL_REPO_US}/ubuntu/14.04/ubuntu_repo.tar.gz" -u "${LOCAL_REPO_HUAWEI}/ubuntu/14.04/ubuntu_repo.tar.gz" Ubuntu-14.04-x86_64.tar.gz unzip /var/www/compass_web/v2/apt.repos.d/ubuntu/14.04 || exit $?
    fi
    if [[ $SUPPORT_SLES_11SP3 = "y" ]]; then
	mkdir -p /var/www/compass_web/v2/zypp.repos.d/sles/11sp3
	download -u "${LOCAL_REPO_US}/sles/11sp3/sles_repo.tar.gz" -u "${LOCAL_REPO_HUAWEI}/sles/11sp3/sles_repo.tar.gz" sles-11sp3-x86_64.tar.gz unzip /var/www/compass_web/v2/zypp.repos.d/sles/11sp3 || exit $?
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
