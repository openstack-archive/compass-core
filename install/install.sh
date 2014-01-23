#!/bin/bash
#

### Log the script all outputs locally
exec > >(sudo tee install.log)
exec 2>&1

### Creat a lock to avoid running multiple instances of script.
LOCKFILE="/tmp/`basename $0`"
LOCKFD=99

# PRIVATE
_lock()             { flock -$1 $LOCKFD; }
_no_more_locking()  { _lock u; _lock xn && rm -f $LOCKFILE; }
_prepare_locking()  { eval "exec $LOCKFD>\"$LOCKFILE\""; trap _no_more_locking EXIT; }

# ON START
_prepare_locking

# PUBLIC
exlock_now()        { _lock xn; }  # obtain an exclusive lock immediately or fail

exlock_now || exit 1

### BEGIN OF SCRIPT ###
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

### Change selinux security policy
echo 0 > /selinux/enforce

### Add epel repo
sudo rpm -Uvh http://download.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm >& /dev/null
sed -i 's/^mirrorlist=https/mirrorlist=http/g' /etc/yum.repos.d/epel.repo

### Trap any error code with related filename and line.
errtrap()
{
    FILE=${BASH_SOURCE[1]:-$BASH_SOURCE[0]}
    echo "[FILE: "$(basename $FILE)", LINE: $1] Error: Command or function exited with status $2"
}

trap 'errtrap $LINENO $?' ERR

# Install figlet
sudo yum -y install figlet >& /dev/null
figlet -ctf slant Compass Installer

while [ $1 ]; do
  flags=$1
  param=${flags/'--'/''}
  var=$(echo $param | cut -d"=" -f1)
  val=$(echo $param | cut -d"=" -f2)
  export $var=$val
  shift
done

# Load variables
source $DIR/install.conf
echo $WEB_SOURCE
echo $ADAPTER_SOURCE
loadvars()
{
    varname=${1,,}
    eval var=\$$(echo $1)

    if [[ -z $var ]]; then
        echo -e "\x1b[32mPlease enter the DHCP $varname (Example: $2):\x1b[37m"
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
export netmask=$(ifconfig $NIC |grep Mask | cut -f 4 -d ':')
export ipaddr=$(ifconfig $NIC | grep 'inet addr:' | cut -d: -f2 | awk '{ print $1}')
export range=$(echo "$(echo "$ipaddr"|cut -f 1 -d '.').$(echo "$ipaddr"|cut -f 2 -d '.').$(echo "$ipaddr"|cut -f 3 -d '.').100 $(echo "$ipaddr"|cut -f 1 -d '.').$(echo "$ipaddr"|cut -f 2 -d '.').$(echo "$ipaddr"|cut -f 3 -d '.').250")
export ipnet=$(ip address| grep "global $NIC" |cut -f 6 -d ' ')
loadvars SUBNET $(ipcalc $ipnet -n |cut -f 2 -d '=')/$(ipcalc $ipnet -p |cut -f 2 -d '=')
loadvars OPTION_ROUTER $(route -n | grep '^0.0.0.0' | xargs | cut -d ' ' -f 2)
loadvars IP_RANGE "$range"
loadvars NEXTSERVER $ipaddr
loadvars NAMESERVER_DOMAINS "ods.com"

echo "Install the Dependencies"
source $DIR/dependency.sh

echo "Install the OS Installer Tool"
source $DIR/$OS_INSTALLER.sh

echo "Install the Package Installer Tool"
source $DIR/$PACKAGE_INSTALLER.sh

echo "Download and Setup Compass and related services"
source $DIR/compass.sh

echo -e "It takes\x1b[32m $SECONDS \x1b[0mseconds during the installation."
