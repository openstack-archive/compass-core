#!/bin/bash
#
copygit2dir()
{
    repo=$1
    destdir=$2
    if [ -d $destdir ];then
        echo "$destdir exists"
        cd $destdir
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
        echo "create $destdir"
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
if [ "$source" != "local" ]; then
  copygit2dir $WEB_SOURCE $WEB_HOME
  copygit2dir $ADAPTER_SOURCE $ADAPTER_HOME
else 
  copylocal2dir $WEB_SOURCE $WEB_HOME
  copylocal2dir $ADAPTER_SOURCE $ADAPTER_HOME
fi

# download chef-server package
if [[ -f /tmp/chef-server-11.0.8-1.el6.${IMAGE_ARCH}.rpm ]]; then
    echo "chef-server-11.0.8-1.el6.${IMAGE_ARCH}.rpm already exists"
else
    wget -c --progress=bar:force -O /tmp/chef-server-11.0.8-1.el6.${IMAGE_ARCH}.rpm $CHEF_SRV
    if [[ "$?" != "0" ]]; then
        echo "failed to download chef-server-11.0.8-1.el6.${IMAGE_ARCH}.rpm"
        exit 1
    else
        echo "successfully download chef-server-11.0.8-1.el6.${IMAGE_ARCH}.rpm"
    fi
fi

# download centos image
if [[ -f /tmp/${IMAGE_NAME}-${IMAGE_ARCH}.iso ]]; then
    echo "/tmp/${IMAGE_NAME}-${IMAGE_ARCH}.iso already exists"
else
    sudo wget -c --progress=bar:force -O /tmp/${IMAGE_NAME}-${IMAGE_ARCH}.iso "$IMAGE_SOURCE"
    if [[ "$?" != "0" ]]; then
        echo "failed to download ${IMAGE_NAME}-${IMAGE_ARCH}.iso"
        exit 1
    else
        echo "successfully download ${IMAGE_NAME}-${IMAGE_ARCH}.iso"
    fi
fi

# download ppa_repo packages
ppa_repo_packages="ntp-4.2.6p5-1.el6.${IMAGE_TYPE}.$IMAGE_ARCH.rpm 
                   openssh-clients-5.3p1-94.1.el6.${IMAGE_ARCH}.rpm 
                   iproute-2.6.32-31.el6.${IMAGE_ARCH}.rpm
                   wget-1.12-1.8.el6.${IMAGE_ARCH}.rpm
                   ntpdate-4.2.6p5-1.el6.${IMAGE_TYPE}.${IMAGE_ARCH}.rpm"
for f in $ppa_repo_packages
do 
    if [ -f /tmp/$f ]; then
        echo "$f already exists"
    else
        sudo wget -c --progress=bar:force -O /tmp/$f ftp://rpmfind.net/linux/${IMAGE_TYPE,,}/${IMAGE_VERSION_MAJOR}/os/${IMAGE_ARCH}/Packages/$f
        if [[ "$?" != "0" ]]; then
            echo "fail to download $f"
        else 
            echo "successfully download $f"
        fi
    fi
done

if [[ ! -e /tmp/chef-11.8.0-1.el6.${IMAGE_ARCH}.rpm ]]; then
    sudo wget -c --progress=bar:force -O /tmp/chef-11.8.0-1.el6.${IMAGE_ARCH}.rpm http://opscode-omnibus-packages.s3.amazonaws.com/el/${IMAGE_VERSION_MAJOR}/${IMAGE_ARCH}/chef-11.8.0-1.el6.${IMAGE_ARCH}.rpm
else
    echo "chef-11.8.0-1.el6.${IMAGE_ARCH}.rpm already exists"
fi        

# install js mvc package
if [[ -f /tmp/$JS_MVC.zip ]]; then
    echo "$JS_MVC.zip already exists"
else
    wget -c --progress=bar:force -O /tmp/$JS_MVC.zip http://github.com/downloads/bitovi/javascriptmvc/$JS_MVC.zip
    if [[ "$?" != "0" ]]; then
        echo "failed to download $JS_MVC"
        exit 1
    else
        echo "successfully download $JS_MVC"
    fi
fi

if [ -d /tmp/$JS_MVC ]; then
echo "/tmp/$JS_MVC is already unzipped"
else
sudo unzip -o /tmp/$JS_MVC.zip -d /tmp/
fi
sudo cp -rf /tmp/$JS_MVC/. $WEB_HOME/public/

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

# Install net-snmp
sudo cp -rn /etc/snmp/snmp.conf /root/backup/
sudo mkdir -p /usr/local/share/snmp/
sudo cp -rf $COMPASSDIR/mibs /usr/local/share/snmp/
sudo rm -f /etc/snmp/snmp.conf
sudo cp -rf $COMPASSDIR/misc/snmp/snmp.conf /etc/snmp/snmp.conf
sudo chmod 644 /etc/snmp/snmp.conf
