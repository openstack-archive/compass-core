#!/bin/bash -xe
# Determinate is the given option present in the INI file
# ini_has_option config-file section option
function ini_has_option {
    local xtrace=$(set +o | grep xtrace)
    set +o xtrace
    local file=$1
    local section=$2
    local option=$3
    local line
    line=$(sed -ne "/^\[$section\]/,/^\[.*\]/ { /^$option[ \t]*=/ p; }" "$file")
    $xtrace
    [ -n "$line" ]
}
# Set an option in an INI file
# iniset config-file section option value
function iniset {
    local xtrace=$(set +o | grep xtrace)
    set +o xtrace
    local file=$1
    local section=$2
    local option=$3
    local value=$4

    [[ -z $section || -z $option ]] && return

    if ! grep -q "^\[$section\]" "$file" 2>/dev/null; then
        # Add section at the end
        echo -e "\n[$section]" >>"$file"
    fi
    if ! ini_has_option "$file" "$section" "$option"; then
        # Add it
        sed -i -e "/^\[$section\]/ a\\
$option = $value
" "$file"
    else
        local sep=$(echo -ne "\x01")
        # Replace it
        sed -i -e '/^\['${section}'\]/,/^\[.*\]/ s'${sep}'^\('${option}'[ \t]*=[ \t]*\).*$'${sep}'\1'"${value}"${sep} "$file"
    fi
    $xtrace
}
#Install prerequites for Tempest
pip install tox==1.6.1
#Install setuptools twice so that it is really upgraded
pip install -U setuptools
pip install -U setuptools
yum install -y libxml2-devel libxslt-devel python-devel sshpass
if [[ ! -e /tmp/tempest ]]; then
    git clone http://git.openstack.org/openstack/tempest /tmp/tempest
    cd /tmp/tempest
    git checkout grizzly-eol
else
    cd /tmp/tempest
    git remote set-url origin http://git.openstack.org/openstack/tempest
    git remote update
    git reset --hard
    git clean -x -f -d -q
    git checkout grizzly-eol
fi
cd /tmp/tempest
#Install Tempest including dependencies
pip install -e .
if [[ ! -e /etc/tempest ]]; then
    mkdir /etc/tempest
fi
#Initialize cloud environment for test and Tempest config file
cp etc/tempest.conf.sample /etc/tempest/tempest.conf
nova_api_host=$(knife search node 'roles:os-compute-api' | grep 'IP:' | awk '{print $2}' | head -1)
sshpass -p 'root' scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -r root@$nova_api_host:/root/openrc /root/.
source /root/openrc
demo_tenant_id=`keystone tenant-create --name demo |grep " id " |awk '{print $4}'`
alt_demo_tenant_id=`keystone tenant-create --name alt_demo |grep " id " |awk '{print $4}'`
keystone user-create --name demo --pass secret --tenant $demo_tenant_id
keystone user-create --name alt_demo --pass secret --tenant $alt_demo_tenant_id
image_id=`glance image-list |grep 'cirros'|awk '{print$2}'`
private_net_id=`quantum net-create --tenant_id $demo_tenant_id private |grep " id " |awk '{print$4}'`
quantum subnet-create --tenant_id $demo_tenant_id --ip_version 4 --gateway 10.1.0.1  $private_net_id 10.10.0.0/24
router_id=`quantum router-create --tenant_id $demo_tenant_id router1|grep " id " |awk '{print$4}'`
public_net_id=`quantum net-create public -- --router:external=True |grep " id " |awk '{print$4}'`
quantum subnet-create --ip_version 4 $public_net_id 172.24.4.0/24 -- --enable_dhcp=False
quantum router-gateway-set $router_id $public_net_id
iniset /etc/tempest/tempest.conf identity uri $OS_AUTH_URL
iniset /etc/tempest/tempest.conf identity admin_username $OS_USERNAME
iniset /etc/tempest/tempest.conf identity admin_password $OS_PASSWORD
iniset /etc/tempest/tempest.conf compute allow_tenant_isolation false
iniset /etc/tempest/tempest.conf compute image_ref $image_id
iniset /etc/tempest/tempest.conf compute image_ref_alt $image_id
iniset /etc/tempest/tempest.conf compute image_ssh_user cirros
iniset /etc/tempest/tempest.conf compute image_alt_ssh_user cirros
iniset /etc/tempest/tempest.conf compute resize_available false
iniset /etc/tempest/tempest.conf compute change_password_available false
iniset /etc/tempest/tempest.conf compute build_interval 15
iniset /etc/tempest/tempest.conf whitebox whitebox_enabled false
iniset /etc/tempest/tempest.conf network public_network_id $public_net_id
iniset /etc/tempest/tempest.conf network public_router_id ''
iniset /etc/tempest/tempest.conf network quantum_available true
iniset /etc/tempest/tempest.conf network tenant_network_cidr '172.16.2.128/25'

#Start a smoke test against cloud without object storage and aws related tests 
#as they are unavailable for now
if [[ $tempest_full == true ]]; then
    nosetests --logging-format '%(asctime)-15s %(message)s' --with-xunit -sv --attr=type=smoke \
                             --xunit-file=nosetests-smoke.xml tempest -e object_storage -e boto
    if [[ $tempest_network == true ]]; then
    nosetests tempest.tests.network.test_network_basic_ops
    fi
else
    nosetests --logging-format '%(asctime)-15s %(message)s' --with-xunit --xunit-file=nosetests-smoke.xml \
-sv --attr=type=smoke --tests="\
tempest.tests.compute.servers.test_server_addresses:ServerAddressesTest.test_list_server_addresses,\
tempest.tests.compute.servers.test_create_server:ServersTestAutoDisk.test_verify_server_details,\
tempest.tests.volume.test_volumes_get:VolumesGetTest.test_volume_create_get_delete"
    if [[ $tempest_network == true ]]; then
    nosetests tempest.tests.network.test_network_basic_ops
    fi
fi
