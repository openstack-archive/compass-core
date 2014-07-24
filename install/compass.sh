#!/bin/bash
# Move files to their respective locations
mkdir -p /etc/compass
mkdir -p /opt/compass/bin
mkdir -p /var/www/compass_web
mkdir -p /var/log/compass
mkdir -p /opt/compass/db
mkdir -p /var/www/compass

sudo cp -rf $COMPASSDIR/misc/apache/ods-server /etc/httpd/conf.d/ods-server.conf
sudo cp -rf $COMPASSDIR/misc/apache/compass.wsgi /var/www/compass/compass.wsgi
sudo cp -rf $COMPASSDIR/conf/* /etc/compass/
sudo cp -rf $COMPASSDIR/service/* /etc/init.d/
sudo cp -rf $COMPASSDIR/bin/*.py /opt/compass/bin/
sudo cp -rf $COMPASSDIR/bin/*.sh /opt/compass/bin/
sudo cp -rf $COMPASSDIR/bin/compass /usr/bin/
sudo cp -rf $COMPASSDIR/bin/chef/* /opt/compass/bin/
sudo cp -rf $WEB_HOME/public/* /var/www/compass_web/
if [[ -f /etc/compass/package_installer/chef-icehouse.conf ]]; then
    sudo sed -i "s/127.0.0.1/$ippaddr/g" /etc/compass/package_installer/chef-icehouse.conf
fi
# add apache user to the group of virtualenv user
sudo usermod -a -G `groups $USER|awk '{print$3}'` apache
sudo chkconfig compass-progress-updated on
sudo chkconfig compass-celeryd on

# setup ods server
if [ ! -f /usr/lib64/libcrypto.so ]; then
sudo cp -rf /usr/lib64/libcrypto.so.6 /usr/lib64/libcrypto.so
fi

sudo chmod -R 777 /opt/compass/db
sudo chmod -R 777 /var/log/compass
sudo echo "export C_FORCE_ROOT=1" > /etc/profile.d/celery_env.sh
sudo chmod +x /etc/profile.d/celery_env.sh
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

sudo sed -i "/COBBLER_INSTALLER_URL/c\COBBLER_INSTALLER_URL = 'http:\/\/$ipaddr/cobbler_api'" /etc/compass/setting
sudo sed -i "/CHEF_INSTALLER_URL/c\CHEF_INSTALLER_URL = 'https:\/\/$ipaddr/'" /etc/compass/setting
sudo sed -i "s/\$compass_ip/$ipaddr/g" /etc/compass/global_config
sudo sed -i "s/\$compass_hostname/$HOSTNAME/g" /etc/compass/global_config
sudo sed -i "s/\$compass_testmode/$TESTMODE/g" /etc/compass/global_config
sudo sed -e 's|$PythonHome|'$VIRTUAL_ENV'|' -i /var/www/compass/compass.wsgi
sudo sed -e 's|$Python|'$VIRTUAL_ENV/bin/python'|' -i /etc/init.d/compass-progress-updated
sudo sed -e 's|$CeleryPath|'$VIRTUAL_ENV/bin/celeryd'|' -i /etc/init.d/compass-celeryd
sudo sed -e 's|$Python|'$VIRTUAL_ENV/bin/python'|' -i /usr/bin/compassd

# add cookbooks, databags and roles
sudo chmod +x /opt/compass/bin/addcookbooks.py	
sudo chmod +x /opt/compass/bin/adddatabags.py
sudo chmod +x /opt/compass/bin/addroles.py

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

/opt/compass/bin/refresh.sh
if [[ "$?" != "0" ]]; then
    echo "failed to refresh compassd service"
    exit 1
else
    echo "compassed service is refreshed"
fi

sudo service httpd status
if [[ "$?" != "0" ]]; then
    echo "httpd is not started"
    exit 1
else
    echo "httpd has already started"
fi

mkdir -p /var/log/redis
chown -R redis:root /var/log/redis
mkdir -p /var/lib/redis/
chown -R redis:root /var/lib/redis
mkdir -p /var/run/redis
chown -R redis:root /var/run/redis

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

deactivate
