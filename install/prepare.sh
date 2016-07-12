#!/bin/bash
# prepare the installation

### BEGIN OF SCRIPT ###
echo "prepare installation"
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
source $DIR/install.conf
if [ -f $DIR/env.conf ]; then
    source $DIR/env.conf
else
    echo "failed to load environment"
    exit 1
fi
source $DIR/install_func.sh

# Create backup dir
sudo mkdir -p /root/backup

# update /etc/hosts
echo "update /etc/hosts"
sudo cp -rn /etc/hosts /root/backup/hosts
sudo rm -f /etc/hosts
sudo cp -rf $COMPASSDIR/misc/hosts /etc/hosts
sudo sed -i "s/\$ipaddr \$hostname/$IPADDR $HOSTNAME/g" /etc/hosts
sudo chmod 644 /etc/hosts

# update rsyslog
echo "update rsyslog"
sudo cp -rn /etc/rsyslog.conf /root/backup/
sudo rm -f /etc/rsyslog.conf
sudo cp -rf $COMPASSDIR/misc/rsyslog/rsyslog.conf /etc/rsyslog.conf
sudo chmod 644 /etc/rsyslog.conf
sudo service rsyslog restart
sudo sleep 10
sudo service rsyslog status
if [[ "$?" != "0" ]]; then
    echo "rsyslog is not started"
    exit 1
else
    echo "rsyslog conf is updated"
fi

# update logrotate.d
echo "update logrotate config"
sudo cp -rn /etc/logrotate.d /root/backup/
rm -f /etc/logrotate.d/*
sudo cp -rf $COMPASSDIR/misc/logrotate.d/* /etc/logrotate.d/
sudo chmod 644 /etc/logrotate.d/*

# update ntp conf
echo "update ntp config"
sudo cp -rn /etc/ntp.conf /root/backup/
sudo rm -f /etc/ntp.conf
sudo cp -rf $COMPASSDIR/misc/ntp/ntp.conf /etc/ntp.conf
sudo chmod 644 /etc/ntp.conf
sudo systemctl stop ntpd.service
sudo ntpdate 0.centos.pool.ntp.org
sudo systemctl start ntpd.service
sudo sleep 10
sudo systemctl status ntpd.service
if [[ "$?" != "0" ]]; then
    echo "ntp is not started"
    exit 1
else
    echo "ntp conf is updated"
fi

# commenting out squid as we are not using it now
#echo "update squid config"
#sudo cp -rn /etc/squid/squid.conf /root/backup/
#sudo rm -f /etc/squid/squid.conf 
#sudo cp $COMPASSDIR/misc/squid/squid.conf /etc/squid/
#export netaddr=$(ipcalc $IPADDR $NETMASK -n |cut -f 2 -d '=')
#export netprefix=$(ipcalc $IPADDR $NETMASK -p |cut -f 2 -d '=')
#subnet=${netaddr}/${netprefix}
#subnet_escaped=$(echo $subnet | sed -e 's/[\/&]/\\&/g')
#sudo sed -i "s/acl localnet src \$subnet/acl localnet src $subnet_escaped/g" /etc/squid/squid.conf
#sudo chmod 644 /etc/squid/squid.conf
#sudo mkdir -p /var/squid/cache
#sudo chown -R squid:squid /var/squid
#sudo mkdir -p /var/log/squid
#sudo chmod -R 777 /var/log/squid
#sudo systemctl restart squid.service
#sudo sleep 10
#sudo ser
#if [[ "$?" != "0" ]]; then
#    echo "squid is not started"
#    exit 1
#else
#    echo "squid conf is updated"
# fi

mkdir -p /var/log/httpd
chmod -R 777 /var/log/httpd

systemctl restart httpd.service
sudo sleep 10
systemctl status httpd.service
if [[ "$?" != "0" ]]; then
    echo "httpd is not started"
    exit 1
else
    echo "httpd conf is updated"
fi

#update mysqld
if [ "$FULL_COMPASS_SERVER" == "true"]; then
    echo "update mysqld"
    mkdir -p /var/log/mysql
    chmod -R 777 /var/log/mysql
    sleep 10
    systemctl restart mysql.service
    sudo sleep 10
    systemctl status mysql.service
    if [[ "$?" != "0" ]]; then
        echo "failed to restart mysqld"
        exit 1
    else
        echo "mysqld restarted"
    fi

    MYSQL_USER=${MYSQL_USER:-root}
    MYSQL_OLD_PASSWORD=${MYSQL_OLD_PASSWORD:-root}
    MYSQL_PASSWORD=${MYSQL_PASSWORD:-root}
    MYSQL_SERVER=${MYSQL_SERVER:-127.0.0.1}
    MYSQL_PORT=${MYSQL_PORT:-3306}
    MYSQL_DATABASE=${MYSQL_DATABASE:-compass}
    # first time set mysql password
    sudo mysqladmin -h${MYSQL_SERVER} --port=${MYSQL_PORT} -u ${MYSQL_USER} -p"${MYSQL_OLD_PASSWORD}" password ${MYSQL_PASSWORD}
    if [[ "$?" != "0" ]]; then
        echo "setting up mysql initial password"
        sudo mysqladmin -h${MYSQL_SERVER} --port=${MYSQL_PORT} -u ${MYSQL_USER} password ${MYSQL_PASSWORD}
    fi
    mysql -h${MYSQL_SERVER} --port=${MYSQL_PORT} -u${MYSQL_USER} -p${MYSQL_PASSWORD} -e "show databases;"
    if [[ "$?" != "0" ]]; then
        echo "mysql password set failed"
        exit 1
    else
        echo "mysql password set succeeded"
    fi

    sudo mysql -h${MYSQL_SERVER} --port=${MYSQL_PORT} -u${MYSQL_USER} -p${MYSQL_PASSWORD} -e "drop database ${MYSQL_DATABASE}"
    sudo mysql -h${MYSQL_SERVER} --port=${MYSQL_PORT} -u${MYSQL_USER} -p${MYSQL_PASSWORD} -e "create database ${MYSQL_DATABASE}"
    if [[ "$?" != "0" ]]; then
        echo "mysql database set failed"
        exit 1
    fi

    sudo systemctl restart mysql.service
    sudo systemctl status mysql.service
    if [[ "$?" != "0" ]]; then
        echo "mysqld is not started"
        exit 1
    fi

    sudo systemctl restart rabbitmq-server.service
    sudo systemctl status rabbitmq-server.service
    if [[ "$?" != "0" ]]; then
        echo "rabbitmq-server is not started"
        exit 1
    fi
fi

cd $SCRIPT_DIR
remote_branch=$(git rev-parse --abbrev-ref --symbolic-full-name @{u})
if [[ "$?" != "0" ]]; then
    remote_branch="origin/master"
fi
local_branch=$(echo ${remote_branch} | sed -e 's/origin\///g')

if [ -z $WEB_SOURCE ]; then
    echo "web source $WEB_SOURCE is not set"
    exit 1
fi
copy2dir "$WEB_SOURCE" "$WEB_HOME" || exit $?

if [ -z $ADAPTERS_SOURCE ]; then
    echo "adpaters source $ADAPTERS_SOURCE is not set"
    exit 1
fi
copy2dir "$ADAPTERS_SOURCE" "$ADAPTERS_HOME" || exit $?

if [ "$tempest" == "true" ]; then
    echo "download tempest packages"
    if [[ ! -e /tmp/tempest ]]; then
        git clone http://git.openstack.org/openstack/tempest /tmp/tempest
        if [[ "$?" != "0" ]]; then
            echo "failed to git clone tempest project"
            exit 1
        else
            echo "git clone tempest project succeeded"
        fi
        cd /tmp/tempest
        git checkout grizzly-eol
    else
        cd /tmp/tempest
        git remote set-url origin http://git.openstack.org/openstack/tempest
        git remote update
        if [[ "$?" != "0" ]]; then
            echo "failed to git remote update tempest project"
            exit 1
        else
            echo "git remote update tempest project succeeded"
        fi
        git reset --hard
        git clean -x -f -d -q
        git checkout grizzly-eol
    fi
    source `which virtualenvwrapper.sh`
    if ! lsvirtualenv |grep tempest>/dev/null; then
        mkvirtualenv tempest
    fi
    workon tempest
    rm -rf ${WORKON_HOME}/tempest/build
    cd /tmp/tempest
    pip install -e .
    pip install sqlalchemy
    if [[ "$?" != "0" ]]; then
        echo "failed to install tempest project"
        deactivate
        exit 1
    else
        echo "install tempest project succeeded"
        deactivate
    fi
fi

source `which virtualenvwrapper.sh`
if ! lsvirtualenv |grep compass-core>/dev/null; then
    mkvirtualenv --system-site-packages compass-core
fi
cd $COMPASSDIR
workon compass-core
easy_install --upgrade pip
rm -rf ${WORKON_HOME}/compass-core/build
echo "install compass requirements"
pip install -U -r requirements.txt
if [[ "$?" != "0" ]]; then
    echo "failed to install compass requiremnts"
    deactivate
    exit 1
fi
pip install -U -r test-requirements.txt
if [[ "$?" != "0" ]]; then
    echo "failed to install compass test requiremnts"
    deactivate
    exit 1
else
    echo "intall compass requirements succeeded"
    deactivate
fi


# download cobbler related packages
if [[ $SUPPORT_CENTOS_7_2 == "y" ]]; then
    download -u $CENTOS_7_2_PPA_REPO_SOURCE || exit $?
fi

if [[ $SUPPORT_UBUNTU_14_04_03 == "y" ]]; then
    download -u $UBUNTU_14_04_03_PPA_REPO_SOURCE || exit $?
fi

# download chef related packages
# download -u "$CHEF_SRV" -u "$CHEF_SRV_HUAWEI" || exit $?
# download -u "$CHEF_CLIENT" -u "$CHEF_CLIENT_HUAWEI" || exit $?

# download os images
if [[ $SUPPORT_CENTOS_7_2 == "y" ]]; then
    download -u "$CENTOS_7_2_IMAGE_SOURCE" || exit $?
fi

if [[ $SUPPORT_UBUNTU_14_04_03 == "y" ]]; then
    download -u "$UBUNTU_14_04_03_IMAGE_SOURCE" || exit $?
fi

# Install net-snmp
echo "install snmp config"
if [[ ! -e /etc/snmp ]]; then
    sudo mkdir -p /etc/snmp
fi
if [[ -e /etc/snmp/snmp.conf ]]; then
    sudo cp -rn /etc/snmp/snmp.conf /root/backup/
    sudo rm -f /etc/snmp/snmp.conf
fi
sudo mkdir -p /usr/local/share/snmp/
sudo cp -rf $COMPASSDIR/mibs /usr/local/share/snmp/
sudo cp -rf $COMPASSDIR/misc/snmp/snmp.conf /etc/snmp/snmp.conf
sudo chmod 644 /etc/snmp/snmp.conf
sudo mkdir -p /var/lib/net-snmp/mib_indexes
sudo chmod 755 /var/lib/net-snmp/mib_indexes

# generate ssh key
echo "generate ssh key"
if [[ ! -e $HOME/.ssh ]]; then
    sudo mkdir -p $HOME/.ssh
fi
if [ ! -e $HOME/.ssh/id_rsa.pub ]; then
    rm -rf $HOME/.ssh/id_rsa
    ssh-keygen -t rsa -f $HOME/.ssh/id_rsa -q -N ''
fi
