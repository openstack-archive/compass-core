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
source `which virtualenvwrapper.sh`
workon compass-core

machines=''

tear_down_machines

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
done

echo "machines: $machines"
virsh list

# Avoid infinite relative symbolic links
if [[ ! -L cobbler_logs ]]; then
    ln -s /var/log/cobbler/anamon cobbler_logs
fi
if [[ ! -L compass_logs ]]; then
    ln -s /var/log/compass compass_logs
fi
if [[ ! -L chef_logs ]]; then
    ln -s /var/log/chef chef_logs
fi
CLIENT_SCRIPT=/opt/compass/bin/client.py
if [[ "$CLEAN_OLD_DATA" == "0" || "$CLEAN_OLD_DATA" == "false" ]]; then
    echo "keep old deployment data"
else
    rm -rf /var/log/compass/*
    /opt/compass/bin/refresh.sh
    if [[ "$?" != "0" ]]; then
        echo "failed to refresh"
        exit 1
    fi
    /opt/compass/bin/clean_nodes.sh
    /opt/compass/bin/clean_clients.sh
    /opt/compass/bin/clean_environments.sh
    /opt/compass/bin/remove_systems.sh
fi

if [[ "$USE_POLL_SWITCHES" == "0" || "$USE_POLL_SWITCHES" == "false" ]]; then
    POLL_SWITCHES_FLAG="nopoll_switches"
    TMP_SWITCH_MACHINE_FILE=$(mktemp)
    > ${TMP_SWITCH_MACHINE_FILE}
    for switch_ip in ${SWITCH_IPS//,/ }; do
        echo "switch,${switch_ip},huawei,${SWITCH_VERSION},${SWITCH_COMMUNITY},under_monitoring" >> ${TMP_SWITCH_MACHINE_FILE}
        switch_port=1
        for mac in ${machines//,/ }; do
            echo "machine,${switch_ip},${switch_port},${mac}" >> ${TMP_SWITCH_MACHINE_FILE}
            let switch_port+=1
        done
        break
    done
    echo "generated switch machine file: $TMP_SWITCH_MACHINE_FILE"
    cat $TMP_SWITCH_MACHINE_FILE
    echo "======================================================="
    /opt/compass/bin/manage_db.py set_switch_machines --switch_machines_file ${TMP_SWITCH_MACHINE_FILE}
    if [[ "$?" != "0" ]]; then
        echo "failed to set switch machines"
        exit 1
    fi
else
    POLL_SWITCHES_FLAG="poll_switches"
fi

${CLIENT_SCRIPT} --logfile= --loglevel=debug --logdir= --compass_server="${COMPASS_SERVER_URL}" --compass_user_email="${COMPASS_USER_EMAIL}" --compass_user_password="${COMPASS_USER_PASSWORD}" --cluster_name="${CLUSTER_NAME}" --language="${LANGUAGE}" --timezone="${TIMEZONE}" --hostnames="${HOSTNAMES}" --partitions="${PARTITIONS}" --subnets="${SUBNETS}" --adapter_os_pattern="${ADAPTER_OS_PATTERN}" --adapter_name="${ADAPTER_NAME}" --adapter_target_system_pattern="${ADAPTER_TARGET_SYSTEM_PATTERN}" --adapter_flavor_pattern="${ADAPTER_FLAVOR_PATTERN}" --http_proxy="${PROXY}" --https_proxy="${PROXY}" --no_proxy="${IGNORE_PROXY}" --ntp_server="${NTP_SERVER}" --dns_servers="${NAMESERVERS}" --domain="${DOMAIN}" --search_path="${SEARCH_PATH}" --default_gateway="${GATEWAY}" --server_credential="${SERVER_CREDENTIAL}" --service_credentials="${SERVICE_CREDENTIALS}" --console_credentials="${CONSOLE_CREDENTIALS}" --host_networks="${HOST_NETWORKS}" --network_mapping="${NETWORK_MAPPING}" --host_roles="${HOST_ROLES}" --default_roles="${DEFAULT_ROLES}" --switch_ips="${SWITCH_IPS}" --machines="${machines}" --switch_credential="${SWITCH_CREDENTIAL}" --deployment_timeout="${DEPLOYMENT_TIMEOUT}" --${POLL_SWITCHES_FLAG} --dashboard_url="${DASHBOARD_URL}"
rc=$?
deactivate
# Tear down machines after the test
if [[ $rc != 0 ]]; then
    tear_down_machines
    echo "deployment failed"
    exit 1
fi
#if [[ $tempest == true ]]; then
#    ./tempest_run.sh
#    if [[ $? != 0 ]]; then
#        tear_down_machines
#        echo "tempest failed"
#        exit 1
#    fi
#    tear_down_machines 
#fi
