#!/bin/bash -x
# create a bridge named 'installation' so that compass and pxeboot vm are in the
# same l2 network.
brctl show |grep installation > /dev/null
if [[ $? -eq 0 ]] ; then
    echo "bridge already exists"
else
    brctl addbr installation
    brctl addif installation eth1
    ifconfig eth1 up
    dhclient -r eth1
    dhclient -r installation
    dhclient installation
fi
# kill the dhcp service started by libvirt to avoid conflict with dhcpd
killall dnsmasq
source compass-core/install/install.conf.template
/bin/bash -x compass-core/install/install.sh || exit $?
echo "cache_peer 10.145.81.137       parent    3128  3130  default" >> /etc/squid/squid.conf
service squid restart
service squid status |grep running || exit $?
sleep 5
