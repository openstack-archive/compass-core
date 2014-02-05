#!/bin/bash
# update rsyslog
sudo rm -f /etc/rsyslog.conf
sudo cp -rf $COMPASSDIR/misc/rsyslog/rsyslog.conf /etc/rsyslog.conf
sudo chmod 644 /etc/rsyslog.conf
sudo service rsyslog restart
sudo service rsyslog status
if [[ "$?" != "0" ]]; then
    echo "rsyslog is not started"
    exit 1
fi

# update logrotate.d
rm -f /etc/logrotate.d/*
sudo cp -rf $COMPASSDIR/misc/logrotate.d/* /etc/logrotate.d/
sudo chmod 644 /etc/logrotate.d/*

# update ntp conf
sudo rm -f /etc/ntp.conf
sudo cp -rf $COMPASSDIR/misc/ntp/ntp.conf /etc/ntp.conf
sudo chmod 644 /etc/ntp.conf
sudo service ntpd stop
sudo ntpdate 0.centos.pool.ntp.org
sudo service ntpd start
sudo service ntpd status
if [[ "$?" != "0" ]]; then
    echo "ntp is not started"
    exit 1
fi

# update squid conf
sudo rm -f /etc/squid/squid.conf 
sudo cp $COMPASSDIR/misc/squid/squid.conf /etc/squid/
subnet_escaped=$(echo $SUBNET | sed -e 's/[\/&]/\\&/g')
sudo sed -i "s/acl localnet src \$subnet/acl localnet src $subnet_escaped/g" /etc/squid/squid.conf
sudo chmod 644 /etc/squid/squid.conf
sudo mkdir -p /var/squid/cache
sudo chown -R squid:squid /var/squid
sudo service squid restart
sudo service squid status
if [[ "$?" != "0" ]]; then
    echo "squid is not started"
    exit 1
fi

# Install net-snmp
sudo mkdir -p /usr/local/share/snmp/
sudo cp -rf $COMPASSDIR/mibs /usr/local/share/snmp/
sudo rm -f /etc/snmp/snmp.conf
sudo cp -rf $COMPASSDIR/misc/snmp/snmp.conf /etc/snmp/snmp.conf
sudo chmod 644 /etc/snmp/snmp.conf

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
fi

sudo sed -i "/COBBLER_INSTALLER_URL/c\COBBLER_INSTALLER_URL = 'http:\/\/$ipaddr/cobbler_api'" /etc/compass/setting
sudo sed -i "/CHEF_INSTALLER_URL/c\CHEF_INSTALLER_URL = 'https:\/\/$ipaddr/'" /etc/compass/setting

# add cookbooks, databags and roles
sudo /opt/compass/bin/addcookbooks.py  --cookbooks_dir=$ADAPTER_HOME/chef/cookbooks
sudo /opt/compass/bin/adddatabags.py   --databags_dir=$ADAPTER_HOME/chef/databags
sudo /opt/compass/bin/addroles.py      --roles_dir=$ADAPTER_HOME/chef/roles

# copy the chef validatation keys to cobbler snippets
sudo cp -rf /etc/chef-server/chef-validator.pem /var/lib/cobbler/snippets/chef-validator.pem

sudo sh /opt/compass/bin/refresh.sh

sudo service httpd status
if [[ "$?" != "0" ]]; then
   echo "httpd is not started"
   exit 1
fi

sudo service compassd status
if [[ "$?" != "0" ]]; then
    echo "compassd is not started"
    exit 1
fi

figlet -ctf slant Installation Complete!
