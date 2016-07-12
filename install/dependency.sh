#!/bin/bash

echo 'Installing Required packages for Compass...'
sudo yum clean all
sudo yum update -y --skip-broken
if [ "$tempest" == "true" ]; then
    sudo yum --enablerepo=compass_install install -y virt-install libvirt qemu-kvm libxml2-devel libffi-devel libxslt-devel python-devel sshpass openssl-devel --nogpgcheck
    if [[ "$?" != "0" ]]; then
        echo "failed to install tempest yum dependency"
        exit 1
    fi
fi

if [ "$FULL_COMPASS_SERVER" == "true" ]; then
    sudo yum --enablerepo=compass_install install -y $MYSQL
    sudo yum --enablerepo=compass_install --nogpgcheck install -y rsyslog logrotate ntp iproute openssh-clients python python-devel git wget syslinux amqp rabbitmq-server mod_wsgi httpd squid dhcp bind rsync yum-utils xinetd tftp-server gcc net-snmp-utils net-snmp net-snmp-python unzip openssl openssl098e ca-certificates mysql-devel mysql-server mysql MySQL-python python-virtualenv python-setuptools python-pip bc libselinux-python libffi-devel openssl-devel
else
    sudo yum --enablerepo=compass_install --nogpgcheck install -y rsyslog logrotate ntp iproute openssh-clients python python-devel git wget syslinux amqp httpd dhcp bind rsync yum-utils xinetd tftp-server gcc net-snmp-utils net-snmp net-snmp-python unzip openssl openssl098e ca-certificates mysql-devel mysql MySQL-python python-virtualenv python-setuptools python-pip bc libselinux-python libffi-devel openssl-devel
fi
sudo yum --setopt=tsflags=noscripts -y remove redis
# sudo yum --enablerepo=remi,remi-test install -y redis
sudo yum --enablerepo=compass_install --nogpgcheck install -y redis

if [[ "$?" != "0" ]]; then
    echo "failed to install yum dependency"
    exit 1
fi

# https need the system time is correct.
sudo service ntpd stop
ntpdate 0.centos.pool.ntp.org
sudo service ntpd start
sudo sleep 10
sudo service ntpd status
if [[ "$?" != "0" ]]; then
    echo "ntpd is not started"
    exit 1
fi

sudo easy_install --upgrade pip
sudo pip install --upgrade pip
sudo pip install --upgrade setuptools
sudo pip install --upgrade virtualenv
if [[ "$?" != "0" ]]; then
    echo "failed to install easy install"
    exit 1
fi

sudo pip install virtualenvwrapper
if [[ "$?" != "0" ]]; then
    echo "failed to install virtualenvwrapper"
    exit 1
fi

sudo systemctl enable httpd.service
sudo systemctl enable squid.service
sudo systemctl enable xinetd.service
sudo systemctl enable dhcpd.service
sudo systemctl enable named.service
sudo systemctl enable sshd.service
sudo systemctl enable rsyslog.service
sudo systemctl enable ntpd.service
sudo systemctl enable redis.service
if [ "$FULL_COMPASS_SERVER" == "true" ]; then
    sudo systemctl enable mysqld.service
    sudo systemctl enable rabbitmq-server.service
fi
