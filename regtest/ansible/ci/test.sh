sudo apt-get update -y
sudo apt-get install git python-pip python-dev -y
vagrant_pkg_url=https://dl.bintray.com/mitchellh/vagrant/vagrant_1.7.2_x86_64.deb
wget ${vagrant_pkg_url}
sudo dpkg -i $(basename ${vagrant_pkg_url})
sudo apt-get install libxslt-dev libxml2-dev libvirt-dev build-essential qemu-utils qemu-kvm libvirt-bin virtinst -y
sudo service libvirt-bin restart
vagrant plugin install vagrant-libvirt
vagrant plugin install vagrant-mutate
precise_box_vb_url=https://cloud-images.ubuntu.com/vagrant/precise/current/precise-server-cloudimg-amd64-vagrant-disk1.box
precise_box_vb_filename=$(basename ${precise_box_vb_url})
centos65_box_vb_url=https://developer.nrel.gov/downloads/vagrant-boxes/CentOS-6.5-x86_64-v20140504.box
centos65_box_vb_filename=$(basename ${centos65_box_vb_url})
wget ${precise_box_vb_url}
wget ${centos65_box_vb_url}
mv ${precise_box_vb_filename} precise64.box
mv ${centos65_box_vb_filename} centos65.box
vagrant mutate precise64.box libvirt
vagrant mutate centos65.box libvirt
sudo pip install ansible
git clone http://git.openstack.org/stackforge/compass-install
cd compass-install

function join { local IFS="$1"; shift; echo "$*"; }

if [[ ! -z $VIRT_NUMBER ]]; then
    mac_array=$(ci/mac_generator.sh $VIRT_NUMBER)
    mac_list=$(join , $mac_array)
    echo "pxe_boot_macs: [${mac_list}]" >> install/group_vars/all
    echo "test: true" >> install/group_vars/all
fi
sudo vagrant up compass_vm
if [[ $? != 0 ]]; then
    sudo vagrant provision compass_vm
    if [[ $? != 0 ]]; then
        echo "provisioning of compass failed"
        exit 1
    fi
fi
echo "compass is up"

if [[ -n $mac_array ]]
    echo "bringing up pxe boot vms"
    i=0
    for mac in "$mac_array"; do
        virsh list |grep pxe${i}
        if [[ $? == 0 ]]; then
            virsh destroy pxe${i}
            virsh undefine pxe${i}
        fi
        virsh list --all |grep pxe${i}
        if [[ $? == 0 ]]; then
            virsh undefine pxe${i}
        fi
        echo "creating vm disk for instance pxe${i}"
        sudo qemu-img create -f raw /home/pxe${i}.raw ${VIRT_DISK}
        sudo virt-install --accelerate --hvm --connect qemu:///system \
             --name pxe$i --ram=$VIRT_MEM --pxe --disk /home/pxe$i.raw,format=raw \
             --vcpus=$VIRT_CPUS --graphics vnc,listen=0.0.0.0 \
             --network=bridge:virbr2,mac=$mac \
             --network=bridge:virbr2
             --network=bridge:virbr2
             --network=bridge:virbr2
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

rm -rf compass-core
git clone http://git.openstack.org/stackforge/compass-core -b dev/experimental
cd compass-core
virtualenv venv
source venv/bin/activate
pip install -e .
if [[ ! -f /var/log/compass ]]; then
    sudo mkdir /var/log/compass
    sudo chown -R 777 /var/log/compass
fi
if [[ ! -f /etc/compass ]]; then
    sudo mkdir /etc/compass
    sudo cp -rf conf/setting /etc/compass/.
fi
cp bin/switch_virtualenv.py.template bin/switch_virtualenv.py
sed -i "s|\$PythonHome|$VIRTUAL_ENV|g" /opt/compass/bin/switch_virtualenv.py
source ../compass-install/ci/allinone.conf
bin/client.py --logfile= --loglevel=debug --logdir= --compass_server="${COMPASS_SERVER_URL}" \
--compass_user_email="${COMPASS_USER_EMAIL}" --compass_user_password="${COMPASS_USER_PASSWORD}" \
--cluster_name="${CLUSTER_NAME}" --language="${LANGUAGE}" --timezone="${TIMEZONE}" \
--hostnames="${HOSTNAMES}" --partitions="${PARTITIONS}" --subnets="${SUBNETS}" \
--adapter_os_pattern="${ADAPTER_OS_PATTERN}" --adapter_name="${ADAPTER_NAME}" \
--adapter_target_system_pattern="${ADAPTER_TARGET_SYSTEM_PATTERN}" \
--adapter_flavor_pattern="${ADAPTER_FLAVOR_PATTERN}" \
--http_proxy="${PROXY}" --https_proxy="${PROXY}" --no_proxy="${IGNORE_PROXY}" \
--ntp_server="${NTP_SERVER}" --dns_servers="${NAMESERVERS}" --domain="${DOMAIN}" \
--search_path="${SEARCH_PATH}" --default_gateway="${GATEWAY}" \
--server_credential="${SERVER_CREDENTIAL}" --local_repo_url="${LOCAL_REPO_URL}" \
--os_config_json_file="${OS_CONFIG_FILENAME}" --service_credentials="${SERVICE_CREDENTIALS}" \
--console_credentials="${CONSOLE_CREDENTIALS}" --host_networks="${HOST_NETWORKS}" \
--network_mapping="${NETWORK_MAPPING}" --package_config_json_file="${PACKAGE_CONFIG_FILENAME}" \
--host_roles="${HOST_ROLES}" --default_roles="${DEFAULT_ROLES}" --switch_ips="${SWITCH_IPS}" \
--machines="${machines}" --switch_credential="${SWITCH_CREDENTIAL}" \
--deployment_timeout="${DEPLOYMENT_TIMEOUT}" --${POLL_SWITCHES_FLAG} --dashboard_url="${DASHBOARD_URL}"
#sudo vagrant up regtest_vm
#if [[ $? != 0 ]]; then
#    sudo vagrant provision regtest_vm
#    if [[ $? != 0 ]]; then
#        echo "deployment of cluster failed"
#        exit 1
#    fi
#fi
#echo "deployment of cluster complete"

