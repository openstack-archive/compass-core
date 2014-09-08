#!/bin/bash
echo "clean chef environments"
environments=$(knife environment list)
for environment in $environments; do
    if [[ "$environment" != "_default" ]]; then
        yes | knife environment delete $environment
	if [[ "$?" != "0" ]]; then
	    echo "failed to delete environment $environment"
	else
	    echo "environment $environment is deleted"
	fi
    fi
done
