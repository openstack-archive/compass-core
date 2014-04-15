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
sudo python setup.py install
if [[ "$?" != "0" ]]; then
    echo "failed to install compass package"
    exit 1
else
    echo "compass package is installed"
fi

sudo sed -i "/COBBLER_INSTALLER_URL/c\COBBLER_INSTALLER_URL = 'http:\/\/$ipaddr/cobbler_api'" /etc/compass/setting
sudo sed -i "/CHEF_INSTALLER_URL/c\CHEF_INSTALLER_URL = 'https:\/\/$ipaddr/'" /etc/compass/setting
sudo sed -i "s/\$compass_ip/$ipaddr/g" /etc/compass/global_config
sudo sed -i "s/\$compass_hostname/$HOSTNAME/g" /etc/compass/global_config

# add cookbooks, databags and roles
sudo chmod +x /opt/compass/bin/addcookbooks.py	
sudo chmod +x /opt/compass/bin/adddatabags.py
sudo chmod +x /opt/compass/bin/addroles.py

sudo /opt/compass/bin/addcookbooks.py  --cookbooks_dir=/var/chef/cookbooks
if [[ "$?" != "0" ]]; then
    echo "failed to add cookbooks"
    exit 1
fi
sudo /opt/compass/bin/adddatabags.py   --databags_dir=/var/chef/databags
if [[ "$?" != "0" ]]; then
    echo "failed to add databags"
    exit 1
fi
sudo /opt/compass/bin/addroles.py      --roles_dir=/var/chef/roles
if [[ "$?" != "0" ]]; then
    echo "failed to add roles"
    exit 1
fi

# copy the chef validatation keys to cobbler snippets
sudo cp -rf /etc/chef-server/chef-validator.pem /var/lib/cobbler/snippets/chef-validator.pem

sudo sh /opt/compass/bin/refresh.sh

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

sudo service compassd status
if [[ "$?" != "0" ]]; then
    echo "compassd is not started"
    exit 1
else
    echo "compassd has already started"
fi
