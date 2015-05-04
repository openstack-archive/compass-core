#!/bin/bash
#

VBoxManage unregistervm controller --delete
VBoxManage unregistervm compute --delete
VBoxManage unregistervm network --delete
VBoxManage unregistervm storage --delete
vagrant destroy -f
hostonlyifs=$(VBoxManage list hostonlyifs|grep '\ vboxnet'| awk -F ' ' '{print $2}')
for hostonlyif in $hostonlyifs
do
    VBoxManage hostonlyif remove $hostonlyif
done
rm -rf $HOME/VirtualBox VMs/*
