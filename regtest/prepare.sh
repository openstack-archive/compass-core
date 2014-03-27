#!/bin/bash -x
# create a bridge named 'installation' so that compass and pxeboot vm are in the
# same l2 network.
brctl show |grep installation > /dev/null
if [[ $? -eq 0 ]] ; then
    echo "bridge already exists"
else
    brctl addbr installation
    brctl addif installation eth1
fi

ifconfig installation 172.16.0.1 broadcast 172.16.0.0 netmask 255.255.0.0 up
ifconfig eth1 up

