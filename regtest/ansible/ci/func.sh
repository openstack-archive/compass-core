function tear_down_machines() {
    virtmachines=$(virsh list --name |grep pxe)
    for virtmachine in $virtmachines; do
        echo "destroy $virtmachine"
        virsh destroy $virtmachine
        if [[ "$?" != "0" ]]; then
            echo "destroy instance $virtmachine failed"
            exit 1
        fi
    done
    virtmachines=$(virsh list --all --name |grep pxe)
    for virtmachine in $virtmachines; do
        echo "undefine $virtmachine"
        virsh undefine $virtmachine
        if [[ "$?" != "0" ]]; then
            echo "undefine instance $virtmachine failed"
            exit 1
        fi
    done
}
