#!/bin/bash

echo 'Installing Required packages for Compass...'

sudo yum install -y rsyslog ntp iproute openssh-clients python git wget python-setuptools python-netaddr python-flask python-flask-sqlalchemy python-amqplib amqp python-paramiko python-mock mod_wsgi httpd squid dhcp bind rsync yum-utils xinetd tftp-server gcc net-snmp-utils net-snmp python-daemon

sudo easy_install pip==1.2.1
sudo pip install flask-script flask-restful Celery six discover unittest2 pychef

sudo chkconfig httpd on
sudo chkconfig squid on
sudo chkconfig xinetd on
sudo chkconfig dhcpd on
sudo chkconfig named on
sudo chkconfig sshd on
sudo chkconfig rsyslog on
sudo chkconfig ntpd on
sudo chkconfig iptables off
sudo chkconfig ip6tables off
