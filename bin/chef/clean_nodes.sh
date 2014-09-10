#!/bin/bash
echo "clean chef nodes"
yes | knife node bulk delete '.*'
if [[ "$?" != "0" ]]; then
    echo "failed to clean all nodes"
fi
