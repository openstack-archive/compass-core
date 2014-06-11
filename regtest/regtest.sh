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

function tear_down_machines() {
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
}

REGTEST_CONF=${REGTEST_CONF:-"regtest.conf"}
REGTEST_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
source ${REGTEST_DIR}/${REGTEST_CONF}

declare -A roles_list
machines=''

for roles in ${HOST_ROLES//;/ }; do
    roles_list[${#roles_list[@]}]=${roles}
done
echo "role list: ${roles_list[@]}"
roles_offset=0
host_roles_list=''

tear_down_machines

echo "setup $VIRT_NUM virt machines"
for i in `seq $VIRT_NUM`; do
    if [[ ! -e /home/pxe${i}.raw ]]; then
        echo "create image for instance pxe$i"
        qemu-img create -f raw /home/pxe${i}.raw ${VIRT_DISK}
        if [[ "$?" != "0" ]]; then
            echo "create image /home/pxe${i}.raw failed"
            exit 1
        fi 
    else
        echo "recreate image for instance pxe$i"
        rm -rf /home/pxe${i}.raw
        qemu-img create -f raw /home/pxe${i}.raw ${VIRT_DISK}
        if [[ "$?" != "0" ]]; then
            echo "create image /home/pxe${i}.raw failed"
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
        --disk /home/pxe${i}.raw,format=raw \
        --vcpus=${VIRT_CPUS} \
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

    if [ -z "$machines" ]; then
        machines="${mac}"
    else
        machines="${machines},${mac}"
    fi

    if [ $roles_offset -lt ${#roles_list[@]} ]; then
        host_roles="host${i}=${roles_list[$roles_offset]}"
        roles_offset=$(expr $roles_offset + 1)
    else
        host_roles="host${i}="
    fi

    if [ -z "$host_roles_list" ]; then
        host_roles_list="$host_roles"
    else
        host_roles_list="${host_roles_list};$host_roles"
    fi
done

echo "machines: $machines"
echo "host roles: $host_roles_list"
virsh list

# Avoid infinite relative symbolic links
if [[ ! -L cobbler_logs ]]; then
    ln -s /var/log/cobbler/anamon cobbler_logs
fi
if [[ ! -L compass_logs ]]; then
    ln -s /var/log/compass compass_logs
fi
CLIENT_SCRIPT=/opt/compass/bin/client.py
/opt/compass/bin/refresh.sh
if [[ "$?" != "0" ]]; then
    echo "failed to refresh"
    exit 1 
fi

if [[ "$USE_POLL_SWITCHES" == "0" || "$USE_POLL_SWITCHES" == "false" ]]; then
    POLL_SWITCHES_FLAG="nopoll_switches"
    TMP_SWITCH_MACHINE_FILE=$(mktemp)
    > ${TMP_SWITCH_MACHINE_FILE}
    for switch_ip in ${SWITCH_IPS//,/ }; do
        echo "switch,${switch_ip},huawei,${SWITCH_VERSION},${SWITCH_COMMUNITY},under_monitoring" >> ${TMP_SWITCH_MACHINE_FILE}
        switch_port=1
        for mac in ${machines//,/ }; do
            echo "machine,${switch_ip},${switch_port},1,${mac}" >> ${TMP_SWITCH_MACHINE_FILE}
            let switch_port+=1
        done
        break
    done
    echo "generated switch machine file: $TMP_SWITCH_MACHINE_FILE"
    cat $TMP_SWITCH_MACHINE_FILE
    echo "======================================================="
    /opt/compass/bin/manage_db.py set_switch_machines --switch_machines_file ${TMP_SWITCH_MACHINE_FILE}
else
    POLL_SWITCHES_FLAG="poll_switches"
fi

${CLIENT_SCRIPT} --logfile= --loglevel=info --logdir= --adapter_os_name="${ADAPTER_OS_NAME_PATTERN}" --adapter_target_system="${ADAPTER_TARGET_SYSTEM_NAME}" --networking="${NETWORKING}" --partitions="${PARTITION}" --credentials="${SECURITY}" --host_roles="${host_roles_list}" --dashboard_role="${DASHBOARD_ROLE}" --switch_ips="${SWITCH_IPS}" --machines="${machines}" --switch_credential="${SWITCH_CREDENTIAL}" --deployment_timeout="${DEPLOYMENT_TIMEOUT}" --${POLL_SWITCHES_FLAG}
rc=$?
# Tear down machines after the test
if [[ $rc != 0 ]]; then
    tear_down_machines
    echo "deployment failed"
    exit 1
fi
if [[ $tempest == true ]]; then
    ./tempest_run.sh
    if [[ $? != 0 ]]; then
        tear_down_machines
        echo "tempest failed"
        exit 1
    fi
    tear_down_machines 
fi
