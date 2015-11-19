#!/bin/bash
services=`cat /opt/service | uniq`
for service in $services; do
    if [ `/sbin/initctl list|awk '/stop\/waiting/{print $1}'|uniq | grep $service` ]; then
        /sbin/start $service
    fi
done
