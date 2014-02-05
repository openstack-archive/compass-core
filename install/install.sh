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
loadvars WEB_SOURCE ${DIR}/../web
loadvars ADAPTER_SOURCE ${DIR}/../misc
else
loadvars WEB_SOURCE 'https://github.com/stackforge/compass-web'
loadvars ADAPTER_SOURCE 'https://github.com/stackforge/compass-adapters' 
fi

echo "Install the Dependencies"
source $DIR/dependency.sh

SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
echo "script dir: $SCRIPT_DIR"
COMPASSDIR=${SCRIPT_DIR}/..
echo "compass dir is $COMPASSDIR"

copygit2dir()
{
    repo=$1
    destdir=$2
    if [ -d $destdir ];then
        echo "$destdir exists"
        git remote set-url origin $repo
        git remote update
        git reset --hard
        git clean -x -f
        git checkout master
        git reset --hard remotes/origin/master
        if [[ -n "$GERRIT_REFSPEC" ]];then
            git fetch origin $GERRIT_REFSPEC && git checkout FETCH_HEAD
        fi
        git clean -x -f
    else
        mkdir -p $destdir
        git clone $repo $destdir
        if [[ -n "$GERRIT_REFSPEC" ]];then
            # project=$(echo $repo|rev|cut -d '/' -f 1|rev)
            cd $destdir
            git fetch $repo $GERRIT_REFSPEC && git checkout FETCH_HEAD
        fi
    fi
    cd $SCRIPT_DIR
}

copylocal2dir()
{
    repo=$1
    destdir=$2
    if [ -d $destdir ];then
        echo "$destdir exists"
    else
        mkdir -p $destdir
    fi
    sudo cp -rf $repo/* $destdir
}

cd $SCRIPT_DIR
WEB_HOME=${WEB_HOME:-'/tmp/web/'}
ADAPTER_HOME=${ADAPTER_HOME:-'/tmp/adapter/'}
WEB_SOURCE=${WEB_SOURCE:-$REPO_URL'/stackforge/compass-web'}
ADAPTER_SOURCE=${ADAPTER_SOURCE:-$REPO_URL'/stackforge/compass-adapters'}
if [ "$source" != "local" ]; then
  copygit2dir $WEB_SOURCE $WEB_HOME
  copygit2dir $ADAPTER_SOURCE $ADAPTER_HOME
else 
  copylocal2dir $WEB_SOURCE $WEB_HOME
  copylocal2dir $ADAPTER_SOURCE $ADAPTER_HOME
fi

# install js mvc package
wget -c --progress=bar:force -O /tmp/$JS_MVC.zip http://github.com/downloads/bitovi/javascriptmvc/$JS_MVC.zip
if [[ "$?" != "0" ]]; then
echo "failed to download $JS_MVC"
exit 1
fi

if [ -d /tmp/$JS_MVC ]; then
echo "/tmp/$JS_MVC is already unzipped"
else
sudo unzip -o /tmp/$JS_MVC.zip -d /tmp/
fi
sudo cp -rf /tmp/$JS_MVC/. $WEB_HOME/public/

# Create backup dir
sudo mkdir -p /root/backup

echo "Install the OS Installer Tool"
source $DIR/$OS_INSTALLER.sh

echo "Install the Package Installer Tool"
source $DIR/$PACKAGE_INSTALLER.sh

echo "Download and Setup Compass and related services"
source $DIR/compass.sh

echo -e "It takes\x1b[32m $SECONDS \x1b[0mseconds during the installation."
