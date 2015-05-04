#!/bin/bash
#

SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
if [ -f $HOME/VirtualBox\ VMs/compass-server ];then
    mkdir -p $HOME/VirtualBox VMs/compass-server
fi

VBoxManage hostonlyif create
VBoxManage hostonlyif create > $HOME/adapter1info
export adapter1=`cut -d\' -f2 $HOME/adapter1info`
VBoxManage hostonlyif ipconfig $adapter1 --ip "192.168.33.1" --netmask "255.255.255.0"

VBoxManage hostonlyif create > $HOME/adapter2info
export adapter2=`cut -d\' -f2 $HOME/adapter2info`
VBoxManage hostonlyif ipconfig $adapter2 --ip "172.16.10.1" --netmask "255.255.255.0"

VBoxManage createvm --name controller --ostype Linux_64 --register
VBoxManage createvm --name compute --ostype Linux_64 --register
VBoxManage createvm --name network --ostype Linux_64 --register
VBoxManage createvm --name storage --ostype Linux_64 --register

# controller
VBoxManage modifyvm controller --memory 2048 --nic1 hostonly --hostonlyadapter1 $adapter1 --macaddress1 000102030405 --nic2 hostonly --hostonlyadapter2 $adapter2 --nicpromisc2 allow-vms --macaddress2 000120295BFA --vram 12 --boot1 net --boot2 disk
VBoxManage createhd --filename "$HOME/VirtualBox VMs/controller/controller.vdi" --size 32768
VBoxManage storagectl controller --name "controller-IDE" --add ide
VBoxManage storageattach controller --storagectl "controller-IDE" --port 0 --device 0 --type hdd --medium "$HOME/VirtualBox VMs/controller/controller.vdi"

# compute
VBoxManage modifyvm compute --memory 3072 --nic1 hostonly --hostonlyadapter1 $adapter1 --macaddress1 000102030406 --nic2 hostonly --hostonlyadapter2 $adapter2 --nicpromisc2 allow-vms --macaddress2 000120295BFB --vram 12 --boot1 net --boot2 disk
VBoxManage createhd --filename "$HOME/VirtualBox VMs/compute/compute.vdi" --size 16384
VBoxManage storagectl compute --name "compute-IDE" --add ide
VBoxManage storageattach compute --storagectl "compute-IDE" --port 0 --device 0 --type hdd --medium "$HOME/VirtualBox VMs/compute/compute.vdi"

# network
VBoxManage modifyvm network --memory 2048 --nic1 hostonly --hostonlyadapter1 $adapter1 --macaddress1 000102030407 --nic2 hostonly --hostonlyadapter2 $adapter2 --nicpromisc2 allow-vms --macaddress2 000120295BFC --vram 12 --boot1 net --boot2 disk
VBoxManage createhd --filename "$HOME/VirtualBox VMs/network/network.vdi" --size 16384
VBoxManage storagectl network --name "network-IDE" --add ide
VBoxManage storageattach network --storagectl "network-IDE" --port 0 --device 0 --type hdd --medium "$HOME/VirtualBox VMs/network/network.vdi"

# storage
VBoxManage modifyvm storage --memory 2048 --nic1 hostonly --hostonlyadapter1 $adapter1 --macaddress1 000102030408 --nic2 hostonly --hostonlyadapter2 $adapter2 --nicpromisc2 allow-vms --macaddress2 000120295BFD --vram 12 --boot1 net --boot2 disk
VBoxManage createhd --filename "$HOME/VirtualBox VMs/storage/storage.vdi" --size 32768
VBoxManage storagectl storage --name "storage-IDE" --add ide
VBoxManage storageattach storage --storagectl "storage-IDE" --port 0 --device 0 --type hdd --medium "$HOME/VirtualBox VMs/storage/storage.vdi"

# compass
# get latest ansible code
cd $SCRIPT_DIR
git clone -b dev/experimental git://git.openstack.org/stackforge/compass-adapters.git
cp -r compass-adapters/ansible/openstack_juno compass-adapters/ansible/openstack_juno_plumgrid
vagrant box list |grep compass
if [ "$?" != "0" ]; then
vagrant box add compass https://atlas.hashicorp.com/compass-dev/boxes/compass/versions/0.0.1/providers/compass.box
fi
vagrant up --provision
