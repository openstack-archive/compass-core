function deploy_host(){

    ssh $ssh_args root@${MGMT_IP} mkdir -p /opt/compass/bin/ansible_callbacks
    scp $ssh_args -r ${COMPASS_DIR}/deploy/status_callback.py root@${MGMT_IP}:/opt/compass/bin/ansible_callbacks/status_callback.py

    reboot_hosts

    python ${COMPASS_DIR}/deploy/client.py --compass_server="${HTTP_SERVER_URL}" \
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
    --enable_secgroup="${ENABLE_SECGROUP}" --enable_fwaas="${ENABLE_FWAAS}" --enable_vpnaas="${ENABLE_VPNAAS}"

}
