#!/bin/bash -xe
cp compass-core/compass/apiclient/example.py /tmp/test.py
chmod +x /tmp/test.py
virsh destroy pxe01
virsh start pxe01
virsh list
source compass-core/install/install.conf.template
/usr/bin/python /tmp/test.py
