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


declare -A switches
declare -A switch_machines
declare -A virt_machines
declare -A hosts
declare -A roles_list
declare -A host_roles
for switch in ${SWITCH_IPS//,/ }; do
    switches[${#switches[@]}]=${switch}
    switch_machines[$switch]=""
done
switch_offset=0

for roles in ${HOST_ROLES//;/ }; do
    roles_list[${#roles_list[@]}]=${roles}
done
roles_offset=0

for i in `seq $VIRT_NUM`; do
    if [[ ! -e /tmp/pxe${i}.raw ]]; then
        qemu-img create -f raw /tmp/pxe${i}.raw ${VIRT_DISK}
        if [[ "$?" != "0" ]]; then
            echo "create image $i failed"
            exit 1
        fi 
    else
        rm -rf /tmp/pxe${i}.raw
        qemu-img create -f raw /tmp/pxe${i}.raw ${VIRT_DISK}
        if [[ "$?" != "0" ]]; then
            echo "create image /tmp/pxe${i}.raw failed"
            exit 1
        fi 
    fi
    virsh list | grep pxe${i}
    vmrc=$?
    if [[ $vmrc -eq 0 ]] ; then
        virsh destroy pxe${i}
        if [[ "$?" != "0" ]]; then
            echo "destroy instance pxe$i failed"
            exit 1
        fi
        virsh undefine pxe${i}
        if [[ "$?" != "0" ]]; then
            echo "undefine instance pxe$i failed"
            exit 1
        fi
    else
        echo "no legacy pxe${i} vm found"
    fi
    mac=$(mac_address)
    virt-install --accelerate --hvm --connect qemu:///system \
        --network=network:eth0,bridge:installation,mac=${mac} --pxe \
        --network=network:eth1 \
        --network=network:eth2 \
        --network=network:eth3 \
        --name pxe${i} --ram=${VIRT_MEM} \
        --disk /tmp/pxe${i}.raw,format=raw \
        --vcpus=${VIRT_CPU} \
        --graphics vnc,listen=0.0.0.0 --noautoconsole \
        --os-type=linux --os-variant=rhel6
    if [[ "$?" != "0" ]]; then
        echo "install instance pxe${i} failed"
        exit 1
    fi    

    virt_machines[$i]=pxe${i}
    switch=${switches[$switch_offset]}
    switch_machines[$switch]="${switch_machines[$switch]} $mac"
    switch_offset=$(expr \( $switch_offset + 1 \) % ${#switches[@]})

    hosts[$i]=host${i}
    if [ $roles_offset -lt ${#roles_list[@]} ]; then
        host_roles[${hosts[$i]}]=${roles[$roles_offset]}
        roles_offset=$(expr $roles_offset + 1)
    else
        host_roles[${hosts[$i]}]=""
    fi
done

host_roles_str=''
for host in ${!host_roles[@]}; do
    host_roles_str="${host_roles_str};${host_roles[$host]}"
done

switches_str=''
for switch in ${!switches[@]}; do
    switches_str="${switches_str},switch"
done

machines_str=''
rm -rf switch-file
echo '# switch machines' > /tmp/switch-file
for switch in ${!switch_machines[@]}; do
    machines=${switch_machines[$switch]}
    machine_port=0
    for machine in $machines; do
        echo "machine,${switch},${machine_port},1,${machine}" >> /tmp/switch-file
        machine_port=$(expr $machine_port + 1)
        machines_str="${machines_str},${machine}"
    done
    echo "switch,${switch},huawei,v2c,public,under_monitoring" >> /tmp/switch-file
done

ln -s /var/log/cobbler/anamon cobbler_logs
ln -s /var/log/compass compass_logs
CLIENT_SCRIPT=/tmp/${RANDOM}.py
cp compass-core/regtest/client.py ${CLIENT_SCRIPT}
chmod +x ${CLIENT_SCRIPT}

/usr/bin/python /opt/compass/bin/manage_db.py set_switch_machines --switch_machines_file /tmp/switch-file
/usr/bin/python /opt/compass/bin/manage_db.py clean_clusters
/usr/bin/python /opt/compass/bin/manage_db.py clean_installation_progress
service rsyslog restart
service redis restart
redis-cli flushall

for virt_machine in ${!virt_machines[@]}; do
    virsh start ${virt_machine}
    if [[ "$?" != "0" ]]; then
        echo "start instance ${virt_machine} failed"
        exit 1
    fi
done
virsh list

/usr/bin/python ${CLIENT_SCRIPT} --logfile= --loglevel=info --logdir= --networking="${NETWORKING}" --partitions="${PARTITION}" --credentials="${SECURITY}" --host_roles="${host_roles_str}" --dashboard_role="${DASHBOARD_ROLE}" --switch_ips="${switches_str}" --machines="${machines_str}"
if [[ "$?" != "0" ]]; then
    echo "deploy cluster failed"
    exit 1
fi
