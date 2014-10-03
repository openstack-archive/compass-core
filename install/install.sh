#!/bin/bash
#

### Log the script all outputs locally
exec > >(sudo tee install.log)
exec 2>&1

### Creat a lock to avoid running multiple instances of script.
LOCKFILE="/tmp/`basename $0`"
LOCKFD=99

if [ -f $LOCKFILE ]; then
    LOCKED_PID=$(cat $LOCKFILE | head -n 1)
    ps -p $LOCKED_PID &> /dev/null
    if [[ "$?" != "0" ]]; then
	echo "the progress of pid $LOCKED_PID does not exist"
	rm -f $LOCKFILE
    else
	echo "the progress of pid $LOCKED_PID is running"
	exit 1
    fi
else
    echo "$LOCKFILE not exist"
fi

# PRIVATE
_lock()
{
    echo "lock $LOCKFILE"
    flock -$1 $LOCKFD
    pid=$$
    echo $pid 1>& $LOCKFD
}

_no_more_locking()
{
    _lock u
    _lock xn && rm -f $LOCKFILE
}

_prepare_locking()
{
    eval "exec $LOCKFD>\"$LOCKFILE\""
    trap _no_more_locking EXIT
}

# ON START
_prepare_locking

# PUBLIC
exlock_now()
{
    _lock xn || exit 1
}  # obtain an exclusive lock immediately or fail

exlock_now
if [[ "$?" != "0" ]]; then
    echo "failed to acquire lock $LOCKFILE"
    exit 1
fi

### BEGIN OF SCRIPT ###
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
source $DIR/install.conf

### Change selinux security policy
echo 0 > /selinux/enforce

### Add epel repo
sudo rpm -q epel-release
if [ "$?" != "0" ]; then
    sudo rpm -Uvh http://download.fedoraproject.org/pub/epel/${IMAGE_VERSION_MAJOR}/${IMAGE_ARCH}/epel-release-6-8.noarch.rpm >& /dev/null
    if [ "$?" != "0" ]; then
        echo "failed to install epel-release"
        exit 1
    else
        echo "sucessfaully installed epel-release"
    fi
else
    echo "epel-release is already installed"
fi

sed -i 's/^mirrorlist=https/mirrorlist=http/g' /etc/yum.repos.d/epel.repo

### Add atomic repo
sudo rpm -q atomic-release
if [ "$?" != "0" ]; then
    sudo rpm -Uvh http://www6.atomicorp.com/channels/atomic/${IMAGE_TYPE,,}/${IMAGE_VERSION_MAJOR}/${IMAGE_ARCH}/RPMS/atomic-release-1.0-19.${IMAGE_TYPE_OTHER}${IMAGE_VERSION_MAJOR}.art.noarch.rpm >& /dev/null
    if [ "$?" != "0" ]; then
        echo "failed to install atomic-release"
        exit 1
    else
        echo "successfully installed atomic-release"
    fi
else
    echo "atomic-release is already installed"
fi 

sed -i 's/^mirrorlist=https/mirrorlist=http/g' /etc/yum.repos.d/atomic.repo

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
if [[ "$?" != "0" ]]; then
    echo "failed to install figlet"
    exit 1
else
    echo "figlet is installed"
fi
figlet -ctf slant Compass Installer

while [ $1 ]; do
  flags=$1
  param=${flags/'--'/''}
  var=$(echo $param | cut -d"=" -f1)
  val=$(echo $param | cut -d"=" -f2)
  export $var=$val
  shift
done

# convert ip address to int
ipaddr_convert()
{
    ipaddr=$1
    IFS=. read -r a b c d <<< "$ipaddr"
    printf '%d\n' "$((a * 256 ** 3 + b * 256 ** 2 + c * 256 + d))"
}

# Load variables
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
                echo "You have entered $input"
                export $(echo $1)="$input"
                break
            fi
        done
    fi
}

loadvars NIC "eth0"
sudo ifconfig $NIC
if [ $? -ne 0 ]; then
    echo "There is no nic '$NIC' yet"
    exit 1
fi
sudo ifconfig $NIC | grep 'inet addr:' >& /dev/null
if [ $? -ne 0 ]; then
    echo "There is not any IP address assigned to the NIC '$NIC' yet, please assign an IP address first."
    exit 1
fi

export ipaddr=$(ifconfig $NIC | grep 'inet addr:' | cut -d: -f2 | awk '{ print $1}')
loadvars IPADDR ${ipaddr}
ipcalc $IPADDR -c
if [ $? -ne 0 ]; then
    echo "ip addr $IPADDR format should be x.x.x.x"
    exit 1
fi
export netmask=$(ifconfig $NIC |grep Mask | cut -f 4 -d ':')
loadvars NETMASK ${netmask}
export netaddr=$(ipcalc $IPADDR $NETMASK -n |cut -f 2 -d '=')
export netprefix=$(ipcalc $IPADDR $NETMASK -p |cut -f 2 -d '=')
subnet=${netaddr}/${netprefix}
ipcalc $subnet -c
if [ $? -ne 0 ]; then
    echo "subnet $subnet format should be x.x.x.x/x"
    exit 1
fi
loadvars OPTION_ROUTER $(route -n | grep '^0.0.0.0' | xargs | cut -d ' ' -f 2)
ipcalc $OPTION_ROUTER -c
if [ $? -ne 0 ]; then
    echo "router $OPTION_ROUTER format should be x.x.x.x"
    exit 1
fi
export ip_start=$(echo "$IPADDR"|cut -f 1,2,3 -d '.')."100"
export ip_end=$(echo "$IPADDR"|cut -f 1,2,3 -d '.')."250"
loadvars IP_START "$ip_start"
ipcalc $IP_START -c
if [ $? -ne 0 ]; then
    echo "ip start $IP_START format should be x.x.x.x"
    exit 1
else
    echo "ip start address is $IP_START"
fi
ip_start_net=$(ipcalc $IP_START $NETMASK -n |cut -f 2 -d '=')
if [[ "$ip_start_net" != "$netaddr" ]]; then
    echo "ip start $IP_START is not in $subnet"
    exit 1
fi
loadvars IP_END "$ip_end"
ipcalc $IP_END -c
if [ $? -ne 0 ]; then
    echo "ip end $IP_END format should be x.x.x.x"
    exit 1
fi
ip_end_net=$(ipcalc $IP_END $NETMASK -n |cut -f 2 -d '=')
if [[ "$ip_end_net" != "$netaddr" ]]; then
    echo "ip end $IP_END is not in $subnet"
    exit 1
fi
ip_start_int=$(ipaddr_convert $IP_START)
ip_end_int=$(ipaddr_convert $IP_END)
let ip_range=${ip_end_int}-${ip_start_int}
if [ $ip_range -le 0 ]; then
    echo "there is no available ips to assign between $IP_START and $IP_END"
    exit 1
fi
echo "there will be at most $ip_range hosts deployed."
loadvars NEXTSERVER $IPADDR
ipcalc $NEXTSERVER -c
if [ $? -ne 0 ]; then
    echo "next server $NEXTSERVER format should be x.x.x.x"
    exit 1
fi

if [[ -z $LOCAL_REPO ]]; then
    echo -e "\x1b[32mWould you like to set up a local repository?(y/n)\x1b[37m"
    while true; do
        read ans
        case $ans in
            y ) export LOCAL_REPO="y"; break;;
            n ) export LOCAL_REPO="n"; break;;
            * ) echo "I don't understand this";;
        esac
    done
fi
loadvars NAMESERVER_DOMAINS "ods.com"
loadvars WEB_SOURCE 'http://git.openstack.org/stackforge/compass-web'
loadvars ADAPTERS_SOURCE 'http://git.openstack.org/stackforge/compass-adapters'

echo "script dir: $SCRIPT_DIR"
echo "compass dir is $COMPASSDIR"

echo "generate env.conf"
source ${COMPASSDIR}/install/setup_env.sh || exit $?

echo "Install the Dependencies"
source ${COMPASSDIR}/install/dependency.sh || exit $?

echo "Prepare the Installation"
source ${COMPASSDIR}/install/prepare.sh || exit $?

echo "Install the OS Installer Tool"
source ${COMPASSDIR}/install/$OS_INSTALLER.sh || exit $?

echo "Install the Package Installer Tool"
source ${COMPASSDIR}/install/$PACKAGE_INSTALLER.sh || exit $?

echo "Download and Setup Compass and related services"
source ${COMPASSDIR}/install/compass.sh || exit $?

if [[ $LOCAL_REPO = "y" ]]; then
    echo "setting up local repo"
    source ${COMPASSDIR}/install/local_repo.sh || exit $?
fi
figlet -ctf slant Installation Complete!
echo -e "It takes\x1b[32m $SECONDS \x1b[0mseconds during the installation."
