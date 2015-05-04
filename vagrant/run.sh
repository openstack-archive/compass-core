#!/bin/bash
#

VBoxManage list vms|grep controller
if [ "$?" == "0" ]; then
    exit 0
else
    source first_run.sh
fi
