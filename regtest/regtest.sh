#!/bin/bash -x

function mac_address_part() {
    hex_number=$(printf '%02x' $RANDOM)
    number_length=${#hex_number}
    number_start=$(expr $number_length - 2)
    echo ${hex_number:$number_start:2}
}

function mac_address() {
    echo "00:00:$(mac_address_part):$(mac_address_part):$(mac_address_part):$(mac_address_part)"
}

REGTEST_CONF=${REGTEST_CONF:-"regtest.conf"}
REGTEST_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
source ${REGTEST_DIR}/${REGTEST_CONF}

declare -A roles_list
declare -A host_roles
machines_str=''

for roles in ${HOST_ROLES//;/ }; do
    roles_list[${#roles_list[@]}]=${roles}
done
echo "role list: ${roles_list[@]}"
roles_offset=0
host_roles_str=''

virtmachines=$(virsh list --name)
for virtmachine in $virtmachines; do
    echo "destroy $virtmachine"
    virsh destroy $virtmachine
    if [[ "$?" != "0" ]]; then
        echo "destroy instance $virtmachine failed"
        exit 1
    fi
done
virtmachines=$(virsh list --all --name)
for virtmachine in $virtmachines; do
    echo "undefine $virtmachine"
    virsh undefine $virtmachine
    if [[ "$?" != "0" ]]; then
        echo "undefine instance $virtmachine failed"
        exit 1
    fi
done

echo "setup $VIRT_NUM virt machines"
for i in `seq $VIRT_NUM`; do
    if [[ ! -e /tmp/pxe${i}.raw ]]; then
        echo "create image for instance pxe$i"
        qemu-img create -f raw /tmp/pxe${i}.raw ${VIRT_DISK}
        if [[ "$?" != "0" ]]; then
            echo "create image /tmp/pxe${i}.raw failed"
            exit 1
        fi 
    else
        echo "recreate image for instance pxe$i"
        rm -rf /tmp/pxe${i}.raw
        qemu-img create -f raw /tmp/pxe${i}.raw ${VIRT_DISK}
        if [[ "$?" != "0" ]]; then
            echo "create image /tmp/pxe${i}.raw failed"
            exit 1
        fi 
    fi
    mac=$(mac_address)
    echo "virt-install instance pxe$i on mac ${mac}"
    virt-install --accelerate --hvm --connect qemu:///system \
        --network=bridge:installation,mac=${mac} --pxe \
        --network=bridge:installation \
        --network=bridge:installation \
        --network=bridge:installation \
        --name pxe${i} --ram=${VIRT_MEM} \
        --disk /tmp/pxe${i}.raw,format=raw \
        --vcpus=${VIRT_CPU} \
        --graphics vnc,listen=0.0.0.0 \
        --noautoconsole \
        --autostart \
        --os-type=linux --os-variant=rhel6
    if [[ "$?" != "0" ]]; then
        echo "install instance pxe${i} failed"
        exit 1
    fi

    echo "make pxe${i} reboot if installation failing."
    sed -i "/<boot dev='hd'\/>/ a\    <bios useserial='yes' rebootTimeout='0'\/>" /etc/libvirt/qemu/pxe${i}.xml
    echo "check pxe${i} state"
    state=$(virsh domstate pxe${i})
    if [[ "$state" == "running" ]]; then
        echo "pxe${i} is already running"
        virsh destroy pxe${i}
        if [[ "$?" != "0" ]]; then
            echo "detroy intsance pxe${i} failed"
            exit 1
        fi
    fi

    echo "start pxe${i}"
    virsh start pxe${i}
    if [[ "$?" != "0" ]]; then
        echo "start instance pxe${i} failed"
        exit 1
    fi

    machines_str="${machines_str},${mac}"

    if [ $roles_offset -lt ${#roles_list[@]} ]; then
        host_roles_str="${host_roles_str};host${i}=${roles[$roles_offset]}"
        roles_offset=$(expr $roles_offset + 1)
    else
        host_roles_str="${host_roles_str};host${i}="
    fi
done

echo "machines: $machines_str"
echo "host roles: $host_roles_str"
virsh list

ln -sf /var/log/cobbler/anamon cobbler_logs
ln -sf /var/log/compass compass_logs
CLIENT_SCRIPT=/opt/compass/bin/client.py
/opt/compass/bin/refresh.sh
if [[ "$?" != "0" ]]; then
    echo "failed to refresh"
    exit 1 
fi

${CLIENT_SCRIPT} --logfile= --loglevel=info --logdir= --networking="${NETWORKING}" --partitions="${PARTITION}" --credentials="${SECURITY}" --host_roles="${host_roles_str}" --dashboard_role="${DASHBOARD_ROLE}" --switch_ips="${SWITCH_IPS}" --machines="${machines_str}" --switch_credential="${SWITCH_CREDENTIAL}"
if [[ "$?" != "0" ]]; then
    echo "deploy cluster failed"
    exit 1
fi
