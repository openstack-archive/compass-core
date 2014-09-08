#!/bin/bash
systems=$(cobbler system list)
echo "remove systems: $systems"
for system in $systems; do
    cobbler system remove --name=$system
    if [[ "$?" != "0" ]]; then
	echo "failed to remove system %s"
    fi
done
