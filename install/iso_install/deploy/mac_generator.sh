#!/bin/bash
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
