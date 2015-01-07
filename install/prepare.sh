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
sudo service ntpd stop
sudo ntpdate 0.centos.pool.ntp.org
sudo service ntpd start
sudo service ntpd status
if [[ "$?" != "0" ]]; then
    echo "ntp is not started"
    exit 1
else
    echo "ntp conf is updated"
fi

# update squid conf
echo "update squid config"
sudo cp -rn /etc/squid/squid.conf /root/backup/
sudo rm -f /etc/squid/squid.conf 
sudo cp $COMPASSDIR/misc/squid/squid.conf /etc/squid/
export netaddr=$(ipcalc $IPADDR $NETMASK -n |cut -f 2 -d '=')
export netprefix=$(ipcalc $IPADDR $NETMASK -p |cut -f 2 -d '=')
subnet=${netaddr}/${netprefix}
subnet_escaped=$(echo $subnet | sed -e 's/[\/&]/\\&/g')
sudo sed -i "s/acl localnet src \$subnet/acl localnet src $subnet_escaped/g" /etc/squid/squid.conf
sudo chmod 644 /etc/squid/squid.conf
sudo mkdir -p /var/squid/cache
sudo chown -R squid:squid /var/squid
sudo mkdir -p /var/log/squid
sudo chmod -R 777 /var/log/squid
sudo service squid restart
sudo service squid status
if [[ "$?" != "0" ]]; then
    echo "squid is not started"
    exit 1
else
    echo "squid conf is updated"
fi

mkdir -p /var/log/httpd
chmod -R 777 /var/log/httpd

mkdir -p /var/log/mysql
chmod -R 777 /var/log/mysql
sudo service httpd restart
sudo service httpd status
if [[ "$?" != "0" ]]; then
    echo "squid is not started"
    exit 1
else
    echo "squid conf is updated"
fi

#update mysqld
echo "update mysqld"
sudo service mysqld restart
sudo service mysqld status
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
else
    echo "mysql database set succeeded"
fi
sudo service mysqld restart
sudo service mysqld status
if [[ "$?" != "0" ]]; then
    echo "mysqld is not started"
    exit 1
else
    echo "mysqld is started"
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
copy2dir "$WEB_SOURCE" "$WEB_HOME" "stackforge/compass-web" || exit $?

if [ -z $ADAPTERS_SOURCE ]; then
    echo "adpaters source $ADAPTERS_SOURCE is not set"
    exit 1
fi
copy2dir "$ADAPTERS_SOURCE" "$ADAPTERS_HOME" "stackforge/compass-adapters" ${local_branch} || exit $?

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
# TODO: temporarily host the deprecated packages in huawei lab, will switch later.
# CENTOS_PPA_SOURCE=`fastesturl "http://mirrors.hustunique.com" "http://mirror.centos.org"`
CENTOS_PPA_SOURCE="http://huawei-repo.uubright.com/repos"
centos_ppa_repo_packages="
ntp-4.2.6p5-1.${CENTOS_IMAGE_TYPE_OTHER}${CENTOS_IMAGE_VERSION_MAJOR}.${CENTOS_IMAGE_TYPE,,}.${CENTOS_IMAGE_ARCH}.rpm
openssh-clients-5.3p1-94.${CENTOS_IMAGE_TYPE_OTHER}${CENTOS_IMAGE_VERSION_MAJOR}.${CENTOS_IMAGE_ARCH}.rpm
openssh-5.3p1-94.${CENTOS_IMAGE_TYPE_OTHER}${CENTOS_IMAGE_VERSION_MAJOR}.${CENTOS_IMAGE_ARCH}.rpm
iproute-2.6.32-31.${CENTOS_IMAGE_TYPE_OTHER}${CENTOS_IMAGE_VERSION_MAJOR}.${CENTOS_IMAGE_ARCH}.rpm
wget-1.12-1.8.${CENTOS_IMAGE_TYPE_OTHER}${CENTOS_IMAGE_VERSION_MAJOR}.${CENTOS_IMAGE_ARCH}.rpm
ntpdate-4.2.6p5-1.${CENTOS_IMAGE_TYPE_OTHER}${CENTOS_IMAGE_VERSION_MAJOR}.${CENTOS_IMAGE_TYPE,,}.${CENTOS_IMAGE_ARCH}.rpm
yum-plugin-priorities-1.1.30-14.${CENTOS_IMAGE_TYPE_OTHER}${CENTOS_IMAGE_VERSION_MAJOR}.noarch.rpm
parted-2.1-21.${CENTOS_IMAGE_TYPE_OTHER}${CENTOS_IMAGE_VERSION_MAJOR}.${CENTOS_IMAGE_ARCH}.rpm"

for f in $centos_ppa_repo_packages; do
    download $CENTOS_PPA_SOURCE/${CENTOS_IMAGE_TYPE,,}/${CENTOS_IMAGE_VERSION}/os/${CENTOS_IMAGE_ARCH}/Packages/$f $f || exit $?
done

centos_ppa_repo_rsyslog_packages="
json-c-0.10-2.${CENTOS_IMAGE_TYPE_OTHER}${CENTOS_IMAGE_VERSION_MAJOR}.${CENTOS_IMAGE_ARCH}.rpm
libestr-0.1.9-1.${CENTOS_IMAGE_TYPE_OTHER}${CENTOS_IMAGE_VERSION_MAJOR}.${CENTOS_IMAGE_ARCH}.rpm
libgt-0.3.11-1.${CENTOS_IMAGE_TYPE_OTHER}${CENTOS_IMAGE_VERSION_MAJOR}.${CENTOS_IMAGE_ARCH}.rpm
liblogging-1.0.4-1.${CENTOS_IMAGE_TYPE_OTHER}${CENTOS_IMAGE_VERSION_MAJOR}.${CENTOS_IMAGE_ARCH}.rpm
rsyslog-7.6.3-1.${CENTOS_IMAGE_TYPE_OTHER}${CENTOS_IMAGE_VERSION_MAJOR}.${CENTOS_IMAGE_ARCH}.rpm"

for f in $centos_ppa_repo_rsyslog_packages; do
    download http://rpms.adiscon.com/v7-stable/epel-${CENTOS_IMAGE_VERSION_MAJOR}/${CENTOS_IMAGE_ARCH}/RPMS/$f $f || exit $?
done

CENTOS_CHEF_CLIENT_SOURCE=`fastesturl "$CENTOS_CHEF_CLIENT" "$CENTOS_CHEF_CLIENT_HUAWEI"`
download $CENTOS_CHEF_CLIENT_SOURCE `basename $CENTOS_CHEF_CLIENT_SOURCE` || exit $?
UBUNTU_CHEF_CLIENT_SOURCE=`fastesturl "$UBUNTU_CHEF_CLIENT" "$UBUNTU_CHEF_CLIENT_HUAWEI"`
download $UBUNTU_CHEF_CLIENT_SOURCE `basename $UBUNTU_CHEF_CLIENT_SOURCE` || exit $?

# download chef related packages
CHEF_SRV_SOURCE=`fastesturl "$CHEF_SRV" "$CHEF_SRV_HUAWEI"`
download $CHEF_SRV_SOURCE chef-server || exit $?

# TODO: temporarily host the deprecated packages in huawei lab, will switch later.
# download os images
#CENTOS_ISO_SOURCE=`fastesturl $CENTOS_IMAGE_SOURCE $CENTOS_IMAGE_SOURCE_ASIA`
CENTOS_ISO_SOURCE="http://huawei-repo.uubright.com/repos/${CENTOS_IMAGE_TYPE,,}/${CENTOS_IMAGE_VERSION}/isos/${CENTOS_IMAGE_ARCH}/${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH}-minimal.iso"
download $CENTOS_ISO_SOURCE ${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH}.iso || exit $?

UBUNTU_ISO_SOURCE=`fastesturl $UBUNTU_IMAGE_SOURCE $UBUNTU_IMAGE_SOURCE_ASIA`
download $UBUNTU_ISO_SOURCE ${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH}.iso || exit $?

# download local repo
if [[ $LOCAL_REPO = "y" ]]; then
    LOCAL_REPO_SOURCE=`fastesturl $LOCAL_REPO_US $LOCAL_REPO_HUAWEI`
    download $LOCAL_REPO_SOURCE local_repo.tar.gz || exit $?
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
