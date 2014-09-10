#!/bin/bash
echo "clean chef clients"
yes | knife client bulk delete '^(?!chef-).*'
if [[ "$?" != "0" ]]; then
    echo "failed to clean all clients"
fi
