#!/bin/bash

echo 'Installing Required packages for Compass...'
sudo yum clean all
sudo yum update -y --skip-broken
if [ "$tempest" == "true" ]; then
    sudo yum install -y virt-install libvirt qemu-kvm libxml2-devel libffi-devel libxslt-devel python-devel sshpass openssl-devel
fi
sudo yum install -y rsyslog logrotate ntp iproute openssh-clients python python-devel git wget python-setuptools syslinux python-netaddr python-flask python-flask-sqlalchemy python-amqplib amqp python-paramiko python-mock mod_wsgi httpd squid dhcp bind rsync yum-utils xinetd tftp-server gcc net-snmp-utils net-snmp net-snmp-python python-daemon unzip openssl openssl098e ca-certificates redis python-redis --skip-broken
if [[ "$?" != "0" ]]; then
    echo "failed to install yum dependency"
    exit 1
fi

# https need the system time is correct.
sudo service ntpd stop
ntpdate 0.centos.pool.ntp.org
sudo service ntpd start

sudo easy_install --upgrade pip==1.5.1
if [[ "$?" != "0" ]]; then
    echo "failed to install easy install"
    exit 1
fi

if [ "$tempest" == "true" ]; then
    sudo pip install -U setuptools 
    sudo pip install -U setuptools
fi
sudo pip install -r $COMPASSDIR/requirements.txt
sudo pip install -r $COMPASSDIR/test-requirements.txt
if [[ "$?" != "0" ]]; then
    echo "failed to install pip packages"
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
