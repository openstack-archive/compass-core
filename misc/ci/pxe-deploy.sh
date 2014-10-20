#!/bin/bash -xe
ln -s /var/log/cobbler/anamon cobbler_logs
ln -s /var/log/compass compass_logs
ln -s /var/log/chef chef_logs
cp compass-core/compass/apiclient/example.py /tmp/test.py
chmod +x /tmp/test.py
virsh destroy pxe01
virsh start pxe01
virsh list
source compass-core/install/install.conf.template
/usr/bin/python /tmp/test.py
if [ "$tempest" == "true" ]; then
    ./tempest_run.sh
fi
