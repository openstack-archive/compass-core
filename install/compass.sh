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
sudo cp -rf $COMPASSDIR/conf/celeryconfig /etc/compass/
sudo cp -rf $COMPASSDIR/conf/global_config /etc/compass/
sudo cp -rf $COMPASSDIR/conf/setting /etc/compass/

sudo cp -rf $COMPASSDIR/conf/compassd /etc/init.d/
sudo cp -rf $COMPASSDIR/bin/*.py /opt/compass/bin/
sudo cp -rf $COMPASSDIR/bin/*.sh /opt/compass/bin/
sudo cp -rf $COMPASSDIR/bin/compass /usr/bin/
sudo cp -rf $COMPASSDIR/bin/chef/* /opt/compass/bin/
sudo cp -rf $COMPASSDIR/conf/compassd /usr/bin/
sudo cp -rf $WEB_HOME/public/* /var/www/compass_web/

sudo chkconfig compassd on

# setup ods server
if [ ! -f /usr/lib64/libcrypto.so ]; then
sudo cp -rf /usr/lib64/libcrypto.so.6 /usr/lib64/libcrypto.so
fi

sudo chmod -R 777 /opt/compass/db
sudo chmod -R 777 /var/log/compass
sudo echo "export C_FORCE_ROOT=1" > /etc/profile.d/celery_env.sh
sudo chmod +x /etc/profile.d/celery_env.sh
cd $COMPASSDIR
sudo python tools/install_venv.py
source .venv/bin/activate
python setup.py install
if [[ "$?" != "0" ]]; then
    echo "failed to install compass package"
    exit 1
else
    echo "compass package is installed in virtualenv under current dir"
fi

sudo sed -i "/^COBBLER_INSTALLER_URL/c\COBBLER_INSTALLER_URL = 'http:\/\/$ipaddr/cobbler_api'" /etc/compass/setting
sudo sed -i "/^CHEF_INSTALLER_URL/c\CHEF_INSTALLER_URL = 'https:\/\/$ipaddr/'" /etc/compass/setting
sudo sed -i "/^DATABASE_TYPE/c\DATABASE_TYPE = 'mysql'" /etc/compass/setting
sudo sed -i "/^DATABASE_USER/c\DATABASE_USER = '${MYSQL_USER}'" /etc/compass/setting
sudo sed -i "/^DATABASE_PASSWORD/c\DATABASE_PASSWORD = '${MYSQL_PASSWORD}'" /etc/compass/setting
sudo sed -i "/^DATABASE_SERVER/c\DATABASE_SERVER = '${MYSQL_SERVER}:${MYSQL_PORT}'" /etc/compass/setting
sudo sed -i "/^DATABASE_NAME/c\DATABASE_NAME = '${MYSQL_DATABASE}'" /etc/compass/setting
sudo sed -i "/^COBBLER_INSTALLER_TOKEN/c\COBBLER_INSTALLER_TOKEN = ['$CBLR_USER', '$CBLR_PASSWD']" /etc/compass/setting
sudo sed -i "s/\$compass_ip/$ipaddr/g" /etc/compass/global_config
sudo sed -i "s/\$compass_hostname/$HOSTNAME/g" /etc/compass/global_config
sudo sed -i "s/\$compass_testmode/$TESTMODE/g" /etc/compass/global_config
sudo sed -e 's|$PythonHome|'$VIRTUAL_ENV'|' -i /etc/httpd/conf.d/ods-server.conf
# add cookbooks, databags and roles
sudo chmod +x /opt/compass/bin/addcookbooks.py	
sudo chmod +x /opt/compass/bin/adddatabags.py
sudo chmod +x /opt/compass/bin/addroles.py

sudo /opt/compass/bin/addcookbooks.py
if [[ "$?" != "0" ]]; then
    echo "failed to add cookbooks"
    exit 1
else
    echo "cookbooks are added to chef server"
fi
sudo /opt/compass/bin/adddatabags.py
if [[ "$?" != "0" ]]; then
    echo "failed to add databags"
    exit 1
else
    echo "databags are added to chef server"
fi
sudo /opt/compass/bin/addroles.py
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

sudo /opt/compass/bin/refresh.sh
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

sudo service redis status
if [[ "$?" != "0" ]]; then
    echo "redis is not started"
    exit 1
else
    echo "redis has already started"
fi

sudo service mysqld status
if [[ "$?" != "0" ]]; then
    echo "mysqld is not started"
    exit 1
fi

sudo service compassd status
if [[ "$?" != "0" ]]; then
    echo "compassd is not started"
    exit 1
else
    echo "compassd has already started"
fi

sudo compass check
if [[ "$?" != "0" ]]; then
    echo "compass check failed"
    exit 1
fi

deactivate
