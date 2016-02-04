#!/bin/bash
##############################################################################
# Copyright (c) 2016 HUAWEI TECHNOLOGIES CO.,LTD and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
function mac_address_part() {
    hex_number=$(printf '%02x' $RANDOM)
    number_length=${#hex_number}
    number_start=$(expr $number_length - 2)
    echo ${hex_number:$number_start:2}
}

function mac_address() {
    echo "'00:00:$(mac_address_part):$(mac_address_part):$(mac_address_part):$(mac_address_part)'"
}

machines=''
for i in `seq $1`; do
  mac=$(mac_address)

  if [[ -z $machines ]]; then
    machines="${mac}"
  else
    machines="${machines} ${mac}"
  fi
done
echo ${machines}
