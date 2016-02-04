#!/bin/bash
##############################################################################
# Copyright (c) 2016 HUAWEI TECHNOLOGIES CO.,LTD and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
if [ "$2" == "started" ]; then
  timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  exists=$(ifconfig | grep macvtap|awk '{print $1}')

  for i in $exists; do
    ifconfig $i allmulti
    echo "$timestamp ALLMULTI set on $i" >> /var/log/libvirt_hook_qemu.log
  done
fi
