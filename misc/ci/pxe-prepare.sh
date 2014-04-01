#!/bin/bash -x
if [[ ! -e /tmp/pxe01.raw ]]; then
    qemu-img create -f raw /tmp/pxe01.raw 20G
else
    rm -rf /tmp/pxe01.raw
    qemu-img create -f raw /tmp/pxe01.raw 20G
fi
virsh list |grep pxe01
vmrc=$?
if [[ $vmrc -eq 0 ]] ; then
    virsh destroy pxe01
    virsh undefine pxe01
else
    echo "no legacy pxe vm found"
fi
virt-install --accelerate --hvm --connect qemu:///system \
    --network=bridge:installation,mac=00:11:20:30:40:01 --pxe \
    --network=network:default \
    --name pxe01 --ram=8192 \
    --disk /tmp/pxe01.raw,format=raw \
    --vcpus=10 \
    --graphics vnc,listen=0.0.0.0 --noautoconsole \
    --os-type=linux --os-variant=rhel6
rm -rf switch-file
echo "machine,10.145.81.220,5,1,00:11:20:30:40:01" > switch-file
echo "switch,10.145.81.220,huawei,v2c,public,under_monitoring" >> switch-file
/usr/bin/python /opt/compass/bin/manage_db.py set_switch_machines --switch_machines_file switch-file
/usr/bin/python /opt/compass/bin/manage_db.py clean_clusters
/usr/bin/python /opt/compass/bin/manage_db.py clean_installation_progress
