#!/bin/bash

echo 'Installing Required packages for Compass...'
sudo yum clean all
sudo yum update -y --skip-broken
if [ "$tempest" == "true" ]; then
    sudo yum install -y virt-install libvirt qemu-kvm libxml2-devel libffi-devel libxslt-devel python-devel sshpass openssl-devel
    if [[ "$?" != "0" ]]; then
        echo "failed to install tempest yum dependency"
        exit 1
    fi
fi
sudo yum install -y rsyslog logrotate ntp iproute openssh-clients python python-devel git wget syslinux amqp mod_wsgi httpd squid dhcp bind rsync yum-utils xinetd tftp-server gcc net-snmp-utils net-snmp net-snmp-python unzip openssl openssl098e ca-certificates redis mysql mysql-server mysql-devel python-virtualenv python-setuptools
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

sudo pip install virtualenvwrapper

sudo chkconfig httpd on
sudo chkconfig squid on
sudo chkconfig xinetd on
sudo chkconfig dhcpd on
sudo chkconfig named on
sudo chkconfig sshd on
sudo chkconfig rsyslog on
sudo chkconfig ntpd on
sudo chkconfig redis on
sudo chkconfig mysqld on
sudo chkconfig iptables off
sudo chkconfig ip6tables off
