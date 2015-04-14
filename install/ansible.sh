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
sudo cp -rf $ADAPTERS_HOME/ansible/* /var/ansible/
