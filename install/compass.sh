#!/bin/bash
SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
echo "script dir: $SCRIPT_DIR"
COMPASSDIR=${SCRIPT_DIR}/..
echo "compass dir is $COMPASSDIR"
copygit2dir()
{
    destdir=$1
    repo=$2
    if [ -d $destdir ];then
        echo "$destdir exists"
        cd $destdir
        git remote set-url origin $repo
        git remote update
        git reset --hard
        git clean -x -f
        git checkout master
        git reset --hard remotes/origin/master
        if [[ -n "$GERRIT_REFSPEC" ]];then
            git fetch origin $GERRIT_REFSPEC && git checkout FETCH_HEAD
        fi
        git clean -x -f
    else
        mkdir -p $destdir
        git clone $repo $destdir
        if [[ -n "$GERRIT_REFSPEC" ]];then
            # project=$(echo $repo|rev|cut -d '/' -f 1|rev)
            cd $destdir
            git fetch $repo $GERRIT_REFSPEC && git checkout FETCH_HEAD
        fi
    fi
    cd $SCRIPT_DIR
}
copylocal2dir()
{
    destdir=$1
    repo=$2
    if [ -d $destdir ];then
        echo "$destdir exists"
    else
        mkdir -p $destdir
    fi
    sudo \cp -rf $repo/* $destdir
}
cd $SCRIPT_DIR
#export ipaddr=$(ifconfig $NIC | grep 'inet addr:' | cut -d: -f2 | awk '{ print $1}')

##SUBNET=${SUBNET:-$(ip address| grep "global $NIC" |cut -f 6 -d ' ')}
WEB_HOME=${WEB_HOME:-'/tmp/web/'}
ADAPTER_HOME=${ADAPTER_HOME:-'/tmp/adapter/'}
##WEB_SOURCE=${WEB_SOURCE:-'https://github.com/stackforge/compass-web'}
WEB_SOURCE=${WEB_SOURCE:-$PROJECT_NAME'/stackforge/compass-web'}
# ADAPTER_SOURCE=${ADAPTER_SOURCE:-'https://github.com/stackforge/compass-adapters'}
ADAPTER_SOURCE=${ADAPTER_SOURCE:-$PROJECT_NAME'/stackforge/compass-adapters'}
if [ "$source" != "local" ]; then
  copygit2dir $WEB_HOME $WEB_SOURCE
  copygit2dir $ADAPTER_HOME $ADAPTER_SOURCE
else 
  copylocal2dir $WEB_HOME $WEB_SOURCE
  copylocal2dir $ADAPTER_HOME $ADAPTER_SOURCE
fi

# download dependences
wget http://github.com/downloads/bitovi/javascriptmvc/$JS_MVC.zip
sudo yum install -y unzip
sudo unzip -o $JS_MVC
sudo \cp -rf $JS_MVC/. $WEB_HOME/public/

# update squid conf
sudo rm /etc/squid/squid.conf 
sudo cp $COMPASSDIR/misc/squid/squid.conf /etc/squid/
sudo sed -i "/acl localnet src 10.0.0.0/i\acl localnet src $SUBNET" /etc/squid/squid.conf
sudo chmod 644 /etc/squid/squid.conf
sudo mkdir -p /var/squid/cache
sudo chown -R squid:squid /var/squid
sudo service squid restart

# update /etc/resolv.conf
echo "DNS1=$ipaddr" >> /etc/sysconfig/network-scripts/ifcfg-$NIC
echo "DOMAIN=ods.com" >> /etc/sysconfig/network-scripts/ifcfg-$NIC
service network restart

# Install net-snmp
sudo yum install -y net-snmp-utils net-snmp net-snmp-python
if [ ! -d "/usr/local/share/snmp/" ]; then
  sudo mkdir /usr/local/share/snmp/
fi
sudo cp -rf $COMPASSDIR/mibs /usr/local/share/snmp/
sudo cat >> /etc/snmp/snmp.conf <<EOF
mibdirs +/usr/local/share/snmp/mibs
EOF

# update cobbler config
sudo cp -r /var/lib/cobbler/snippets /root/backup/cobbler/
sudo cp -r /var/lib/cobbler/kickstarts/ /root/backup/cobbler/
sudo rm -rf /var/lib/cobbler/snippets/*
sudo cp -r $ADAPTER_HOME/cobbler/snippets/* /var/lib/cobbler/snippets/
sudo cp -rf /etc/chef-server/chef-validator.pem /var/lib/cobbler/snippets/chef-validator.pem
sudo chmod 777 /var/lib/cobbler/snippets
sudo chmod 666 /var/lib/cobbler/snippets/*
sudo rm /var/lib/cobbler/kickstarts/default.ks
sudo cp -r $ADAPTER_HOME/cobbler/kickstarts/default.ks /var/lib/cobbler/kickstarts/
sudo chmod 666 /var/lib/cobbler/kickstarts/default.ks

# update chef config
sudo mkdir -p /var/chef/cookbooks/
sudo mkdir -p /var/chef/databags/
sudo mkdir -p /var/chef/roles/

sudo cp -r $ADAPTER_HOME/chef/cookbooks/* /var/chef/cookbooks/
sudo cp -r $ADAPTER_HOME/chef/databags/* /var/chef/databags/
sudo cp -r $ADAPTER_HOME/chef/roles/* /var/chef/roles/

# Move files to their respective locations
mkdir -p /etc/compass
mkdir -p /opt/compass/bin
mkdir -p /var/www/compass_web
mkdir -p /var/log/compass
mkdir -p /opt/compass/db
mkdir -p /var/www/compass

sudo \cp -rf $COMPASSDIR/misc/apache/ods-server /etc/httpd/conf.d/ods-server.conf
sudo \cp -rf $COMPASSDIR/misc/apache/compass.wsgi /var/www/compass/compass.wsgi
sudo \cp -rf $COMPASSDIR/conf/celeryconfig /etc/compass/
sudo \cp -rf $COMPASSDIR/conf/global_config /etc/compass/
sudo \cp -rf $COMPASSDIR/conf/setting /etc/compass/
sudo \cp -rf $COMPASSDIR/conf/compassd /etc/init.d/
sudo \cp -rf $COMPASSDIR/bin/*.py /opt/compass/bin/
sudo \cp -rf $COMPASSDIR/bin/*.sh /opt/compass/bin/
sudo \cp -rf $COMPASSDIR/bin/compass /usr/bin/
sudo \cp -rf $COMPASSDIR/bin/chef/* /opt/compass/bin/
sudo \cp -rf $COMPASSDIR/conf/compassd /usr/bin/
sudo \cp -rf $WEB_HOME/public/* /var/www/compass_web/
sudo chmod +x /etc/init.d/compassd
sudo chmod +x /usr/bin/compassd

sudo chkconfig compassd on

sudo chmod +x /opt/compass/bin/addcookbooks.py
sudo chmod +x /opt/compass/bin/adddatabags.py
sudo chmod +x /opt/compass/bin/addroles.py

/opt/compass/bin/addcookbooks.py
/opt/compass/bin/adddatabags.py
/opt/compass/bin/addroles.py
 
# setup ods server
sudo yum -y install openssl
sudo yum -y install openssl098e
sudo cp -r /usr/lib64/libcrypto.so.6 /usr/lib64/libcrypto.so
sudo chmod -R 777 /opt/compass/db
sudo chmod -R 777 /var/log/compass
sudo echo "export C_FORCE_ROOT=1" > /etc/profile.d/celery_env.sh
sudo chmod +x /etc/profile.d/celery_env.sh
sudo service httpd restart

cd $COMPASSDIR
sudo python setup.py install
sudo sed -i "/COBBLER_INSTALLER_URL/c\COBBLER_INSTALLER_URL = 'http:\/\/$ipaddr/cobbler_api'" /etc/compass/setting
sudo sed -i "/CHEF_INSTALLER_URL/c\CHEF_INSTALLER_URL = 'https:\/\/$ipaddr/'" /etc/compass/setting
sudo sh /opt/compass/bin/refresh.sh --init
figlet -ctf slant Installation Complete!
