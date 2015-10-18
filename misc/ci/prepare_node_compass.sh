#!/bin/bash -x
echo 0 > /selinux/enforce
yum clean all
yum -y update --skip-broken
yum install -y virt-install libvirt qemu-kvm figlet rsyslog logrotate iproute openssh-clients python git wget python-setuptools python-netaddr python-flask python-flask-sqlalchemy python-amqplib amqp python-paramiko python-mock dhcp bind rsync yum-utils xinetd tftp-server gcc net-snmp-utils net-snmp net-snmp-python python-daemon unzip openssl openssl098e createrepo mkisofs python-cheetah python-simplejson python-urlgrabber PyYAML Django cman debmirror pykickstart libxml2-devel libxslt-devel python-devel sshpass bc
service libvirtd start
sed -i "s/Defaults    requiretty/#Defaults    requiretty/"  /etc/sudoers
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
git clone http://git.openstack.org/openstack/compass-core -b dev/experimental ||exit $?
cd compass-core
source install/install.conf.template
source install/install.conf
source install/setup_env.sh
source install/dependency.sh
source install/prepare.sh
sync
sleep 5
echo "image preparation done"
