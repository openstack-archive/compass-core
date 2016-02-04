#!/bin/bash
##############################################################################
# Copyright (c) 2016 HUAWEI TECHNOLOGIES CO.,LTD and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
rsa_file=$compass_vm_dir/boot.rsa

function rename_nics(){
    python $COMPASS_DIR/deploy/rename_nics.py $DHA $rsa_file $MGMT_IP
}

function deploy_host(){
    AYNC_TIMEOUT = 20
    ssh $ssh_args root@${MGMT_IP} mkdir -p /opt/compass/bin/ansible_callbacks
    scp $ssh_args -r ${COMPASS_DIR}/deploy/status_callback.py root@${MGMT_IP}:/opt/compass/bin/ansible_callbacks/status_callback.py

    # avoid nodes reboot to fast, cobbler can not give response
    (sleep $AYNC_TIMEOUT; rename_nics; reboot_hosts) &
    if [[ "$REDEPLOY_HOST" == true ]]; then
        deploy_flag="redeploy"
    else
        deploy_flag="deploy"
    fi

    python ${COMPASS_DIR}/deploy/client.py --deploy_flag=$deploy_flag --compass_server="${HTTP_SERVER_URL}" \
    --compass_user_email="${COMPASS_USER_EMAIL}" --compass_user_password="${COMPASS_USER_PASSWORD}" \
    --cluster_name="${CLUSTER_NAME}" --language="${LANGUAGE}" --timezone="${TIMEZONE}" \
    --hostnames="${HOSTNAMES}" --partitions="${PARTITIONS}" --subnets="${SUBNETS}" \
    --adapter_os_pattern="${ADAPTER_OS_PATTERN}" --adapter_name="${ADAPTER_NAME}" \
    --adapter_target_system_pattern="${ADAPTER_TARGET_SYSTEM_PATTERN}" \
    --adapter_flavor_pattern="${ADAPTER_FLAVOR_PATTERN}" --repo_name="${REPO_NAME}" \
    --http_proxy="${PROXY}" --https_proxy="${PROXY}" --no_proxy="${IGNORE_PROXY}" \
    --ntp_server="${NTP_SERVER}" --dns_servers="${NAMESERVERS}" --domain="${DOMAIN}" \
    --search_path="${SEARCH_PATH}" --default_gateway="${GATEWAY}" \
    --server_credential="${SERVER_CREDENTIAL}" --local_repo_url="${LOCAL_REPO_URL}" \
    --os_config_json_file="${OS_CONFIG_FILENAME}" --service_credentials="${SERVICE_CREDENTIALS}" \
    --console_credentials="${CONSOLE_CREDENTIALS}" --host_networks="${HOST_NETWORKS}" \
    --network_mapping="${NETWORK_MAPPING}" --package_config_json_file="${PACKAGE_CONFIG_FILENAME}" \
    --host_roles="${HOST_ROLES}" --default_roles="${DEFAULT_ROLES}" --switch_ips="${SWITCH_IPS}" \
    --machines=${machines//\'} --switch_credential="${SWITCH_CREDENTIAL}" --deploy_type="${TYPE}" \
    --deployment_timeout="${DEPLOYMENT_TIMEOUT}" --${POLL_SWITCHES_FLAG} --dashboard_url="${DASHBOARD_URL}" \
    --cluster_vip="${VIP}" --network_cfg="$NETWORK" --neutron_cfg="$NEUTRON" \
    --enable_secgroup="${ENABLE_SECGROUP}" --enable_fwaas="${ENABLE_FWAAS}" \
    --rsa_file="$rsa_file" --enable_vpnaas="${ENABLE_VPNAAS}"

    RET=$?
    sleep $((AYNC_TIMEOUT+5))
    exit $RET
}
