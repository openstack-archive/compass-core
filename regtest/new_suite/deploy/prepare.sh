#!/bin/bash
##############################################################################
# Copyright (c) 2016 HUAWEI TECHNOLOGIES CO.,LTD and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
function print_logo()
{
    if ! apt --installed list 2>/dev/null | grep "figlet"
    then
        sudo apt-get update -y
        sudo apt-get install -y --force-yes figlet
    fi

    figlet -ctf slant Compass Installer
    set +x; sleep 2; set -x
}

function download_iso()
{
    iso_name=`basename $ISO_URL`
    rm -f $WORK_DIR/cache/"$iso_name.md5"
    curl --connect-timeout 10 -o $WORK_DIR/cache/"$iso_name.md5" $ISO_URL.md5
    if [[ -f $WORK_DIR/cache/$iso_name ]]; then
        local_md5=`md5sum $WORK_DIR/cache/$iso_name | cut -d ' ' -f 1`
        repo_md5=`cat $WORK_DIR/cache/$iso_name.md5 | cut -d ' ' -f 1`
        if [[ "$local_md5" == "$repo_md5" ]]; then
            return
        fi
    fi

    curl --connect-timeout 10 -o $WORK_DIR/cache/$iso_name $ISO_URL
}

function prepare_env() {
    export PYTHONPATH=/usr/lib/python2.7/dist-packages:/usr/local/lib/python2.7/dist-packages
    sudo apt-get update -y
    sudo apt-get install -y --force-yes mkisofs bc curl ipmitool openvswitch-switch
    sudo apt-get install -y --force-yes git python-dev
    sudo apt-get install -y --force-yes libxslt-dev libxml2-dev libvirt-dev build-essential qemu-utils qemu-kvm libvirt-bin virtinst libmysqld-dev
    sudo service libvirt-bin restart

    # prepare work dir
    rm -rf $WORK_DIR/{installer,vm,network,iso}
    mkdir -p $WORK_DIR/installer
    mkdir -p $WORK_DIR/vm
    mkdir -p $WORK_DIR/network
    mkdir -p $WORK_DIR/iso
    mkdir -p $WORK_DIR/cache

    download_iso

    cp $WORK_DIR/cache/`basename $ISO_URL` $WORK_DIR/iso/centos.iso -f

    # copy compass
    mkdir -p $WORK_DIR/mnt
    sudo mount -o loop $WORK_DIR/iso/centos.iso $WORK_DIR/mnt
    cp -rf $WORK_DIR/mnt/compass/compass-core $WORK_DIR/installer/
    cp -rf $WORK_DIR/mnt/compass/compass-install $WORK_DIR/installer/
    sudo umount $WORK_DIR/mnt
    rm -rf $WORK_DIR/mnt

    chmod 755 $WORK_DIR -R

    sudo cp ${COMPASS_DIR}/deploy/qemu_hook.sh /etc/libvirt/hooks/qemu
}

function  prepare_python_env() {
   rm -rf $WORK_DIR/venv
   mkdir -p $WORK_DIR/venv

   sudo apt-get install -y --force-yes python-pip
   sudo pip install --upgrade virtualenv
   virtualenv $WORK_DIR/venv
   source $WORK_DIR/venv/bin/activate

   pip install --upgrade pip
   pip install --upgrade cheetah
   pip install --upgrade pyyaml
   pip install --upgrade requests
   pip install --upgrade netaddr
   pip install --upgrade oslo.config
   pip install --upgrade ansible==1.9.4
}
