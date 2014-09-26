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
if [ -z $WEB_SOURCE ]; then
    echo "web source $WEB_SOURCE is not set"
    exit 1
fi
copy2dir "$WEB_SOURCE" "$WEB_HOME" "stackforge/compass-web" || exit $?

if [ -z $ADAPTERS_SOURCE ]; then
    echo "adpaters source $ADAPTERS_SOURCE is not set"
    exit 1
fi
copy2dir "$ADAPTERS_SOURCE" "$ADAPTERS_HOME" "stackforge/compass-adapters" dev/experimental || exit $?

mkdir -p /etc/compass
mkdir -p /opt/compass/bin
mkdir -p /var/www/compass_web
mkdir -p /var/log/compass
sudo mkdir -p /var/log/chef
mkdir -p /opt/compass/db
mkdir -p /var/www/compass

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

sudo cp -rf $WEB_HOME/public/* /var/www/compass_web/
sudo cp -rf $WEB_HOME/v2 /var/www/compass_web/

sudo rm -rf /var/chef
sudo mkdir -p /var/chef/cookbooks/
sudo cp -r $ADAPTERS_HOME/chef/cookbooks/* /var/chef/cookbooks/
if [ $? -ne 0 ]; then
    echo "failed to copy cookbooks to /var/chef/cookbooks/"
    exit 1
fi
sudo mkdir -p /var/chef/databags/
sudo cp -r $ADAPTERS_HOME/chef/databags/* /var/chef/databags/
if [ $? -ne 0 ]; then
    echo "failed to copy databags to /var/chef/databags/"
    exit 1
fi
sudo mkdir -p /var/chef/roles/
sudo cp -r $ADAPTERS_HOME/chef/roles/* /var/chef/roles/
if [ $? -ne 0 ]; then
    echo "failed to copy roles to /var/chef/roles/"
    exit 1
fi

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
    mkvirtualenv compass-core
fi
cd $COMPASSDIR
workon compass-core

function compass_cleanup {
    echo "deactive"
    deactivate
}
trap compass_cleanup EXIT

python setup.py install
if [[ "$?" != "0" ]]; then
    echo "failed to install compass package"
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

/opt/compass/bin/addcookbooks.py
if [[ "$?" != "0" ]]; then
    echo "failed to add cookbooks"
    exit 1
else
    echo "cookbooks are added to chef server"
fi
/opt/compass/bin/adddatabags.py
if [[ "$?" != "0" ]]; then
    echo "failed to add databags"
    exit 1
else
    echo "databags are added to chef server"
fi
/opt/compass/bin/addroles.py
if [[ "$?" != "0" ]]; then
    echo "failed to add roles"
    exit 1
else
    echo "roles are added to chef server"
fi

sudo mkdir -p /var/log/redis
sudo chown -R redis:root /var/log/redis
sudo mkdir -p /var/lib/redis/
sudo chown -R redis:root /var/lib/redis
sudo mkdir -p /var/run/redis
sudo chown -R redis:root /var/run/redis
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

#compass check
#if [[ "$?" != "0" ]]; then
#    echo "compass check failed"
#    exit 1
#fi
