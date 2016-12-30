#!/bin/bash
#
# set -x
### Log the script outputs locally
exec > >(sudo tee standalone_server.log)
exec 2>&1

### Lock to prevent running multiple instances of the script.
LOCKFILE="/tmp/`basename $0`"
LOCKFD=99

if [ -f $LOCKFILE ]; then
    LOCKED_PID=$(cat $LOCKFILE | head -n 1)
    ps -p $LOCKED_PID &> /dev/null
    if [[ "$?" != "0" ]]; then
        echo "the progress of pid $LOCKED_PID does not exist: `ps -p $LOCKED_PID`"
        rm -f $LOCKFILE
    else
        echo "the progress of pid $LOCKED_PID is running: `ps -p $LOCKED_PID`"
        exit 1
    fi
else
    echo "$LOCKFILE does not exist"
fi

# PRIVATE
_lock()
{
    echo "lock $LOCKFILE"
    flock -$1 $LOCKFD
    pid=$$
    echo $pid 1>& $LOCKFD
}

_no_more_locking()
{
    _lock u
    _lock xn && rm -f $LOCKFILE
}

_prepare_locking()
{
    eval "exec $LOCKFD>\"$LOCKFILE\""
    trap _no_more_locking EXIT
}

# ON START
_prepare_locking

# PUBLIC

exlock_now()
{
    _lock xn || exit 1
}  # obtain an exclusive lock immediately or fail

exlock_now
if [[ "$?" != "0" ]]; then
    echo "failed to acquire lock $LOCKFILE"
    exit 1
fi

### Script Begins Here

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

### Load config
source $DIR/standalone_server.conf
### Load functions
source $DIR/install_func.sh

### Change selinux security policy
sudo setenforce 0
sudo sed -i 's/enforcing/disabled/g' /etc/selinux/config

### Add epel repo
sudo rpm -q epel-release
if [ "$?" != "0" ]; then
    sudo rpm -Uvh $EPEL
    if [ "$?" != "0" ]; then
        echo "failed to install epel-release"
        exit 1
    else
        echo "sucessfaully installed epel-release"
    fi
else
    echo "epel-release is already installed"
fi

sed -i 's/^mirrorlist=https/mirrorlist=http/g' /etc/yum.repos.d/epel.repo

sudo rpm -q atomic-release
if [ "$?" == "0" ]; then
    sudo rpm -e atomic-release
fi

### Add remi repo
sudo rpm -q remi-release
if [ "$?" != "0" ]; then
    sudo rpm -Uvh $REMI >& /dev/null
    if [ "$?" != "0" ]; then
        echo "failed to install remi-release"
        exit 1
    else
        echo "successfully installed remi-release"
    fi
else
    echo "remi-release is already installed"
fi

### Trap any error code with related filename and line.
errtrap()
{
    FILE=${BASH_SOURCE[1]:-$BASH_SOURCE[0]}
    echo "[FILE: "$(basename $FILE)", LINE: $1] Error: Command or function exited with status $2"
}

if [[ "$-" == *x* ]]; then
trap 'errtrap $LINENO $?' ERR
fi

sudo yum -y install figlet >& /dev/null
figlet -ctf slant Compass Standalone Web-Server

sudo yum update -y

# assign all necessary values.
export WEB_SOURCE=${WEB_SOURCE:-"http://git.openstack.org/openstack/compass-web"}

rm -rf /etc/yum.repos.d/compass_install.repo 2>/dev/nullcp 
cp ${COMPASSDIR}/misc/compass_install.repo /etc/yum.repos.d/

# Start: install required packages and dependencies
sudo yum --enablerepo=compass_install install -y $MYSQL
sudo yum --enablerepo=compass_install --nogpgcheck install -y rsyslog logrotate ntp python python-devel git wget syslinux amqp mod_wsgi httpd bind rsync yum-utils gcc unzip openssl openssl098e ca-certificates mysql-devel mysql-server mysql MySQL-python python-virtualenv python-setuptools python-pip bc libselinux-python libffi-devel openssl-devel rabbitmq-server
sudo yum --setopt=tsflags=noscripts -y remove redis
sudo yum --enablerepo=compass_install --nogpgcheck install -y redis
if [[ "$?" != "0" ]]; then
    echo "failed to install yum dependency"
    exit 1
fi

# sync system time
sudo service ntpd stop
ntpdate 0.centos.pool.ntp.org
sudo service ntpd start
sudo sleep 10
sudo service ntpd status
if [[ "$?" != "0" ]]; then
    echo "ntpd is not started"
    exit 1
fi

# Disable firewalld
sudo systemctl stop firewalld.service

sudo easy_install --upgrade pip
sudo pip install --upgrade pip
sudo pip install --upgrade setuptools
sudo pip install --upgrade virtualenv
if [[ "$?" != "0" ]]; then
    echo "failed to install easy install and pip."
    exit 1
fi

sudo pip install virtualenvwrapper
if [[ "$?" != "0" ]]; then
    echo "failed to install virtualenvwrapper"
    exit 1
fi

sudo systemctl enable httpd.service
sudo systemctl enable sshd.service
sudo systemctl enable rsyslog.service
sudo systemctl enable ntpd.service
sudo systemctl enable redis.service
sudo systemctl enable mysqld.service
sudo systemctl enable rabbitmq.service
# Finish: dependency and package install finished.

# Start: prepare installation

# Crate backup dir
sudo mkdir -p /root/backup

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

# update httpd
echo "update httpd"
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

# update mysqld
echo "update mysqld"
mkdir -p /var/log/mysql
chmod -R 777 /var/log/mysql
sleep 10
sudo systemctl restart mysql.service
sudo sleep 10
sudo systemctl status mysql.service
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
sudo mysql -h${MYSQL_SERVER} --port=${MYSQL_PORT} -u${MYSQL_USER} -p${MYSQL_PASSWORD} -e "GRANT ALL PRIVILEGES ON *.* TO '$MYSQL_USER'@'%' IDENTIFIED BY '$MYSQL_PASSWORD'"
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

# Get websource now
if [ -z $WEB_SOURCE ]; then
    echo "web source $WEB_SOURCE is not set"
    exit 1
fi
copy2dir "$WEB_SOURCE" "$WEB_HOME" || exit $?

# Set up virtualenv
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
pip install -U boto
if [[ "$?" != "0" ]]; then
    echo "failed to install compass test requiremnts"
    deactivate
    exit 1
else
    echo "intall compass requirements succeeded"
    deactivate
fi

# Setup compass web components
sudo mkdir -p /var/www/compass_web
sudo rm -rf /var/www/compass_web/*

sudo mkdir -p /var/www/compass_web/v2.5
sudo cp -rf $WEB_HOME/v2.5/target/* /var/www/compass_web/v2.5/

sudo systemctl restart httpd.service
sleep 10

echo "Checking if httpd is running"
sudo systemctl status httpd.service
if [[ "$?" == "0" ]]; then
    echo "httpd is running"
else
    echo "httpd is not running"
    exit 1
fi

## Setup compass server
cd $SCRIPT_DIR

sudo mkdir -p /etc/compass
sudo rm -rf /etc/compass/*
sudo mkdir -p /opt/compass/bin
sudo rm -rf /opt/compass/bin/*
sudo mkdir -p /var/log/compass
sudo rm -rf /var/log/compass/*
sudo mkdir -p /var/www/compass
sudo rm -rf /var/www/compass/*

sudo cp -rf $COMPASSDIR/misc/apache/ods-server.conf /etc/httpd/conf.d/ods-server.conf
sudo cp -rf $COMPASSDIR/misc/apache/http_pip.conf /etc/httpd/conf.d/http_pip.conf
sudo cp -rf $COMPASSDIR/misc/apache/images.conf /etc/httpd/conf.d/images.conf
sudo cp -rf $COMPASSDIR/misc/apache/packages.conf /etc/httpd/conf.d/packages.conf
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

sudo usermod -a -G `groups $USER|awk '{print$3}'` apache

# setup ods server
if [ ! -f /usr/lib64/libcrypto.so ]; then
    sudo cp -rf /usr/lib64/libcrypto.so.6 /usr/lib64/libcrypto.so
fi

download -u "$PIP_PACKAGES"  `basename $PIP_PACKAGES` unzip /var/www/ || exit $?
download -u "$EXTRA_PACKAGES" `basename $EXTRA_PACKAGES` unzip /var/www/ || exit $?

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

udo sed -i "s/\$ipaddr/$IPADDR/g" /etc/compass/setting
sudo sed -i "s/\$hostname/$HOSTNAME/g" /etc/compass/setting
sudo sed -i "s/\$gateway/$OPTION_ROUTER/g" /etc/compass/setting
domains=$(echo $NAMESERVER_DOMAINS | sed "s/,/','/g")
sudo sed -i "s/\$domains/$domains/g" /etc/compass/setting
sudo sed -i "/DATABASE_SERVER =/c\DATABASE_SERVER = '127.0.0.1:3306'" /etc/compass/setting
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
sudo mv /etc/compass/celeryconfig_local /etc/compass/celeryconfig
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

figlet -ctf slant Standalone Server Installation Complete!
echo -e "It takes\x1b[32m $SECONDS \x1b[0mseconds during the installation."
