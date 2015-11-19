function reboot_hosts() {
    if [ -z $POWER_MANAGE ]; then
        return
    fi
    $POWER_MANAGE
}

function get_host_macs() {
    local config_file=$WORK_DIR/installer/compass-install/install/group_vars/all
    echo "test: true" >> $config_file
    machine=`echo $HOST_MACS | sed -e 's/,/'\',\''/g' -e 's/^/'\''/g' -e 's/$/'\''/g'`
    echo "pxe_boot_macs: [$machine]" >> $config_file

    echo $machine
}
