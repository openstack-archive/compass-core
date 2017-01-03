#!/bin/bash
#

echo "Installing Ansible"
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
source $DIR/install.conf
if [ -f $DIR/env.conf ]; then
    source $DIR/env.conf
else
    echo "failed to load environment"
    exit 1
fi
source $DIR/install_func.sh

echo "INstalling ansible related packages"
sudo yum -y install ansible
if [[ "$?" != "0" ]]; then
    echo "Failed to install ansible"
    exit 1
fi

sudo mkdir -p /var/ansible/run
sudo mkdir -p /root/backup/ansible
sudo cp -rn /var/ansible/* /root/backup/ansible/

for i in `ls $ADAPTERS_HOME/ansible/ | grep "openstack_"`; do
    mkdir -p /var/ansible/$i
#    cp -rf $ADAPTERS_HOME/ansible/openstack/* /var/ansible/$i
    cp -rf $ADAPTERS_HOME/ansible/$i /var/ansible/
done

cp -rf $ADAPTERS_HOME/ansible/roles /var/ansible/

rm -rf /opt/openstack-ansible-modules
git clone $OPENSTACK_ANSIBLE_MODULE /opt/`basename $OPENSTACK_ANSIBLE_MODULE | sed 's/\.git//g'`
