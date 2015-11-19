#!/bin/bash
services=`cat /opt/service | uniq`
for service in $services; do
    /usr/sbin/service $service status >/dev/null 2>&1
    if [[ $? -ne 0 ]]; then
        /usr/sbin/service $service start
    fi
done
