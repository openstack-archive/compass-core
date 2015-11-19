
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
    setup_bridge_net external $EXTERNAL_NIC
}
