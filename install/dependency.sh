#!/bin/bash

echo 'Installing Required packages for Compass...'
sudo yum update -y
if [ "$tempest" == "true" ]; then
    sudo yum install -y virt-install libvirt qemu-kvm libxml2-devel libxslt-devel python-devel sshpass openssl-devel
fi
sudo yum install -y rsyslog logrotate ntp iproute openssh-clients python python-devel git wget python-setuptools python-netaddr python-flask python-flask-sqlalchemy python-amqplib amqp python-paramiko python-mock mod_wsgi httpd squid dhcp bind rsync yum-utils xinetd tftp-server gcc net-snmp-utils net-snmp net-snmp-python python-daemon unzip openssl openssl098e ca-certificates redis python-redis
if [[ "$?" != "0" ]]; then
    echo "failed to install yum dependency"
    exit 1
fi

sudo service ntpd stop
ntpdate 0.centos.pool.ntp.org
sudo serviced ntpd start

sudo easy_install --upgrade pip==1.5.1
if [[ "$?" != "0" ]]; then
    echo "failed to install easy install"
    exit 1
fi

if [ "$tempest" == "true" ]; then
    sudo pip install -U setuptools 
    sudo pip install -U setuptools
fi
sudo pip install -U -r $COMPASSDIR/requirements.txt
sudo pip install -U -r $COMPASSDIR/test-requirements.txt
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
