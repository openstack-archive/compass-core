#!/bin/bash
let loop=0
mkdir -p /var/log/statistic
chmod -R 644 /var/log/statistic
while true; do
echo "run sar in the ${loop} time"
sar -n DEV -u -r -b 10 1 > /var/log/statistic/sar${loop}.log
let loop+=1
done
