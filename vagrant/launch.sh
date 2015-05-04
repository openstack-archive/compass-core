#!/bin/bash
#

SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
if [ -f $HOME/VirtualBox\ VMs/compass-server ];then
    mkdir -p $HOME/VirtualBox VMs/compass-server
fi

if [ "$1" == "--recreate" ]; then
    source destroy.sh
    source first_run.sh
else
    source run.sh
fi
