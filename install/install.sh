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
sudo rpm -q epel-release-6-8
if [ "$?" != "0" ]; then
sudo rpm -Uvh http://download.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm >& /dev/null
if [ "$?" != "0" ]; then
    echo "failed to install epel"
    exit 1
fi
fi
sed -i 's/^mirrorlist=https/mirrorlist=http/g' /etc/yum.repos.d/epel.repo

### Trap any error code with related filename and line.
errtrap()
{
    FILE=${BASH_SOURCE[1]:-$BASH_SOURCE[0]}
    echo "[FILE: "$(basename $FILE)", LINE: $1] Error: Command or function exited with status $2"
}

if [[ "$-" == *x* ]]; then
trap 'errtrap $LINENO $?' ERR
fi

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
loadvars()
{
    varname=${1,,}
    eval var=\$$(echo $1)

    if [[ -z $var ]]; then
        echo -e "\x1b[32mPlease enter the $varname (Example: $2):\x1b[37m"
        while read input
        do
            if [ "$input" == "" ]; then
                echo "Default $varname '$2' chosen"
                export $(echo $1)="$2"
                break
            else
                if [ "$1" == "NIC" ]; then
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
    if [[ -z $var ]]; then
        echo "variable $var is unset"
        exit 1 
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
if [[ -n $source ]] && [ $source = "local" ];then
loadvars WEB_SOURCE ${COMPASSDIR}/../web
loadvars ADAPTER_SOURCE ${COMPASSDIR}/../misc
else
loadvars WEB_SOURCE $REPO_URL'/stackforge/compass-web'
loadvars ADAPTER_SOURCE $REPO_URL'/stackforge/compass-adapters' 
fi

echo "script dir: $SCRIPT_DIR"
echo "compass dir is $COMPASSDIR"

echo "Install the Dependencies"
source ${COMPASSDIR}/install/dependency.sh

echo "Prepare the Installation"
source ${COMPASSDIR}/install/prepare.sh

echo "Install the OS Installer Tool"
source ${COMPASSDIR}/install/$OS_INSTALLER.sh

echo "Install the Package Installer Tool"
source ${COMPASSDIR}/install/$PACKAGE_INSTALLER.sh

echo "Download and Setup Compass and related services"
source ${COMPASSDIR}/install/compass.sh

figlet -ctf slant Installation Complete!
echo -e "It takes\x1b[32m $SECONDS \x1b[0mseconds during the installation."
