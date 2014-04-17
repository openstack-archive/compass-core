#!/bin/bash -x
echo 0 > /selinux/enforce
yum -y update
sed -i "s/Defaults    requiretty/#Defaults    requiretty/"  /etc/sudoers
git clone http://git.openstack.org/stackforge/compass-core
cd compass-core
source install/install.conf.template
source install/install.conf
export tempest=true
source install/dependency.sh
source install/prepare.sh
service libvirtd start
sync
sleep 5
echo "image preparation done"
