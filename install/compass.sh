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

mkdir -p /etc/compass
rm -rf /etc/compass/*
mkdir -p /opt/compass/bin
rm -rf /opt/compass/bin/*
mkdir -p /var/log/compass
rm -rf /var/log/compass/*
sudo mkdir -p /var/log/chef
rm -rf /var/log/chef/*
mkdir -p /var/www/compass
rm -rf /var/www/compass/*

sudo cp -rf $COMPASSDIR/misc/apache/ods-server.conf /etc/httpd/conf.d/ods-server.conf
sudo cp -rf $COMPASSDIR/conf/* /etc/compass/
sudo cp -rf $COMPASSDIR/service/* /etc/init.d/
sudo cp -rf $COMPASSDIR/bin/*.py /opt/compass/bin/
sudo cp -rf $COMPASSDIR/bin/*.sh /opt/compass/bin/
sudo cp -rf $COMPASSDIR/bin/compassd /usr/bin/
sudo cp -rf $COMPASSDIR/bin/switch_virtualenv.py.template /opt/compass/bin/switch_virtualenv.py
sudo ln -s -f /opt/compass/bin/compass_check.py /usr/bin/compass
sudo ln -s -f /opt/compass/bin/compass_wsgi.py /var/www/compass/compass.wsgi
sudo cp -rf $COMPASSDIR/bin/chef/* /opt/compass/bin/
sudo cp -rf $COMPASSDIR/bin/cobbler/* /opt/compass/bin/

# add apache user to the group of virtualenv user
sudo usermod -a -G `groups $USER|awk '{print$3}'` apache

# setup ods server
if [ ! -f /usr/lib64/libcrypto.so ]; then
    sudo cp -rf /usr/lib64/libcrypto.so.6 /usr/lib64/libcrypto.so
fi

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
sed -i "s/\$gateway/$OPTION_ROUTER/g" /etc/compass/setting
domains=$(echo $NAMESERVER_DOMAINS | sed "s/,/','/g")
sudo sed -i "s/\$domains/$domains/g" /etc/compass/setting

sudo sed -i "s/\$cobbler_ip/$IPADDR/g" /etc/compass/os_installer/cobbler.conf
sudo sed -i "s/\$chef_ip/$IPADDR/g" /etc/compass/package_installer/chef-icehouse.conf
sudo sed -i "s/\$chef_hostname/$HOSTNAME/g" /etc/compass/package_installer/chef-icehouse.conf
sudo sed -i "s|\$PythonHome|$VIRTUAL_ENV|g" /opt/compass/bin/switch_virtualenv.py
sudo ln -s -f $VIRTUAL_ENV/bin/celery /opt/compass/bin/celery

deactivate

sudo mkdir -p /var/log/redis
sudo chown -R redis:root /var/log/redis
sudo mkdir -p /var/lib/redis/
sudo chown -R redis:root /var/lib/redis
sudo mkdir -p /var/run/redis
sudo chown -R redis:root /var/run/redis
killall -9 redis-server
sudo service redis restart
echo "Checking if redis is running"
sudo service redis status
if [[ "$?" == "0" ]]; then
    echo "redis is running"
else
    echo "redis is not running"
    exit 1
fi

sudo chkconfig compass-progress-updated on
sudo chkconfig compass-celeryd on

/opt/compass/bin/refresh.sh
if [[ "$?" != "0" ]]; then
    echo "failed to refresh compassd service"
    exit 1
else
    echo "compassed service is refreshed"
fi

/opt/compass/bin/clean_nodes.sh
/opt/compass/bin/clean_clients.sh
/opt/compass/bin/clean_environments.sh
/opt/compass/bin/remove_systems.sh

sudo service httpd status
if [[ "$?" != "0" ]]; then
    echo "httpd is not started"
    exit 1
else
    echo "httpd has already started"
fi

sudo service redis status |grep running
if [[ "$?" != "0" ]]; then
    echo "redis is not started"
    exit 1
else
    echo "redis has already started"
fi

sudo service mysqld status |grep running
if [[ "$?" != "0" ]]; then
    echo "mysqld is not started"
    exit 1
fi

killall -9 celery
service compass-celeryd restart
service compass-celeryd status |grep running
if [[ "$?" != "0" ]]; then
    echo "compass-celeryd is not started"
    exit 1
else
    echo "compass-celeryd has already started"
fi

service compass-progress-updated status |grep running
if [[ "$?" != "0" ]]; then
    echo "compass-progress-updated is not started"
    exit 1
else
    echo "compass-progress-updated has already started"
fi

compass check
if [[ "$?" != "0" ]]; then
    echo "compass check failed"
    # exit 1
fi
