#!/bin/bash
##############################################################################
# Copyright (c) 2016 HUAWEI TECHNOLOGIES CO.,LTD and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
function reboot_hosts() {
    if [ -z $POWER_MANAGE ]; then
        return
    fi
    $POWER_MANAGE
}

function get_host_macs() {
    machines=`echo $HOST_MACS | sed -e 's/,/'\',\''/g' -e 's/^/'\''/g' -e 's/$/'\''/g'`
    echo $machines
}
