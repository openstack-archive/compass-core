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
pip install -U virtualenvwrapper
yum install -y libxml2-devel libxslt-devel python-devel sshpass
if [[ ! -e /tmp/tempest ]]; then
    git clone http://git.openstack.org/openstack/tempest /tmp/tempest
    cd /tmp/tempest
else
    cd /tmp/tempest
    git remote set-url origin http://git.openstack.org/openstack/tempest
    git remote update
    git reset --hard
    git clean -x -f -d -q
    git checkout remotes/origin/master
fi
source `which virtualenvwrapper.sh`
set +e
if ! lsvirtualenv |grep tempest>/dev/null; then
    mkvirtualenv tempest
    workon tempest
else
    workon tempest
fi
set -e
cd /tmp/tempest
#Install Tempest including dependencies
pip install -e .
nova_api_host=$(knife search node 'roles:os-compute-api' | grep 'IP:' | awk '{print $2}' | head -1)
sshpass -p 'root' scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -r root@$nova_api_host:/root/openrc /root/.
source /root/openrc
# wait for nova-compute neutron-agent and cinder-volume to report health
# In some scenarios, nova-compute is up before conductor and has to retry
# to register to conductor and there is some wait time between retries.
timeout 180s sh -c "while ! nova service-list --binary nova-compute | grep 'enabled.*\ up\ '; do sleep 3; done"
timeout 180s sh -c '''while ! neutron agent-list -f csv -c alive -c agent_type -c host | grep "\":-).*Open vSwitch agent.*\"" ; do sleep 3; done'''
timeout 180s sh -c "cinder service-list --binary cinder-volume | grep 'enabled.*\ up\ '"
