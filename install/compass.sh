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

cd $SCRIPT_DIR

sudo mkdir -p /etc/compass
sudo rm -rf /etc/compass/*
sudo mkdir -p /opt/compass/bin
sudo rm -rf /opt/compass/bin/*
sudo mkdir -p /var/log/compass
sudo rm -rf /var/log/compass/*
sudo mkdir -p /var/log/chef
sudo rm -rf /var/log/chef/*
sudo mkdir -p /var/www/compass
sudo rm -rf /var/www/compass/*

sudo cp -rf $COMPASSDIR/misc/apache/ods-server.conf /etc/httpd/conf.d/ods-server.conf
sudo cp -rf $COMPASSDIR/misc/apache/http_pip.conf /etc/httpd/conf.d/http_pip.conf
sudo cp -rf $COMPASSDIR/conf/* /etc/compass/
sudo cp -rf $COMPASSDIR/service/* /etc/init.d/
sudo cp -rf $COMPASSDIR/bin/*.py /opt/compass/bin/
sudo cp -rf $COMPASSDIR/bin/*.sh /opt/compass/bin/
sudo cp -rf $COMPASSDIR/bin/ansible_callbacks /opt/compass/bin/
sudo cp -rf $COMPASSDIR/bin/compassd /usr/bin/
sudo cp -rf $COMPASSDIR/bin/switch_virtualenv.py.template /opt/compass/bin/switch_virtualenv.py
sudo ln -s -f /opt/compass/bin/compass_check.py /usr/bin/compass
sudo ln -s -f /opt/compass/bin/compass_wsgi.py /var/www/compass/compass.wsgi
sudo cp -rf $COMPASSDIR/bin/chef/* /opt/compass/bin/
sudo cp -rf $COMPASSDIR/bin/cobbler/* /opt/compass/bin/

if [[ $SUPPORT_CENTOS_7_2 != "y" ]]; then
    sudo rm -f /etc/compass/os/centos7.0.conf
fi

if [[ $SUPPORT_UBUNTU_14_04_03 != "y" ]]; then
    sudo rm -f /etc/compass/os/ubuntu14.04.conf
fi

# add apache user to the group of virtualenv user
sudo usermod -a -G `groups $USER|awk '{print$3}'` apache

# setup ods server
if [ ! -f /usr/lib64/libcrypto.so ]; then
    sudo cp -rf /usr/lib64/libcrypto.so.6 /usr/lib64/libcrypto.so
fi

download -u "$PIP_PACKAGES"  `basename $PIP_PACKAGES` unzip /var/www/ || exit $?

sudo mkdir -p /opt/compass/db
sudo chmod -R 777 /opt/compass/db
sudo chmod -R 777 /var/log/compass
sudo chmod -R 777 /var/log/chef
sudo echo "export C_FORCE_ROOT=1" > /etc/profile.d/celery_env.sh
sudo chmod +x /etc/profile.d/celery_env.sh
source `which virtualenvwrapper.sh`
if ! lsvirtualenv |grep compass-core>/dev/null; then
    mkvirtualenv --system-site-packages compass-core
fi
cd $COMPASSDIR
workon compass-core

python setup.py install
if [[ "$?" != "0" ]]; then
    echo "failed to install compass package"
    deactivate
    exit 1
else
    echo "compass package is installed in virtualenv under current dir"
fi

sudo sed -i "s/\$ipaddr/$IPADDR/g" /etc/compass/setting
sudo sed -i "s/\$hostname/$HOSTNAME/g" /etc/compass/setting
sudo sed -i "s/\$gateway/$OPTION_ROUTER/g" /etc/compass/setting
domains=$(echo $NAMESERVER_DOMAINS | sed "s/,/','/g")
sudo sed -i "s/\$domains/$domains/g" /etc/compass/setting

sudo sed -i "s/\$cobbler_ip/$IPADDR/g" /etc/compass/os_installer/cobbler.conf
#sudo sed -i "s/\$chef_ip/$IPADDR/g" /etc/compass/package_installer/chef-icehouse.conf
#sudo sed -i "s/\$chef_hostname/$HOSTNAME/g" /etc/compass/package_installer/chef-icehouse.conf
sudo sed -i "s|\$PythonHome|$VIRTUAL_ENV|g" /opt/compass/bin/switch_virtualenv.py
sudo ln -s -f $VIRTUAL_ENV/bin/celery /opt/compass/bin/celery

deactivate

sudo mkdir -p /var/log/redis
sudo chown -R redis:root /var/log/redis
sudo mkdir -p /var/lib/redis/
sudo rm -rf /var/lib/redis/*
sudo chown -R redis:root /var/lib/redis
sudo mkdir -p /var/run/redis
sudo chown -R redis:root /var/run/redis
sudo mkdir -p /var/lib/redis
sudo chown -R redis:root /var/lib/redis
sudo rm -rf /var/lib/redis/dump.rdb
sudo systemctl kill redis-server
sudo rm -rf /var/run/redis/redis.pid
sudo systemctl restart redis.service
sleep 10
echo "Checking if redis is running"
sudo systemctl status redis.service
if [[ "$?" == "0" ]]; then
    echo "redis is running"
else
    ps -ef | grep redis
    echo "redis is not running"
    exit 1
fi

sudo systemctl enable compass-progress-updated.service
sudo systemctl enable compass-celeryd.service

/opt/compass/bin/refresh.sh
if [[ "$?" != "0" ]]; then
    echo "failed to refresh compassd service"
    exit 1
else
    echo "compassed service is refreshed"
fi

sudo systemctl status httpd.service
if [[ "$?" != "0" ]]; then
    echo "httpd is not started"
    exit 1
else
    echo "httpd has already started"
fi

sudo systemctl status redis.service |grep running
if [[ "$?" != "0" ]]; then
    echo "redis is not started"
    exit 1
else
    echo "redis has already started"
fi

sudo systemctl status mysql.service |grep running
if [[ "$?" != "0" ]]; then
    echo "mysqld is not started"
    exit 1
fi

sudo systemctl status compass-celeryd.service |grep running
if [[ "$?" != "0" ]]; then
    echo "compass-celeryd is not started"
    exit 1
else
    echo "compass-celeryd has already started"
fi

sudo systemctl status compass-progress-updated.service |grep running
if [[ "$?" != "0" ]]; then
    echo "compass-progress-updated is not started"
    exit 1
else
    echo "compass-progress-updated has already started"
fi

sleep 10
#compass check
#if [[ "$?" != "0" ]]; then
#    echo "compass check failed"
#    exit 1
#fi
