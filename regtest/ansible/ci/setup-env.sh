#rm -rf compass-install
#git clone http://git.openstack.org/stackforge/compass-install
#cd compass-install

function join { local IFS="$1"; shift; echo "$*"; }
REGTEST_CONF=${REGTEST_CONF:-"allinone.conf"}
source ${SCRIPT_DIR}/conf/${REGTEST_CONF}
source ${SCRIPT_DIR}/func.sh
if [[ ! -z $VIRT_NUMBER ]]; then
    mac_array=$(${SCRIPT_DIR}/mac_generator.sh $VIRT_NUMBER)
    mac_list=$(join , $mac_array)
    echo "pxe_boot_macs: [${mac_list}]" >> ${SCRIPT_DIR}/../install/group_vars/all
    echo "test: true" >> ${SCRIPT_DIR}/../install/group_vars/all
fi
virsh list |grep compass_nodocker
if [[ $? != 0 ]]; then
    sudo vagrant up compass_nodocker
else
    sudo vagrant provision compass_nodocker
fi
if [[ $? != 0 ]]; then
    echo "installation of compass failed"
    sudo vagrant destroy compass_nodocker
    exit 1
fi
echo "compass is up"

tear_down_machines
if [[ -n $mac_array ]]; then
    echo "bringing up pxe boot vms"
    i=0
    for mac in $mac_array; do
        echo "creating vm disk for instance pxe${i}"
        sudo qemu-img create -f raw /home/pxe${i}.raw ${VIRT_DISK}
        sudo virt-install --accelerate --hvm --connect qemu:///system \
             --name pxe$i --ram=$VIRT_MEM --pxe --disk /home/pxe$i.raw,format=raw \
             --vcpus=$VIRT_CPUS --graphics vnc,listen=0.0.0.0 \
             --network=bridge:virbr2,mac=$mac \
             --network=bridge:virbr2 \
             --network=bridge:virbr2 \
             --network=bridge:virbr2 \
             --noautoconsole --autostart --os-type=linux --os-variant=rhel6
        if [[ $? != 0 ]]; then
            echo "launching pxe${i} failed"
            exit 1
        fi
        echo "checking pxe${i} state"
        state=$(virsh domstate pxe${i})
        if [[ "$state" == "running" ]]; then
            echo "pxe${i} is running"
            sudo virsh destroy pxe${i}
        fi
        echo "add network boot option and make pxe${i} reboot if failing"
        sudo sed -i "/<boot dev='hd'\/>/ a\    <boot dev='network'\/>" /etc/libvirt/qemu/pxe${i}.xml
        sudo sed -i "/<boot dev='network'\/>/ a\    <bios useserial='yes' rebootTimeout='0'\/>" /etc/libvirt/qemu/pxe${i}.xml
        sudo virsh define /etc/libvirt/qemu/pxe${i}.xml
        sudo virsh start pxe${i}
        let i=i+1
    done
fi
machines=${mac_list}
