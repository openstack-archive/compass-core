compass_vm_dir=$WORK_DIR/vm/compass
rsa_file=$compass_vm_dir/boot.rsa
ssh_args="-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $rsa_file"
function tear_down_compass() {
    sudo virsh destroy compass > /dev/null 2>&1
    sudo virsh undefine compass > /dev/null 2>&1

    sudo umount $compass_vm_dir/old > /dev/null 2>&1
    sudo umount $compass_vm_dir/new > /dev/null 2>&1

    sudo rm -rf $compass_vm_dir

    log_info "tear_down_compass success!!!"
}

function install_compass_core() {
    local inventory_file=$compass_vm_dir/inventory.file
    log_info "install_compass_core enter"
    sed -i "s/mgmt_next_ip:.*/mgmt_next_ip: ${COMPASS_SERVER}/g" $WORK_DIR/installer/compass-install/install/group_vars/all
    echo "compass_nodocker ansible_ssh_host=$MGMT_IP ansible_ssh_port=22" > $inventory_file
    PYTHONUNBUFFERED=1 ANSIBLE_FORCE_COLOR=true ANSIBLE_HOST_KEY_CHECKING=false ANSIBLE_SSH_ARGS='-o UserKnownHostsFile=/dev/null -o ControlMaster=auto -o ControlPersist=60s' python /usr/local/bin/ansible-playbook -e pipeline=true --private-key=$rsa_file --user=root --connection=ssh --inventory-file=$inventory_file $WORK_DIR/installer/compass-install/install/compass_nodocker.yml
    exit_status=$?
    rm $inventory_file
    log_info "install_compass_core exit"
    if [[ $exit_status != 0 ]];then
        /bin/false
    fi
}

function wait_ok() {
    set +x
    log_info "wait_compass_ok enter"
    ssh-keygen -f "/root/.ssh/known_hosts" -R $MGMT_IP >/dev/null 2>&1
    retry=0
    until timeout 1s ssh $ssh_args root@$MGMT_IP "exit" >/dev/null 2>&1
    do
        log_progress "os install time used: $((retry*100/$1))%"
        sleep 1
        let retry+=1
        if [[ $retry -ge $1 ]];then
            timeout 1s ssh $ssh_args root@$MGMT_IP "exit"
            log_error "os install time out"
            exit 1
        fi
    done
    set -x
    log_warn "os install time used: 100%"
    log_info "wait_compass_ok exit"
}

function launch_compass() {
    local old_mnt=$compass_vm_dir/old
    local new_mnt=$compass_vm_dir/new
    local old_iso=$WORK_DIR/iso/centos.iso
    local new_iso=$compass_vm_dir/centos.iso

    log_info "launch_compass enter"
    tear_down_compass

    set -e
    mkdir -p $compass_vm_dir $old_mnt
    sudo mount -o loop $old_iso $old_mnt
    cd $old_mnt;find .|cpio -pd $new_mnt;cd -

    sudo umount $old_mnt

    chmod 755 -R $new_mnt

    cp $COMPASS_DIR/util/isolinux.cfg $new_mnt/isolinux/ -f

    sed -i -e "s/REPLACE_MGMT_IP/$MGMT_IP/g" \
           -e "s/REPLACE_MGMT_NETMASK/$MGMT_MASK/g" \
           -e "s/REPLACE_GW/$MGMT_GW/g" \
           -e "s/REPLACE_INSTALL_IP/$COMPASS_SERVER/g" \
           -e "s/REPLACE_INSTALL_NETMASK/$INSTALL_MASK/g" \
           -e "s/REPLACE_COMPASS_EXTERNAL_NETMASK/$COMPASS_EXTERNAL_MASK/g" \
           -e "s/REPLACE_COMPASS_EXTERNAL_IP/$COMPASS_EXTERNAL_IP/g" \
           -e "s/REPLACE_COMPASS_EXTERNAL_GW/$COMPASS_EXTERNAL_GW/g" \
           $new_mnt/isolinux/isolinux.cfg

    if [[ -n $COMPASS_DNS1 ]]; then
        sed -i -e "s/REPLACE_COMPASS_DNS1/$COMPASS_DNS1/g" $new_mnt/isolinux/isolinux.cfg
    fi

    if [[ -n $COMPASS_DNS2 ]]; then
        sed -i -e "s/REPLACE_COMPASS_DNS2/$COMPASS_DNS2/g" $new_mnt/isolinux/isolinux.cfg
    fi

    ssh-keygen -f $new_mnt/bootstrap/boot.rsa -t rsa -N ''
    cp $new_mnt/bootstrap/boot.rsa $rsa_file

    rm -rf $new_mnt/.rr_moved $new_mnt/rr_moved
    sudo mkisofs -quiet -r -J -R -b isolinux/isolinux.bin  -no-emul-boot -boot-load-size 4 -boot-info-table -hide-rr-moved -x "lost+found:" -o $new_iso $new_mnt

    rm -rf $old_mnt $new_mnt

    qemu-img create -f qcow2 $compass_vm_dir/disk.img 100G

    # create vm xml
    sed -e "s/REPLACE_MEM/$COMPASS_VIRT_MEM/g" \
        -e "s/REPLACE_CPU/$COMPASS_VIRT_CPUS/g" \
        -e "s#REPLACE_IMAGE#$compass_vm_dir/disk.img#g" \
        -e "s#REPLACE_ISO#$compass_vm_dir/centos.iso#g" \
        -e "s/REPLACE_NET_MGMT/mgmt/g" \
        -e "s/REPLACE_NET_INSTALL/install/g" \
        -e "s/REPLACE_NET_EXTERNAL/external/g" \
        $COMPASS_DIR/deploy/template/vm/compass.xml \
        > $WORK_DIR/vm/compass/libvirt.xml

    sudo virsh define $compass_vm_dir/libvirt.xml
    sudo virsh start compass

    exit_status=$?
    if [ $exit_status != 0 ];then
        log_error "virsh start compass failed"
        exit 1
    fi

    if ! wait_ok 500;then
        log_error "install os timeout"
        exit 1
    fi

    if ! install_compass_core;then
        log_error "install compass core failed"
        exit 1
    fi

    set +e
    log_info "launch_compass exit"
}
