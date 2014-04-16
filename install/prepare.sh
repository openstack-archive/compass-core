#!/bin/bash
# prepare the installation

copy2dir()
{
    repo=$1
    destdir=$2
    if [[ "$repo" =~ (git|http|https|ftp):// ]]; then
        if [[ -d $destdir || -L $destdir ]]; then
            cd $destdir
            git status &> /dev/null
            if [ $? -ne 0 ]; then
                echo "$destdir is not git repo"
                rm -rf $destdir
            fi
            cd -
        fi

        if [[ -d $destdir || -L $destdir ]]; then
            echo "$destdir exists"
            cd $destdir
            git remote set-url origin $repo
            git remote update
            git reset --hard
            git clean -x -f
            git checkout master
            git reset --hard remotes/origin/master
        else
            echo "create $destdir"
            mkdir -p $destdir
            git clone $repo $destdir
            if [ $? -ne 0 ]; then
                echo "failed to git clone $repo $destdir"
                exit 1
            fi
            cd $destdir
        fi
        gerrit_repo=$3
        if [[ ! -z $gerrit_repo ]]; then
            if [[ -n "$GERRIT_REFSPEC" ]];then
                git fetch $gerrit_repo $GERRIT_REFSPEC && git checkout FETCH_HEAD
                if [ $? -ne 0 ]; then
                    echo "failed to git fetch $gerrit_repo $GERRIT_REFSPEC"
                fi
            fi
        fi
        git clean -x -f
    else
        sudo rm -rf $destdir
        sudo cp -rf $repo $destdir
        if [ $? -ne 0 ]; then
            echo "failed to copy $repo to $destdir"
            exit 1
        fi
    fi
    if [[ ! -d $destdir && ! -L $destdir ]]; then
        echo "$destdir doest not exist"
        exit 1
    fi
    cd $SCRIPT_DIR
}

# Create backup dir
sudo mkdir -p /root/backup

# update /etc/hosts
sudo cp -rn /etc/hosts /root/backup/hosts
sudo rm -f /etc/hosts
sudo cp -rf $COMPASSDIR/misc/hosts /etc/hosts
sudo sed -i "s/\$ipaddr \$hostname/$ipaddr $HOSTNAME/g" /etc/hosts
sudo chmod 644 /etc/hosts

# update rsyslog
sudo cp -rn /etc/rsyslog.conf /root/backup/
sudo rm -f /etc/rsyslog.conf
sudo cp -rf $COMPASSDIR/misc/rsyslog/rsyslog.conf /etc/rsyslog.conf
sudo chmod 644 /etc/rsyslog.conf
sudo service rsyslog restart
sudo service rsyslog status
if [[ "$?" != "0" ]]; then
    echo "rsyslog is not started"
    exit 1
else
    echo "rsyslog conf is updated"
fi

# update logrotate.d
sudo cp -rn /etc/logrotate.d /root/backup/
rm -f /etc/logrotate.d/*
sudo cp -rf $COMPASSDIR/misc/logrotate.d/* /etc/logrotate.d/
sudo chmod 644 /etc/logrotate.d/*

# update ntp conf
sudo cp -rn /etc/ntp.conf /root/backup/
sudo rm -f /etc/ntp.conf
sudo cp -rf $COMPASSDIR/misc/ntp/ntp.conf /etc/ntp.conf
sudo chmod 644 /etc/ntp.conf
sudo service ntpd stop
sudo ntpdate 0.centos.pool.ntp.org
sudo service ntpd start
sudo service ntpd status
if [[ "$?" != "0" ]]; then
    echo "ntp is not started"
    exit 1
else
    echo "ntp conf is updated"
fi

# update squid conf
sudo cp -rn /etc/squid/squid.conf /root/backup/
sudo rm -f /etc/squid/squid.conf 
sudo cp $COMPASSDIR/misc/squid/squid.conf /etc/squid/
subnet_escaped=$(echo $SUBNET | sed -e 's/[\/&]/\\&/g')
sudo sed -i "s/acl localnet src \$subnet/acl localnet src $subnet_escaped/g" /etc/squid/squid.conf
sudo chmod 644 /etc/squid/squid.conf
sudo mkdir -p /var/squid/cache
sudo chown -R squid:squid /var/squid
sudo service squid restart
sudo service squid status
if [[ "$?" != "0" ]]; then
    echo "squid is not started"
    exit 1
else
    echo "squid conf is updated"
fi

cd $SCRIPT_DIR
if [ -z $WEB_SOURCE ]; then
    echo "web source $WEB_SOURCE is not set"
    exit 1
fi
copy2dir "$WEB_SOURCE" "$WEB_HOME" "$WEB_GERRIT_URL"
if [ -z $ADAPTERS_SOURCE ]; then
    echo "adpaters source $ADAPTERS_SOURCE is not set"
    exit 1
fi
copy2dir "$ADAPTERS_SOURCE" "$ADAPTERS_HOME" "$ADAPTERS_GERRIT_URL"

if [ "$tempest" == "true" ]; then
    if [[ ! -e /tmp/tempest ]]; then
        git clone http://git.openstack.org/openstack/tempest /tmp/tempest
        cd /tmp/tempest
        git checkout grizzly-eol
    else
        cd /tmp/tempest
        git remote set-url origin http://git.openstack.org/openstack/tempest
        git remote update
        git reset --hard
        git clean -x -f -d -q
        git checkout grizzly-eol
    fi
    cd /tmp/tempest
    pip install -e .
fi

download()
{
    url=$1
    package=${2:-$(basename $url)}
    action=${3:-""}
    if [[ -f /tmp/${package} || -L /tmp/${package} ]]; then
        echo "$package already exists"
    else
        if [[ "$url" =~ (http|https|ftp):// ]]; then
            wget -c --progress=bar:force -O /tmp/${package}.tmp $url
            if [[ "$?" != "0" ]]; then
                echo "failed to download $package"
                exit 1
            else
                echo "successfully download $package"
                cp -rf /tmp/${package}.tmp /tmp/${package}
            fi
        else
            cp -rf $url /tmp/${package}
        fi
        if [[ ! -f /tmp/${package} && ! -L /tmp/${package} ]]; then
            echo "/tmp/$package is not created"
            exit 1
        fi
    fi
    if [[ "$action" == "install" ]]; then
        sudo rpm -Uvh /tmp/$package
        if [[ "$?" != "0" ]]; then
            echo "failed to install $package"
            exit 1
        else
            echo "$package is installed"
        fi
    elif [[ "$action" == "copy" ]]; then
        destdir=$4
        sudo cp /tmp/$package $destdir
    elif [[ "$action" == "unzip" ]]; then
        unzipped_package=${package%%.zip}
        sudo rm -rf /tmp/$unzipped_package
        sudo unzip -o /tmp/$package /tmp/
        sudo cp -rf /tmp/$unzipped_package/. $destdir
    fi
}

# download js mvc
download http://github.com/downloads/bitovi/javascriptmvc/$JS_MVC.zip $JS_MVC.zip unzip $WEB_HOME/public/

# download cobbler related packages
ppa_repo_packages="ntp-4.2.6p5-1.el6.${IMAGE_TYPE,,}.$IMAGE_ARCH.rpm
                    openssh-clients-5.3p1-94.el6.${IMAGE_ARCH}.rpm
                    iproute-2.6.32-31.el6.${IMAGE_ARCH}.rpm
                    wget-1.12-1.8.el6.${IMAGE_ARCH}.rpm
                    ntpdate-4.2.6p5-1.el6.${IMAGE_TYPE,,}.${IMAGE_ARCH}.rpm"
for f in $ppa_repo_packages
do
    download ftp://rpmfind.net/linux/${IMAGE_TYPE,,}/${IMAGE_VERSION_MAJOR}/os/${IMAGE_ARCH}/Packages/$f $f
done

ppa_repo_rsyslog_packages="json-c-0.10-2.el6.$IMAGE_ARCH.rpm
                           libestr-0.1.9-1.el6.$IMAGE_ARCH.rpm
                           libgt-0.3.11-1.el6.$IMAGE_ARCH.rpm
                           liblogging-1.0.4-1.el6.$IMAGE_ARCH.rpm
                           rsyslog-7.6.3-1.el6.$IMAGE_ARCH.rpm"
for f in $ppa_repo_rsyslog_packages
do
    download http://rpms.adiscon.com/v7-stable/epel-6/${IMAGE_ARCH}/RPMS/$f $f
done

download "$IMAGE_SOURCE" `basename $IMAGE_SOURCE`
download $CHEF_CLIENT `basename $CHEF_CLIENT`

# download chef related packages
download $CHEF_SRV `basename $CHEF_SRV`

# Install net-snmp
sudo cp -rn /etc/snmp/snmp.conf /root/backup/
sudo mkdir -p /usr/local/share/snmp/
sudo cp -rf $COMPASSDIR/mibs /usr/local/share/snmp/
sudo rm -f /etc/snmp/snmp.conf
sudo cp -rf $COMPASSDIR/misc/snmp/snmp.conf /etc/snmp/snmp.conf
sudo chmod 644 /etc/snmp/snmp.conf
sudo mkdir -p /var/lib/net-snmp/mib_indexes
sudo chmod 755 /var/lib/net-snmp/mib_indexes

# generate ssh key
if [ ! -e $HOME/.ssh/id_rsa.pub ]; then
    rm -rf $HOME/.ssh/id_rsa
    ssh-keygen -t rsa -f $HOME/.ssh/id_rsa -q -N ''
fi
