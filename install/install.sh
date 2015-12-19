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
	echo "the progress of pid $LOCKED_PID does not exist: `ps -p $LOCKED_PID`"
	rm -f $LOCKFILE
    else
	echo "the progress of pid $LOCKED_PID is running: `ps -p $LOCKED_PID`"
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
sudo setenforce 0
sudo sed -i 's/enforcing/disabled/g' /etc/selinux/config
### Add epel repo
sudo rpm -q epel-release
if [ "$?" != "0" ]; then
    #sudo rpm -Uvh http://download.fedoraproject.org/pub/epel/${IMAGE_VERSION_MAJOR}/${IMAGE_ARCH}/epel-release-6-8.noarch.rpm >& /dev/null
    sudo rpm -Uvh https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
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

sudo rpm -q atomic-release
if [ "$?" == "0" ]; then
    sudo rpm -e atomic-release
fi

### Add remi repo
sudo rpm -q remi-release
if [ "$?" != "0" ]; then
    sudo rpm -Uvh $REMI >& /dev/null
    if [ "$?" != "0" ]; then
        echo "failed to install remi-release"
        exit 1
    else
        echo "successfully installed remi-release"
    fi
else
    echo "remi-release is already installed"
fi 

# sed -i 's/^mirrorlist=https/mirrorlist=http/g' /etc/yum.repos.d/atomic.repo

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
yum -y install net-tools
loadvars NIC "eth0"
sudo ifconfig $NIC
if [ $? -ne 0 ]; then
    echo "There is no nic '$NIC' yet"
    exit 1
fi
# sudo ifconfig $NIC | grep 'inet addr:' >& /dev/null
sudo ifconfig $NIC |grep 'inet '| cut -d ' ' -f10 >& /dev/null
if [ $? -ne 0 ]; then
    echo "There is not any IP address assigned to the NIC '$NIC' yet, please assign an IP address first."
    exit 1
fi

# export ipaddr=$(ifconfig $NIC | grep 'inet addr:' | cut -d: -f2 | awk '{ print $1}')
export ipaddr=$(ifconfig $NIC | grep 'inet ' | cut -d' ' -f10)
loadvars IPADDR ${ipaddr}
ipcalc $IPADDR -c
if [ $? -ne 0 ]; then
    echo "ip addr $IPADDR format should be x.x.x.x"
    exit 1
fi
export netmask=$(ifconfig $NIC | grep netmask | cut -d ' ' -f 13)
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

if [[ -z $SUPPORT_CENTOS_6_5 ]]; then
    echo -e "\x1b[32mWould you like to support centos6.5?(y/n)\x1b[37m"
    while true; do
        read ans
        case $ans in
            y ) export SUPPORT_CENTOS_6_5="y"; break;;
            n ) export SUPPORT_CENTOS_6_5="n"; break;;
            * ) echo "I don't understand this";;
        esac
    done
fi

if [[ -z $SUPPORT_CENTOS_6_6 ]]; then
    echo -e "\x1b[32mWould you like to support centos6.6?(y/n)\x1b[37m"
    while true; do
        read ans
        case $ans in
            y ) export SUPPORT_CENTOS_6_6="y"; break;;
            n ) export SUPPORT_CENTOS_6_6="n"; break;;
            * ) echo "I don't understand this";;
        esac
    done
fi

if [[ -z $SUPPORT_CENTOS_7_0 ]]; then
    echo -e "\x1b[32mWould you like to support centos7.0?(y/n)\x1b[37m"
    while true; do
        read ans
        case $ans in
            y ) export SUPPORT_CENTOS_7_0="y"; break;;
            n ) export SUPPORT_CENTOS_7_0="n"; break;;
            * ) echo "I don't understand this";;
        esac
    done
fi

if [[ -z $SUPPORT_UBUNTU_12_04 ]]; then
    echo -e "\x1b[32mWould you like to support ubuntu12.04?(y/n)\x1b[37m"
    while true; do
        read ans
        case $ans in
            y ) export SUPPORT_UBUNTU_12_04="y"; break;;
            n ) export SUPPORT_UBUNTU_12_04="n"; break;;
            * ) echo "I don't understand this";;
        esac
    done
fi

if [[ -z $SUPPORT_UBUNTU_14_04 ]]; then
    echo -e "\x1b[32mWould you like to support ubuntu14.04?(y/n)\x1b[37m"
    while true; do
        read ans
        case $ans in
            y ) export SUPPORT_UBUNTU_14_04="y"; break;;
            n ) export SUPPORT_UBUNTU_14_04="n"; break;;
            * ) echo "I don't understand this";;
        esac
    done
fi

if [[ -z $SUPPORT_SLES_11SP3 ]]; then
    echo -e "\x1b[32mWould you like to support sles11sp3?(y/n)\x1b[37m"
    while true; do
        read ans
        case $ans in
            y ) export SUPPORT_SLES_11SP3="y"; break;;
            n ) export SUPPORT_SLES_11SP3="n"; break;;
            * ) echo "I don't understand this";;
        esac
    done
fi

loadvars NAMESERVER_DOMAINS "ods.com"
loadvars NAMESERVER_REVERSE_ZONES "unused"
loadvars WEB_SOURCE 'http://git.openstack.org/openstack/compass-web'
loadvars ADAPTERS_SOURCE 'http://git.openstack.org/openstack/compass-adapters'

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
# source ${COMPASSDIR}/install/chef.sh || exit $?
source ${COMPASSDIR}/install/ansible.sh || exit $?

echo "Download and install Compass Web"
source ${COMPASSDIR}/install/compass_web.sh || exit $?

echo "Download and Setup Compass and related services"
source ${COMPASSDIR}/install/compass.sh || exit $?

figlet -ctf slant Installation Complete!
echo -e "It takes\x1b[32m $SECONDS \x1b[0mseconds during the installation."
