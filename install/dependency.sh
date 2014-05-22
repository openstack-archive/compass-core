#!/bin/bash

echo 'Installing Required packages for Compass...'
sudo yum clean all
sudo yum update -y
if [ "$tempest" == "true" ]; then
    sudo yum install -y virt-install libvirt qemu-kvm libxml2-devel libffi-devel libxslt-devel python-devel sshpass openssl-devel
    if [[ "$?" != "0" ]]; then
        echo "failed to install tempest yum dependency"
        exit 1
    fi
fi
sudo yum install -y rsyslog logrotate ntp iproute openssh-clients python python-devel git wget python-setuptools syslinux python-netaddr python-flask python-flask-sqlalchemy python-amqplib python-argparse amqp python-paramiko python-mock mod_wsgi httpd squid dhcp bind rsync yum-utils xinetd tftp-server gcc net-snmp-utils net-snmp net-snmp-python python-daemon unzip openssl openssl098e ca-certificates redis python-redis python-importlib
if [[ "$?" != "0" ]]; then
    echo "failed to install yum dependency"
    exit 1
fi

# https need the system time is correct.
sudo service ntpd stop
ntpdate 0.centos.pool.ntp.org
sudo service ntpd start
sudo service ntpd status
if [[ "$?" != "0" ]]; then
    echo "ntpd is not started"
    exit 1
fi

sudo easy_install --upgrade pip
if [[ "$?" != "0" ]]; then
    echo "failed to install easy install"
    exit 1
fi

# pip install flask-sqlalchemy need to remove /usr/lib64/python2.6/site-packages/easy-install.pth 
cp -n /usr/lib/python2.6/site-packages/easy-install* /usr/lib64/python2.6/site-packages/

sudo pip install -U setuptools
if [[ "$?" != "0" ]]; then
    echo "failed to install setuptools"
    exit 1 
fi

# TODO: (fixme). setuptools should be installed twice. One is to uninstall distribute, the other is to upgrade setuptools.
 sudo pip install -U setuptools
if [[ "$?" != "0" ]]; then
    echo "failed to install setuptools"
    exit 1 
fi

sudo pip install -U -r $COMPASSDIR/requirements.txt
if [[ "$?" != "0" ]]; then
    echo "failed to install compass requirement packages"
    exit 1
fi

sudo pip install -U -r $COMPASSDIR/test-requirements.txt
if [[ "$?" != "0" ]]; then
    echo "failed to install compass test require packages"
    exit 1
fi

sudo chkconfig httpd on
sudo chkconfig squid on
sudo chkconfig xinetd on
sudo chkconfig dhcpd on
sudo chkconfig named on
sudo chkconfig sshd on
sudo chkconfig rsyslog on
sudo chkconfig ntpd on
sudo chkconfig redis on
sudo chkconfig iptables off
sudo chkconfig ip6tables off
