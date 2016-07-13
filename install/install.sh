#!/bin/bash
#
#set -x
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

set_iptables()
{
  # external_ipaddr=$1; install_ipaddr=$2; install_netmask=$3

  local argument_error="ERROR: argument ARG_NUM is invalidation that is for ARG_DESC"
  local varnames=("3" "external_ipaddr" "install_ipaddr" "install_netmask")
  if [ $# -lt ${varnames[0]} ];then
    echo "ERROR: please input ${varnames[0]} arguments to call function _set_iptables()";exit 1
  fi
  local i=1
  while [ $1 ];do
    eval "${varnames[i]}"=$1
    sudo ipcalc $1 -c
    if [ $? -ne 0 ];then
      echo ${argument_error} | sed 's/ARG_NUM/'"$i"'/g' | sed 's/ARG_DESC/g'"${varnames[i]}"'/g';exit 1
    fi
    let i++;shift
  done

  local install_netaddr=$(sudo ipcalc ${install_ipaddr} ${install_netmask} -n | awk -F = '{print $2}')
  local install_netprefix=$(sudo ipcalc ${install_ipaddr} ${install_netmask} -p | awk -F = '{print $2}')

  sudo sed -i '/^\s*net\.ipv4\.ip_forward\s*=/d' /etc/sysctl.conf
  sudo sed -i '$a net.ipv4.ip_forward=1' /etc/sysctl.conf
  sudo sysctl -p

  sudo rpm -qa | grep iptables-services
  if [ $? -ne 0  ]; then
    sudo yum -y install iptables-services
  fi

  sudo /bin/systemctl status iptables.service
  if [ $? -eq 0 ];then
    sudo /usr/sbin/service iptables save
    sudo /bin/systemctl stop iptables.service
  fi

  sudo mkdir /etc/sysconfig/iptables.bak.d 2>/dev/null
  if [ -f /etc/sysconfig/iptables ];then
    sudo mv -f /etc/sysconfig/iptables /etc/sysconfig/iptables.bak.d/$(uuidgen)
  fi

  iptables_config=" *filter\n
                    :INPUT ACCEPT [0:0]\n
                    :FORWARD ACCEPT [0:0]\n
                    :OUTPUT ACCEPT [0:0]\n
                    COMMIT\n
                    *nat\n
                    :PREROUTING ACCEPT [0:0]\n
                    :INPUT ACCEPT [0:0]\n
                    :OUTPUT ACCEPT [0:0]\n
                    :POSTROUTING ACCEPT [0:0]\n
                    -A POSTROUTING -s ${install_ipaddr}/32 -j ACCEPT\n
                    -A POSTROUTING -s ${install_netaddr}/${install_netprefix} -j SNAT --to-source ${external_ipaddr}\n
                    COMMIT\n"
  sudo echo -e ${iptables_config} | sed 's/^\s*//g' > /etc/sysconfig/iptables

  sudo /bin/systemctl enable iptables
  sudo /bin/systemctl start iptables.service
}

# convert between ip address and integers
ipaddr_to_int()
{
    ipaddr=$1
    IFS=. read -r a b c d <<< "$ipaddr"
    printf '%d\n' "$((a * 256 ** 3 + b * 256 ** 2 + c * 256 + d))"
}
int_to_ipaddr()
{
    ipint=$1
    let a=ipint/$[256**3];let ipint%=$[256**3]
    let b=ipint/$[256**2];let ipint%=$[256**2]
    let c=ipint/256;let ipint%=256
    let d=ipint
    printf '%d.%d.%d.%d\n' $a $b $c $d
}


### BEGIN OF SCRIPT  

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

### LOAD FILE CONFIGURATION
source $DIR/install.conf


### Change selinux security policy
sudo setenforce 0
sudo sed -i 's/enforcing/disabled/g' /etc/selinux/config
### Add epel repo
sudo rpm -q epel-release
if [ "$?" != "0" ]; then
    sudo rpm -Uvh $EPEL
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
  var=$(echo $param | awk -F = '{print $1}')
  val=$(echo $param | awk -F = '{print $2}')
  eval export $var=$val  
  shift
done

yum update -y
sudo rpm -qa | grep net-tools
if [ $? -ne 0 ];then
  yum -y install net-tools
fi

# check the correct format of ip variables
ip_vars="PUBLIC_IP PUBLIC_NETMASK PUBLIC_GATEWAY 
         IPADDR NETMASK 
         OPTION_ROUTER NEXTSERVER IP_START IP_END"
for ip_var in ${ip_vars}; do
  eval ip_val=\$${ip_var}
  if [ ! -z ${ip_val} ];then
    ipcalc ${ip_val} -c
    if [ $? -ne 0 ];then
      echo "The variable of '${ip_var}'='${ip_val}' is invalid."
      exit 1
    fi
  fi
done

# public network variables:
export PUBLIC_NIC=${PUBLIC_NIC:-"eth0"}
export PUBLIC_IP=${PUBLIC_IP:-$(sudo ifconfig ${PUBLIC_NIC} | awk '($1=="inet"){print $2}')}
export PUBLIC_GATEWAY=${PUBLIC_GATEWAY:-$(sudo route -n | awk '($1=="0.0.0.0" && $3=="0.0.0.0"){print $2}')}

if [ -z ${PUBLIC_IP} ];then
  echo "ERROR: There is not any PUBLIC_IP to be set yet, please assign an IP to PUBLIC_NIC or configure 'install.conf' first."
  exit 1
elif [ -z ${PUBLIC_GATEWAY} ];then
  echo "WARNING: There is not any PUBLIC_GATEWAY, please ensure that the agent server can access remote compass center if no gateway."
  sleep 2
fi

export PUBLIC_NETMASK=${PUBLIC_NETMASK:-$(sudo ifconfig ${PUBLIC_NIC} | awk '($3=="netmask"){print $4}')}
export PUBLIC_NETMASK=${PUBLIC_NETMASK:-$(sudo ipcalc ${PUBLIC_IP} -m | awk -F = '{print $2}')}

if [[ $(ipcalc ${PUBLIC_IP} ${PUBLIC_NETMASK} -n) != $(ipcalc ${PUBLIC_GATEWAY} ${PUBLIC_NETMASK} -n) ]];then
  echo "ERROR: The PUBLIC_IP:${PUBLIC_IP} and PUBLIC_GATEWAY:${PUBLIC_GATEWAY} are not in the same subnet, please check the configuration."
  exit 1
fi

sudo ifconfig ${PUBLIC_NIC} ${PUBLIC_IP} netmask ${PUBLIC_NETMASK} up

if [ ! -z ${PUBLIC_GATEWAY} ];then
  sudo route del -net 0.0.0.0/0
  sudo route add -net 0.0.0.0/0 gw ${PUBLIC_GATEWAY}
fi

# install network variables:
export NIC=${NIC:-"eth1"}
export IPADDR=${IPADDR:-$(sudo ifconfig ${NIC} | awk '($1=="inet"){print $2}')}
export IPADDR=${IPADDR:-"10.1.0.15"}
export NETMASK=${NETMASK:-$(sudo ifconfig ${NIC} | awk '($3="netmask"){print $4}')}
export NETMASK=${NETMASK:-"255.255.255.0"}

sudo ifconfig ${NIC} ${IPADDR} netmask ${NETMASK} up

export OPTION_ROUTER=${OPTION_ROUTE:-${IPADDR}}
export NEXTSERVER=${NEXTSERVER:-${IPADDR}}

if [ -z ${IP_START} ];then
  temp_int=$(ipaddr-to-int ${IPADDR})
  let temp_int++
  IP_START=$(int-to-ipaddr ${temp_int}) 
fi
export IP_START

if [ -z ${IP_END} ];then
  broad_addr=$(sudo ipcalc ${IPADDR} ${NETMASK} -b | awk -F = '{print $2}')
  temp_int=$(ipadd-to-int ${broad_addr})
  let temp_int--
  IP_END=$(int-to-ipaddr ${temp_int})
fi
export IP_END

# check the validation of IP_START and IP_END
for ip_var in IP_START IP_END;do
  if [[ $(eval ipcalc \$${ip_var} ${NETMASK} -n) != $(ipcalc ${IPADDR} ${NETMASK} -n) ]];then
    eval echo "ERROR: The ${ip_var}:\$${ip_var} and install nic are not in the same subnet.";
    exit 1
  fi
done
ip_start_int=$(ipaddr_to_int ${IP_START})
ip_end_int=$(ipaddr_to_int ${IP_END})
let ip_range=${ip_end_int}-${ip_start_int}
if [ ${ip_range} -le 0 ];then
  echo "There is no avialable IPs between IP_START:'${IP_START}' and IP_END:'${IP_END}'."
  exit 1
fi

# print all variables about IP
for ip_var in ${ip_vars};do
  eval echo "${ip_var}=\$${ip_var}"
done

export NAMESERVER_DOMAINS=${NAMESERVER_DOMAINS:-"ods.com"}
export NAMESERVER_REVERSE_ZONES=${NAMESERVER_REVERSE_ZONES:-"unused"}
export WEB_SOURCE=${WEB_SOURCE:-"http://git.openstack.org/openstack/compass-web"}
export ADAPTERS_SOURCE=${ADAPTERS_SOURCE:-"https://gerrit.opnfv.org/gerrit/compass4nfv"}

echo "set the iptables' rules so that the openstack hosts installed can access remote compass through agent server"
set_iptables ${PUBLIC_IP} ${IPADDR} ${NETMASK}

rm -rf /etc/yum.repos.d/compass_install.repo 2>/dev/nullcp 
cp ${COMPASSDIR}/misc/compass_install.repo /etc/yum.repos.d/

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

if [ "$FULL_COMPASS_SERVER" == "true"]; then
    echo "Download and install Compass Web"
    source ${COMPASSDIR}/install/compass_web.sh || exit $?
fi

echo "Download and Setup Compass and related services"
source ${COMPASSDIR}/install/compass.sh || exit $?

figlet -ctf slant Installation Complete!
echo -e "It takes\x1b[32m $SECONDS \x1b[0mseconds during the installation."

if [ "$FULL_COMPASS_SERVER" == "false" ]; then
    machine_list_conf="MACHINE_LIST = [ { '${switch_IP}': [ "
    for host in ${PXE_MACs[@]}; do
        port=$(echo ${host} | awk -F , '{print $1}' | awk -F = '{print $2}')
        mac=$(echo ${host} | awk -F , '{print $2}' | awk -F = '{print $2}')
        machine_list_conf="${machine_list_conf}${comma}\n{'port': '${port}', 'mac': '${mac}', 'vlan': '0'}"
        comma=","
    done
    machine_list_conf="${machine_list_conf}\n ] } ]"
    sudo echo -e ${machine_list_conf} > /etc/compass/machine_list/machine_list.conf

#    rm -rf /var/ansible/roles/keystone/vars/Debian.yml 2>/dev/null
#    cp ${COMPASSDIR}/misc/adapter_changes/Debian.yml /var/ansible/roles/keystone/vars/
#    rm -rf /var/ansible/roles/keystone/tasks/keystone_install.yml 2>/dev/null
#    cp ${COMPASSDIR}/misc/adapter_changes/keystone_install.yml /var/ansible/roles/keystone/tasks/
#    rm -rf /var/ansible/openstack_mitaka/HA-ansible-multinodes.yml 2>/dev/null
#    cp ${COMPASSDIR}/misc/adapter_changes/HA-ansible-multinodes.yml /var/ansible/openstack_mitaka/
    rm -rf /var/lib/cobbler/snippets/preseed_post_anamon 2>/dev/null
    cp ${COMPASSDIR}/misc/adapter_changes/preseed_post_anamon /var/lib/cobbler/snippets/

    sed -i 's/^CELERY_DEFAULT_QUEUE.*/CELERY_DEFAULT_QUEUE = \"'"${USER_EMAIL}"'\"/g' /etc/compass/celeryconfig
    sed -i 's/^CELERY_DEFAULT_EXCHANGE.*/CELERY_DEFAULT_EXCHANGE = \"'"${USER_EMAIL}"'\"/g' /etc/compass/celeryconfig
    sed -i 's/^CELERY_DEFAULT_ROUTING_KEY.*/CELERY_DEFAULT_ROUTING_KEY = \"'"${USER_EMAIL}"'\"/g' /etc/compass/celeryconfig

    # Restart services
    systemctl restart httpd.service
    sleep 10
    echo "Checking if httpd is running"
    sudo systemctl status httpd.service
    if [[ "$?" == "0" ]]; then
        echo "httpd is running"
    else
        echo "httpd is not running"
        exit 1
    fi

    systemctl restart compass-celeryd.service
    echo "Checking if httpd is running"
    sudo systemctl status compass-celeryd.service
    if [[ "$?" == "0" ]]; then
        echo "celeryd is running"
    else
        echo "celeryd is not running"
        exit 1
    fi
fi
