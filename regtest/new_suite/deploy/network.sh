#!/bin/bash
##############################################################################
# Copyright (c) 2016 HUAWEI TECHNOLOGIES CO.,LTD and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
function clear_forward_rejct_rules()
{
    while sudo iptables -nL FORWARD --line-number|grep -E 'REJECT +all +-- +0.0.0.0/0 +0.0.0.0/0 +reject-with icmp-port-unreachable'|head -1|awk '{print $1}'|xargs sudo iptables -D FORWARD; do :; done
}

function setup_bridge_net()
{
    net_name=$1
    nic=$2

    sudo virsh net-destroy $net_name
    sudo virsh net-undefine $net_name

    sed -e "s/REPLACE_NAME/$net_name/g" \
        -e "s/REPLACE_NIC/$nic/g" \
    $COMPASS_DIR/deploy/template/network/bridge_nic.xml \
    > $WORK_DIR/network/$net_name.xml

    sudo virsh net-define $WORK_DIR/network/$net_name.xml
    sudo virsh net-start $net_name
}

function save_network_info()
{
    sudo ovs-vsctl list-br |grep br-external
    br_exist=$?
    external_nic=`ip route |grep '^default'|awk '{print $NF}'`
    route_info=`ip route |grep -Eo '^default via [^ ]+'`
    ip_info=`ip addr show $external_nic|grep -Eo '[^ ]+ brd [^ ]+ '`
    if [ $br_exist -eq 0 ]; then
        if [ "$external_nic" != "br-external" ]; then
            sudo ovs-vsctl --may-exist add-port br-external $external_nic
            sudo ip addr flush $external_nic
            sudo ip addr add $ip_info dev br-external
            sudo ip route add $route_info dev br-external
        fi
    else
        sudo ovs-vsctl add-br br-external
        sudo ovs-vsctl add-port br-external $external_nic
        sudo ip addr flush $external_nic
        sudo ip addr add $ip_info dev br-external
        sudo ip route add $route_info dev br-external
    fi
}

function setup_bridge_external()
{
    sudo virsh net-destroy external
    sudo virsh net-undefine external

    save_network_info
    sed -e "s/REPLACE_NAME/external/g" \
        -e "s/REPLACE_OVS/br-external/g" \
    $COMPASS_DIR/deploy/template/network/bridge_ovs.xml \
    > $WORK_DIR/network/external.xml

    sudo virsh net-define $WORK_DIR/network/external.xml
    sudo virsh net-start external

    python $COMPASS_DIR/deploy/setup_vnic.py
}

function setup_nat_net() {
    net_name=$1
    gw=$2
    mask=$3
    ip_start=$4
    ip_end=$5

    sudo virsh net-destroy $net_name
    sudo virsh net-undefine $net_name
    # create install network
    sed -e "s/REPLACE_BRIDGE/br_$net_name/g" \
        -e "s/REPLACE_NAME/$net_name/g" \
        -e "s/REPLACE_GATEWAY/$gw/g" \
        -e "s/REPLACE_MASK/$mask/g" \
        -e "s/REPLACE_START/$ip_start/g" \
        -e "s/REPLACE_END/$ip_end/g" \
        $COMPASS_DIR/deploy/template/network/nat.xml \
        > $WORK_DIR/network/$net_name.xml

    sudo virsh net-define $WORK_DIR/network/$net_name.xml
    sudo virsh net-start $net_name
}

function create_nets() {
    setup_nat_net mgmt $MGMT_GW $MGMT_MASK $MGMT_IP_START $MGMT_IP_END

    # create install network
    if [[ -n $INSTALL_NIC ]]; then
        setup_bridge_net install $INSTALL_NIC
    else
        setup_nat_net install $INSTALL_GW $INSTALL_MASK
    fi

    # create external network
    setup_bridge_external
    clear_forward_rejct_rules
}
