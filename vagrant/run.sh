#!/bin/bash
#

VBoxManage list vms|grep controller
if [ "$?" == "0" ]; then
    if [ `VBoxManage list runningvms | wc -l` == 0 ]; then
	vagrant up
    fi
    exit 0
else
    source first_run.sh
fi
