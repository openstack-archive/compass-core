#!/bin/bash

source install.conf

sudo figlet Compass Installer

loadvars()
{
    varname=${1,,}
    eval var=\$$(echo $1)
    
    if [[ -z $var ]]; then
        echo "Please enter the DHCP $varname (Example: $2) "
        while read input
        do
            if [ "$input" == "" ]; then
                echo "Default $varname '$2' chosen"
                export $(echo $1)="$2"
                break
            else
                if [[ ( "$input" != *.* ) && ( "$1" != "NIC" ) ]]; then
                    echo "I really expect IP addresses"
                    exit
                elif [ "$1" == "NIC" ]; then
                    sudo ip addr |grep $input >& /dev/null
                    if [ $? -ne 0 ]; then
                        echo "There is not any IP address assigned to the NIC '$input' yet, please assign an IP address first."
                        exit
                    fi
                fi
                echo "You have entered $input"
                export $(echo $1)="$input"
                break
            fi
        done
    fi
}


loadvars NIC "eth0"
