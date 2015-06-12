#!/bin/bash
#

echo "Installing cobbler"
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
source $DIR/install.conf
if [ -f $DIR/env.conf ]; then
    source $DIR/env.conf
else
    echo "failed to load environment"
    exit 1
fi
source $DIR/install_func.sh

echo "Installing cobbler related packages"
sudo yum -y install cobbler cobbler-web createrepo mkisofs python-cheetah python-simplejson python-urlgrabber PyYAML Django cman debmirror pykickstart reprepro
if [[ "$?" != "0" ]]; then
    echo "failed to install cobbler related packages"
    exit 1
else
    # patch cobbler code
    find /usr/lib -name manage_bind.py |xargs  perl -pi.old -e 's/(\s+)(self\.logger\s+\= logger)/$1$2\n$1if self\.logger is None:\n$1    import clogger\n$1    self\.logger = clogger.Logger\(\)/'
fi

# cobbler snippet uses netaddr to calc subnet and ip addr
sudo pip install netaddr
if [[ "$?" != "0" ]]; then
    echo "failed to install pip packages"
    exit 1
fi

sudo chkconfig cobblerd on

# create backup dir
sudo mkdir -p /root/backup/cobbler

# update httpd conf
sudo cp -rn /etc/httpd/conf.d /root/backup/cobbler/
sudo rm -f /etc/httpd/conf.d/cobbler_web.conf
sudo cp -rf $COMPASSDIR/misc/apache/cobbler_web.conf /etc/httpd/conf.d/cobbler_web.conf
chmod 644 /etc/httpd/conf.d/cobbler_web.conf
sudo rm -rf /etc/httpd/conf.d/ssl.conf
sudo cp -rf $COMPASSDIR/misc/apache/ssl.conf /etc/httpd/conf.d/ssl.conf
chmod 644 /etc/httpd/conf.d/ssl.conf

# disable selinux
sudo mkdir -p /root/backup/selinux
sudo cp -rn /etc/selinux/config /root/backup/selinux/
sudo sed -i '/SELINUX/s/enforcing/disabled/' /etc/selinux/config

# update cobbler settings
sudo cp -rn /etc/cobbler/settings /root/backup/cobbler/
sudo rm -f /etc/cobbler/settings
sudo cp -rf $ADAPTERS_HOME/cobbler/conf/settings /etc/cobbler/settings
sudo sed -i "s/next_server:[ \t]*\$next_server/next_server: $NEXTSERVER/g" /etc/cobbler/settings
sudo sed -i "s/server:[ \t]*\$ipaddr/server: $IPADDR/g" /etc/cobbler/settings
sudo sed -i "s/default_name_servers:[ \t]*\['\$ipaddr'\]/default_name_servers: \['$IPADDR'\]/g" /etc/cobbler/settings
domains=$(echo $NAMESERVER_DOMAINS | sed "s/,/','/g")
sudo sed -i "s/manage_forward_zones:[ \t]*\[\]/manage_forward_zones: \['$domains'\]/g" /etc/cobbler/settings
if [[ "$NAMESERVER_REVERSE_ZONES" != "unused" ]]; then
    reverse_zones=$(echo $NAMESERVER_REVERSE_ZONES | sed "s/,/','/g")
    sudo sed -i "s/manage_reverse_zones:[ \t]*\[\]/manage_reverse_zones: \['$reverse_zones'\]/g" /etc/cobbler/settings
fi
export cobbler_passwd=$(openssl passwd -1 -salt 'huawei' '123456')
sudo sed -i "s,^default_password_crypted:[ \t]\+\"\(.*\)\",default_password_crypted: \"$cobbler_passwd\",g" /etc/cobbler/settings
sudo chmod 644 /etc/cobbler/settings

# update dhcp.template
sudo cp -rn /etc/cobbler/dhcp.template /root/backup/cobbler/
sudo rm -f /etc/cobbler/dhcp.template
sudo cp -rf $ADAPTERS_HOME/cobbler/conf/dhcp.template /etc/cobbler/dhcp.template
export netaddr=$(ipcalc $IPADDR $NETMASK -n |cut -f 2 -d '=')
export netprefix=$(ipcalc $IPADDR $NETMASK -p |cut -f 2 -d '=')
export subnet=${netaddr}/${netprefix}
sudo sed -i "s/subnet \$subnet netmask \$netmask/subnet $netaddr netmask $NETMASK/g" /etc/cobbler/dhcp.template
sudo sed -i "s/option routers \$gateway/option routers $OPTION_ROUTER/g" /etc/cobbler/dhcp.template
sudo sed -i "s/option subnet-mask \$netmask/option subnet-mask $NETMASK/g" /etc/cobbler/dhcp.template
sudo sed -i "s/option domain-name-servers \$ipaddr/option domain-name-servers $IPADDR/g" /etc/cobbler/dhcp.template
sudo sed -i "s/range dynamic-bootp \$ip_range/range dynamic-bootp $IP_START $IP_END/g" /etc/cobbler/dhcp.template
sudo sed -i "s/local-address \$ipaddr/local-address $IPADDR/g" /etc/cobbler/dhcp.template
sudo chmod 644 /etc/cobbler/dhcp.template

# update tftpd.template
sudo cp -rn /etc/cobbler/tftpd.template /root/backup/cobbler/
sudo rm -f /etc/cobbler/tftpd.template
sudo cp -rf $ADAPTERS_HOME/cobbler/conf/tftpd.template /etc/cobbler/tftpd.template
sudo chmod 644 /etc/cobbler/tftpd.template

# update named.template
sudo cp -rn /etc/cobbler/named.template /root/backup/cobbler/
sudo rm -f /etc/cobbler/named.template
sudo cp -rf $ADAPTERS_HOME/cobbler/conf/named.template /etc/cobbler/named.template
sudo sed -i "s/listen-on port 53 { \$ipaddr; }/listen-on port 53 \{ $IPADDR; \}/g" /etc/cobbler/named.template
subnet_escaped=$(echo $subnet | sed -e 's/[\/&]/\\&/g')
sudo sed -i "s/allow-query { 127.0.0.0\/8; \$subnet; }/allow-query \{ 127.0.0.0\/8; $subnet_escaped; \}/g" /etc/cobbler/named.template
sudo chmod 644 /etc/cobbler/named.template

# update zone.template
sudo cp -rn /etc/cobbler/zone.template /root/backup/cobbler/
sudo rm -f /etc/cobbler/zone.template
sudo cp -rf $ADAPTERS_HOME/cobbler/conf/zone.template /etc/cobbler/zone.template
sudo sed -i "s/\$hostname IN A \$ipaddr/$HOSTNAME IN A $IPADDR/g" /etc/cobbler/zone.template
sudo sed -i "s/metrics IN A \$ipaddr/metrics IN A $IPADDR/g" /etc/cobbler/zone.template
sudo chmod 644 /etc/cobbler/zone.template

# update modules.conf
sudo cp -rn /etc/cobbler/modules.conf /root/backup/cobbler/
sudo rm -f /etc/cobbler/modules.conf
sudo cp -rf $ADAPTERS_HOME/cobbler/conf/modules.conf /etc/cobbler/modules.conf
sudo chmod 644 /etc/cobbler/modules.conf

echo "setting up cobbler web password: default user is cobbler"

CBLR_USER=${CBLR_USER:-"cobbler"}
CBLR_PASSWD=${CBLR_PASSWD:-"cobbler"}
(echo -n "$CBLR_USER:Cobbler:" && echo -n "$CBLR_USER:Cobbler:$CBLR_PASSWD" | md5sum - | cut -d' ' -f1) > /etc/cobbler/users.digest

# update cobbler config
sudo cp -rn /var/lib/cobbler/snippets /root/backup/cobbler/
sudo cp -rn /var/lib/cobbler/scripts /root/backup/cobbler
sudo cp -rn /var/lib/cobbler/kickstarts/ /root/backup/cobbler/
sudo cp -rn /var/lib/cobbler/triggers /root/backup/cobbler/
sudo rm -rf /var/lib/cobbler/scripts/*
sudo rm -rf /var/lib/cobbler/snippets/*
sudo rm -rf /var/lib/cobbler/kickstarts/*
sudo cp -rf $ADAPTERS_HOME/cobbler/snippets/* /var/lib/cobbler/snippets/
sudo cp -rf $ADAPTERS_HOME/cobbler/scripts/* /var/lib/cobbler/scripts/
sudo cp -rf $ADAPTERS_HOME/cobbler/triggers/* /var/lib/cobbler/triggers/
sudo chmod 777 /var/lib/cobbler/snippets
sudo chmod 777 /var/lib/cobbler/scripts
sudo chmod -R 666 /var/lib/cobbler/snippets/*
sudo chmod -R 666 /var/lib/cobbler/scripts/*
sudo chmod -R 755 /var/lib/cobbler/triggers
sudo cp -rf $ADAPTERS_HOME/cobbler/kickstarts/* /var/lib/cobbler/kickstarts/
sudo chmod 666 /var/lib/cobbler/kickstarts/*
sudo mkdir -p /var/www/cblr_ks
sudo chmod 755 /var/www/cblr_ks
sudo cp -rf $ADAPTERS_HOME/cobbler/conf/cobbler.conf /etc/httpd/conf.d/
chmod 644 /etc/httpd/conf.d/cobbler.conf

sudo cp -rn /etc/xinetd.d /root/backup/
sudo sed -i 's/disable\([ \t]\+\)=\([ \t]\+\)yes/disable\1=\2no/g' /etc/xinetd.d/rsync
sudo sed -i 's/^@dists=/# @dists=/g' /etc/debmirror.conf
sudo sed -i 's/^@arches=/# @arches=/g' /etc/debmirror.conf

sudo rm -rf /var/lib/cobbler/config/systems.d/*

echo "disable iptables"
sudo service iptables stop
sudo sleep 10
sudo service iptables status
if [[ "$?" == "0" ]]; then
    echo "iptables is running"
    exit 1
else
    echo "iptables is already stopped"
fi

echo "disable selinux temporarily"
echo 0 > /selinux/enforce

# make log dir
sudo mkdir -p /var/log/cobbler
sudo mkdir -p /var/log/cobbler/tasks
sudo mkdir -p /var/log/cobbler/anamon
sudo chmod -R 777 /var/log/cobbler

# kill dnsmasq service
if `sudo chkconfig --list dnsmasq`; then
    sudo chkconfig dnsmasq off
    sudo service dnsmasq stop
fi
sudo killall -9 dnsmasq

sudo service httpd restart
sudo service cobblerd restart

sudo cobbler get-loaders
if [[ "$?" != "0" ]]; then
    echo "failed to get loaders for cobbler"
    exit 1
else
    echo "cobbler loaders updated"
fi

sudo cobbler sync
if [[ "$?" != "0" ]]; then
    echo "failed to sync cobbler"
    exit 1
else
    echo "cobbler synced"
fi

sudo service xinetd restart

sudo sleep 10

echo "Checking if httpd is running"
sudo service httpd status
if [[ "$?" == "0" ]]; then
    echo "httpd is running."
else
    echo "httpd is not running"
    exit 1
fi

echo "Checking if dhcpd is running"
sudo service dhcpd status
if [[ "$?" == "0" ]]; then
    echo "dhcpd is running."
else
    echo "dhcpd is not running"
    exit 1
fi

echo "Checking if named is running"
sudo service named status
if [[ "$?" == "0" ]]; then
    echo "named is running."
else
    echo "named is not running"
    exit 1
fi

echo "Checking if xinetd is running"
sudo service xinetd status
if [[ "$?" == "0" ]]; then
    echo "xinetd is running."
else
    echo "xinetd is not running"
    exit 1
fi

echo "Checking if cobblerd is running"
sudo service cobblerd status
if [[ "$?" == "0" ]]; then
    echo "cobblerd is running."
else
    echo "cobblerd is not running"
    exit 1
fi

sudo mkdir -p /var/lib/cobbler/repo_mirror
# create centos repo
if [[ $SUPPORT_CENTOS_6_5 == "y" ]]; then
    sudo mkdir -p /var/lib/cobbler/repo_mirror/centos_6_5_ppa_repo
    found_centos_6_5_ppa_repo=0
    for repo in $(cobbler repo list); do
        if [ "$repo" == "centos_6_5_ppa_repo" ]; then
            found_centos_6_5_ppa_repo=1
        fi
    done

    if [ "$found_centos_6_5_ppa_repo" == "0" ]; then
        sudo cobbler repo add --mirror=/var/lib/cobbler/repo_mirror/centos_6_5_ppa_repo --name=centos_6_5_ppa_repo --mirror-locally=Y --arch=x86_64
        if [[ "$?" != "0" ]]; then
            echo "failed to add centos_6_5_ppa_repo"
            exit 1
        else
            echo "centos_6_5_ppa_repo is added"
        fi
    else
        echo "repo centos_6_5_ppa_repo has already existed."
    fi

    # download packages
    download -u "$CENTOS_6_5_PPA_REPO_SOURCE" -u "$CENTOS_6_5_PPA_REPO_SOURCE_ASIA" centos_6_5_ppa_repo.tar.gz unzip /var/lib/cobbler/repo_mirror || exit $?
fi

if [[ $SUPPORT_CENTOS_6_6 == "y" ]]; then
    sudo mkdir -p /var/lib/cobbler/repo_mirror/centos_6_6_ppa_repo
    found_centos_6_6_ppa_repo=0
    for repo in $(cobbler repo list); do
        if [ "$repo" == "centos_6_6_ppa_repo" ]; then
            found_centos_6_6_ppa_repo=1
        fi
    done

    if [ "$found_centos_6_6_ppa_repo" == "0" ]; then
        sudo cobbler repo add --mirror=/var/lib/cobbler/repo_mirror/centos_6_6_ppa_repo --name=centos_6_6_ppa_repo --mirror-locally=Y --arch=x86_64
        if [[ "$?" != "0" ]]; then
            echo "failed to add centos_6_6_ppa_repo"
            exit 1
        else
            echo "centos_6_6_ppa_repo is added"
        fi
    else
        echo "repo centos_6_6_ppa_repo has already existed."
    fi

    # download packages
    download -u "$CENTOS_6_6_PPA_REPO_SOURCE" -u "$CENTOS_6_6_PPA_REPO_SOURCE_ASIA" centos_6_6_ppa_repo.tar.gz unzip /var/lib/cobbler/repo_mirror || exit $?
fi

if [[ $SUPPORT_CENTOS_7_0 == "y" ]]; then
    sudo mkdir -p /var/lib/cobbler/repo_mirror/centos_7_0_ppa_repo
    found_centos_7_0_ppa_repo=0
    for repo in $(cobbler repo list); do
        if [ "$repo" == "centos_7_0_ppa_repo" ]; then
            found_centos_7_0_ppa_repo=1
        fi
    done

    if [ "$found_centos_7_0_ppa_repo" == "0" ]; then
        sudo cobbler repo add --mirror=/var/lib/cobbler/repo_mirror/centos_7_0_ppa_repo --name=centos_7_0_ppa_repo --mirror-locally=Y --arch=x86_64
        if [[ "$?" != "0" ]]; then
            echo "failed to add centos_7_0_ppa_repo"
            exit 1
        else
            echo "centos_7_0_ppa_repo is added"
        fi
    else
        echo "repo centos_7_0_ppa_repo has already existed."
    fi

    # download packages
    download -u "$CENTOS_7_0_PPA_REPO_SOURCE" -u "$CENTOS_7_0_PPA_REPO_SOURCE_ASIA" centos_7_0_ppa_repo.tar.gz unzip /var/lib/cobbler/repo_mirror || exit $?
fi


# create ubuntu repo
if [[ $SUPPORT_UBUNTU_12_04 == "y" ]]; then
    sudo mkdir -p /var/lib/cobbler/repo_mirror/ubuntu_12_04_ppa_repo
    found_ubuntu_12_04_ppa_repo=0
    for repo in $(cobbler repo list); do
        if [ "$repo" == "ubuntu_12_04_ppa_repo" ]; then
            found_ubuntu_12_04_ppa_repo=1
        fi
    done

    if [ "$found_ubuntu_12_04_ppa_repo" == "0" ]; then
        sudo cobbler repo add --mirror=/var/lib/cobbler/repo_mirror/ubuntu_12_04_ppa_repo --name=ubuntu_12_04_ppa_repo --mirror-locally=Y --arch=x86_64 --apt-dists=ppa --apt-components=main
        if [[ "$?" != "0" ]]; then
            echo "failed to add ubuntu_12_04_ppa_repo"
            exit 1
        else
            echo "ubuntu_12_04_ppa_repo is added"
        fi
    else
        echo "repo ubuntu_12_04_ppa_repo has already existed."
    fi

    download -u "$UBUNTU_12_04_PPA_REPO_SOURCE" -u "$UBUNTU_12_04_PPA_REPO_SOURCE_ASIA" ubuntu_12_04_ppa_repo.tar.gz unzip /var/lib/cobbler/repo_mirror || exit $?
fi

if [[ $SUPPORT_UBUNTU_14_04 == "y" ]]; then
    sudo mkdir -p /var/lib/cobbler/repo_mirror/ubuntu_14_04_ppa_repo
    found_ubuntu_14_04_ppa_repo=0
    for repo in $(cobbler repo list); do
        if [ "$repo" == "ubuntu_14_04_ppa_repo" ]; then
            found_ubuntu_14_04_ppa_repo=1
        fi
    done

    if [ "$found_ubuntu_14_04_ppa_repo" == "0" ]; then
        sudo cobbler repo add --mirror=/var/lib/cobbler/repo_mirror/ubuntu_14_04_ppa_repo --name=ubuntu_14_04_ppa_repo --mirror-locally=Y --arch=x86_64 --apt-dists=ppa --apt-components=main
        if [[ "$?" != "0" ]]; then
            echo "failed to add ubuntu_14_04_ppa_repo"
            exit 1
        else
            echo "ubuntu_14_04_ppa_repo is added"
        fi
    else
        echo "repo ubuntu_14_04_ppa_repo has already existed."
    fi

    download -u "$UBUNTU_14_04_PPA_REPO_SOURCE" -u "$UBUNTU_14_04_PPA_REPO_SOURCE_ASIA" ubuntu_14_04_ppa_repo.tar.gz unzip /var/lib/cobbler/repo_mirror || exit $?
fi

if [[ $SUPPORT_SLES_11SP3 == "y" ]]; then
    sudo mkdir -p /var/lib/cobbler/repo_mirror/sles_11sp3_ppa_repo
    found_sles_11sp3_ppa_repo=0
    for repo in $(cobbler repo list); do
        if [ "$repo" == "sles_11sp3_ppa_repo" ]; then
            found_sles_11sp3_ppa_repo=1
        fi
    done

    if [ "$found_sles_11sp3_ppa_repo" == "0" ]; then
        sudo cobbler repo add --mirror=/var/lib/cobbler/repo_mirror/sles_11sp3_ppa_repo --name=sles_11sp3_ppa_repo --mirror-locally=Y --arch=x86_64
        if [[ "$?" != "0" ]]; then
            echo "failed to add sles_11sp3_ppa_repo"
            exit 1
        else
            echo "sles_11sp3_ppa_repo is added"
        fi
    else
        echo "repo sles_11sp3_ppa_repo has already existed."
    fi

    download -u "$SLES_11SP3_PPA_REPO_SOURCE" -u "$SLES_11SP3_PPA_REPO_SOURCE_ASIA" sles_11sp3_ppa_repo.tar.gz unzip /var/lib/cobbler/repo_mirror || exit $?
fi

if [[ $SUPPORT_UVP_11SP3 == "y" ]]; then
    sudo mkdir -p /var/lib/cobbler/repo_mirror/sles_11sp3_ppa_repo
    found_sles_11sp3_ppa_repo=0
    for repo in $(cobbler repo list); do
        if [ "$repo" == "sles_11sp3_ppa_repo" ]; then
            found_sles_11sp3_ppa_repo=1
        fi
    done

    if [ "$found_sles_11sp3_ppa_repo" == "0" ]; then
        sudo cobbler repo add --mirror=/var/lib/cobbler/repo_mirror/sles_11sp3_ppa_repo --name=sles_11sp3_ppa_repo --mirror-locally=Y --arch=x86_64
        if [[ "$?" != "0" ]]; then
            echo "failed to add sles_11sp3_ppa_repo"
            exit 1
        else
            echo "sles_11sp3_ppa_repo is added"
        fi
    else
        echo "repo sles_11sp3_ppa_repo has already existed."
    fi

    download -u "$SLES_11SP3_PPA_REPO_SOURCE" -u "$SLES_11SP3_PPA_REPO_SOURCE_ASIA" sles_11sp3_ppa_repo.tar.gz unzip /var/lib/cobbler/repo_mirror || exit $?
fi


sudo cobbler reposync
if [[ "$?" != "0" ]]; then
    echo "cobbler reposync failed"
    exit 1
else
    echo "cobbler repos are synced"
fi

# import cobbler distro
sudo mkdir -p /var/lib/cobbler/iso
if [[ $SUPPORT_CENTOS_6_5 == "y" ]]; then
    download -u "$CENTOS_6_5_IMAGE_SOURCE_ASIA" -u "$CENTOS_6_5_IMAGE_SOURCE" CentOS-6.5-x86_64.iso copy /var/lib/cobbler/iso/ || exit $?
    sudo mkdir -p /mnt/CentOS-6.5-x86_64
    if [ $(mount | grep -c "/mnt/CentOS-6.5-x86_64") -eq 0 ]; then
        sudo mount -o loop /var/lib/cobbler/iso/CentOS-6.5-x86_64.iso /mnt/CentOS-6.5-x86_64
        if [[ "$?" != "0" ]]; then
            echo "failed to mount image /mnt/CentOS-6.5-x86_64"
            exit 1
        else
            echo "/mnt/CentOS-6.5-x86_64 is mounted"
        fi
    else
        echo "/mnt/CentOS-6.5-x86_64 has already mounted"
    fi
fi

if [[ $SUPPORT_CENTOS_6_6 == "y" ]]; then
    download -u "$CENTOS_6_6_IMAGE_SOURCE_ASIA" -u "$CENTOS_6_6_IMAGE_SOURCE" CentOS-6.6-x86_64.iso copy /var/lib/cobbler/iso/ || exit $?
    sudo mkdir -p /mnt/CentOS-6.6-x86_64
    if [ $(mount | grep -c "/mnt/CentOS-6.6-x86_64") -eq 0 ]; then
        sudo mount -o loop /var/lib/cobbler/iso/CentOS-6.6-x86_64.iso /mnt/CentOS-6.6-x86_64
        if [[ "$?" != "0" ]]; then
            echo "failed to mount image /mnt/CentOS-6.6-x86_64"
            exit 1
        else
            echo "/mnt/CentOS-6.6-x86_64 is mounted"
        fi
    else
        echo "/mnt/CentOS-6.6-x86_64 has already mounted"
    fi
fi

if [[ $SUPPORT_CENTOS_7_0 == "y" ]]; then
    download -u "$CENTOS_7_0_IMAGE_SOURCE_ASIA" -u "$CENTOS_7_0_IMAGE_SOURCE" CentOS-7.0-x86_64.iso copy /var/lib/cobbler/iso/ || exit $?
    sudo mkdir -p /mnt/CentOS-7.0-x86_64
    if [ $(mount | grep -c "/mnt/CentOS-7.0-x86_64") -eq 0 ]; then
        sudo mount -o loop /var/lib/cobbler/iso/CentOS-7.0-x86_64.iso /mnt/CentOS-7.0-x86_64
        if [[ "$?" != "0" ]]; then
            echo "failed to mount image /mnt/CentOS-7.0-x86_64"
            exit 1
        else
            echo "/mnt/CentOS-7.0-x86_64 is mounted"
        fi
    else
        echo "/mnt/CentOS-7.0-x86_64 has already mounted"
    fi
fi


if [[ $SUPPORT_UBUNTU_12_04 == "y" ]]; then
    download -u "$UBUNTU_12_04_IMAGE_SOURCE_ASIA" -u "$UBUNTU_12_04_IMAGE_SOURCE" Ubuntu-12.04-x86_64.iso copy /var/lib/cobbler/iso/ || exit $?
    sudo mkdir -p /mnt/Ubuntu-12.04-x86_64
    if [ $(mount | grep -c "/mnt/Ubuntu-12.04-x86_64") -eq 0 ]; then
        sudo mount -o loop /var/lib/cobbler/iso/Ubuntu-12.04-x86_64.iso /mnt/Ubuntu-12.04-x86_64
        if [[ "$?" != "0" ]]; then
            echo "failed to mount image /mnt/Ubuntu-12.04-x86_64"
            exit 1
        else
            echo "/mnt/Ubuntu-12.04-x86_64 is mounted"
        fi
    else
        echo "/mnt/Ubuntu-12.04-x86_64 has already mounted"
    fi
fi

if [[ $SUPPORT_UBUNTU_14_04 == "y" ]]; then
    download -u "$UBUNTU_14_04_IMAGE_SOURCE_ASIA" -u "$UBUNTU_14_04_IMAGE_SOURCE" Ubuntu-14.04-x86_64.iso copy /var/lib/cobbler/iso/ || exit $?
    sudo mkdir -p /mnt/Ubuntu-14.04-x86_64
    if [ $(mount | grep -c "/mnt/Ubuntu-14.04-x86_64") -eq 0 ]; then
        sudo mount -o loop /var/lib/cobbler/iso/Ubuntu-14.04-x86_64.iso /mnt/Ubuntu-14.04-x86_64
        if [[ "$?" != "0" ]]; then
            echo "failed to mount image /mnt/Ubuntu-12.04-x86_64"
            exit 1
        else
            echo "/mnt/Ubuntu-14.04-x86_64 is mounted"
        fi
    else
        echo "/mnt/Ubuntu-14.04-x86_64 has already mounted"
    fi
fi

if [[ $SUPPORT_SLES_11SP3 == "y" ]]; then
    download -u "$SLES_11SP3_IMAGE_SOURCE_ASIA" -u "$SLES_11SP3_IMAGE_SOURCE" sles-11sp3-x86_64.iso copy /var/lib/cobbler/iso/ || exit $?
    sudo mkdir -p /mnt/sles-11sp3-x86_64
    if [ $(mount | grep -c "/mnt/sles-11sp3-x86_64") -eq 0 ]; then
        sudo mount -o loop /var/lib/cobbler/iso/sles-11sp3-x86_64.iso /mnt/sles-11sp3-x86_64
        if [[ "$?" != "0" ]]; then
            echo "failed to mount image /mnt/sles-11sp3-x86_64"
            exit 1
        else
            echo "/mnt/sles-11sp3-x86_64 is mounted"
        fi
    else
        echo "/mnt/sles-11sp3-x86_64 has already mounted"
    fi
fi

if [[ $SUPPORT_UVP_11SP3 == "y" ]]; then
    download -u "$SLES_11SP3_IMAGE_SOURCE_ASIA" -u "$SLES_11SP3_IMAGE_SOURCE" sles-11sp3-x86_64.iso copy /var/lib/cobbler/iso/ || exit $?
    sudo mkdir -p /mnt/sles-11sp3-x86_64
    if [ $(mount | grep -c "/mnt/sles-11sp3-x86_64") -eq 0 ]; then
        sudo mount -o loop /var/lib/cobbler/iso/sles-11sp3-x86_64.iso /mnt/sles-11sp3-x86_64
        if [[ "$?" != "0" ]]; then
            echo "failed to mount image /mnt/sles-11sp3-x86_64"
            exit 1
        else
            echo "/mnt/sles-11sp3-x86_64 is mounted"
        fi
    else
        echo "/mnt/sles-11sp3-x86_64 has already mounted"
    fi
    download -u "$UVP_11SP3_IMAGE_SOURCE" -u "$UVP_11SP3_IMAGE_SOURCE_ASIA" uvp-os-11sp3-x86_64.tar.gz copy /var/www/cobbler/aux/uvp-11sp3-x86_64.tar.gz || exit $?
fi


# add distro
if [[ $SUPPORT_CENTOS_6_5 == "y" ]]; then
    found_centos_6_5_distro=0
    distro=$(cobbler distro find --name=CentOS-6.5-x86_64)
    if [ "$distro" == "CentOS-6.5-x86_64" ]; then
        found_centos_6_5_distro=1
    fi

    if [ "$found_centos_6_5_distro" == "0" ]; then
        sudo cobbler import --path=/mnt/CentOS-6.5-x86_64 --name=CentOS-6.5 --arch=x86_64 --kickstart=/var/lib/cobbler/kickstarts/default.ks --breed=redhat
        if [[ "$?" != "0" ]]; then
            echo "failed to import /mnt/CentOS-6.5-x_86_64"
            exit 1
        else
            echo "/mnt/CentOS-6.5-x86_64 is imported" 
        fi
    else
        echo "distro CentOS-6.5-x86_64 has already existed"
        sudo cobbler distro edit --name=CentOS-6.5-x86_64 --arch=x86_64 --breed=redhat
        if [[ "$?" != "0" ]]; then
            echo "failed to edit distro CentOS-6.5-x86_64"
            exit 1
        else
            echo "distro CentOS-6.5-x86_64 is updated"
        fi
    fi

    centos_6_5_found_profile=0
    profile=$(cobbler profile find --name=CentOS-6.5-x86_64)
    if [ "$profile" == "CentOS-6.5-x86_64" ]; then
        centos_6_5_found_profile=1
    fi

    if [ "$centos_6_5_found_profile" == "0" ]; then
        sudo cobbler profile add --name="CentOS-6.5-x86_64" --repo=centos_6_5_ppa_repo --distro=CentOS-6.5-x86_64 --ksmeta="tree=http://$IPADDR/cobbler/ks_mirror/CentOS-6.5-x86_64" --kickstart=/var/lib/cobbler/kickstarts/default.ks
        if [[ "$?" != "0" ]]; then
            echo "failed to add profile CentOS-6.5-x86_64"
            exit 1
        else
            echo "profile CentOS-6.5-x86_64 is added"
        fi
    else
        echo "profile CentOS-6.5-x86_64 has already existed."
        sudo cobbler profile edit --name=CentOS-6.5-x86_64 --repo=centos_6_5_ppa_repo --distro=CentOS-6.5-x86_64 --ksmeta="tree=http://$IPADDR/cobbler/ks_mirror/CentOS-6.5-x86_64" --kickstart=/var/lib/cobbler/kickstarts/default.ks
        if [[ "$?" != "0" ]]; then
            echo "failed to edit profile CentOS-6.5-x86_64"
            exit 1
        else
            echo "profile CentOS-6.5-x86_64 is updated"
        fi
    fi
fi

if [[ $SUPPORT_CENTOS_6_6 == "y" ]]; then
    found_centos_6_6_distro=0
    distro=$(cobbler distro find --name=CentOS-6.6-x86_64)
    if [ "$distro" == "CentOS-6.6-x86_64" ]; then
        found_centos_6_6_distro=1
    fi

    if [ "$found_centos_6_6_distro" == "0" ]; then
        sudo cobbler import --path=/mnt/CentOS-6.6-x86_64 --name=CentOS-6.6 --arch=x86_64 --kickstart=/var/lib/cobbler/kickstarts/default.ks --breed=redhat
        if [[ "$?" != "0" ]]; then
            echo "failed to import /mnt/CentOS-6.6-x_86_64"
            exit 1
        else
            echo "/mnt/CentOS-6.6-x86_64 is imported" 
        fi
    else
        echo "distro CentOS-6.6-x86_64 has already existed"
        sudo cobbler distro edit --name=CentOS-6.6-x86_64 --arch=x86_64 --breed=redhat
        if [[ "$?" != "0" ]]; then
            echo "failed to edit distro CentOS-6.6-x86_64"
            exit 1
        else
            echo "distro CentOS-6.6-x86_64 is updated"
        fi
    fi

    centos_6_6_found_profile=0
    profile=$(cobbler profile find --name=CentOS-6.6-x86_64)
    if [ "$profile" == "CentOS-6.6-x86_64" ]; then
        centos_6_6_found_profile=1
    fi

    if [ "$centos_6_6_found_profile" == "0" ]; then
        sudo cobbler profile add --name="CentOS-6.6-x86_64" --repo=centos_6_6_ppa_repo --distro=CentOS-6.6-x86_64 --ksmeta="tree=http://$IPADDR/cobbler/ks_mirror/CentOS-6.6-x86_64" --kickstart=/var/lib/cobbler/kickstarts/default.ks
        if [[ "$?" != "0" ]]; then
            echo "failed to add profile CentOS-6.6-x86_64"
            exit 1
        else
            echo "profile CentOS-6.6-x86_64 is added"
        fi
    else
        echo "profile CentOS-6.6-x86_64 has already existed."
        sudo cobbler profile edit --name=CentOS-6.6-x86_64 --repo=centos_6_6_ppa_repo --distro=CentOS-6.6-x86_64 --ksmeta="tree=http://$IPADDR/cobbler/ks_mirror/CentOS-6.6-x86_64" --kickstart=/var/lib/cobbler/kickstarts/default.ks
        if [[ "$?" != "0" ]]; then
            echo "failed to edit profile CentOS-6.6-x86_64"
            exit 1
        else
            echo "profile CentOS-6.6-x86_64 is updated"
        fi
    fi
fi

if [[ $SUPPORT_CENTOS_7_0 == "y" ]]; then
    found_centos_7_0_distro=0
    distro=$(cobbler distro find --name=CentOS-7.0-x86_64)
    if [ "$distro" == "CentOS-7.0-x86_64" ]; then
        found_centos_7_0_distro=1
    fi

    if [ "$found_centos_7_0_distro" == "0" ]; then
        sudo cobbler import --path=/mnt/CentOS-7.0-x86_64 --name=CentOS-7.0 --arch=x86_64 --kickstart=/var/lib/cobbler/kickstarts/default.ks --breed=redhat
        if [[ "$?" != "0" ]]; then
            echo "failed to import /mnt/CentOS-7.0-x_86_64"
            exit 1
        else
            echo "/mnt/CentOS-7.0-x86_64 is imported" 
        fi
    else
        echo "distro CentOS-7.0-x86_64 has already existed"
        sudo cobbler distro edit --name=CentOS-7.0-x86_64 --arch=x86_64 --breed=redhat
        if [[ "$?" != "0" ]]; then
            echo "failed to edit distro CentOS-7.0-x86_64"
            exit 1
        else
            echo "distro CentOS-7.0-x86_64 is updated"
        fi
    fi

    centos_7_0_found_profile=0
    for profile in $(cobbler profile list); do
        if [ "$profile" == "CentOS-7.0-x86_64" ]; then
            centos_7_0_found_profile=1
        fi
    done

    if [ "$centos_7_0_found_profile" == "0" ]; then
        sudo cobbler profile add --name="CentOS-7.0-x86_64" --repo=centos_7_0_ppa_repo --distro=CentOS-7.0-x86_64 --ksmeta="tree=http://$IPADDR/cobbler/ks_mirror/CentOS-7.0-x86_64" --kickstart=/var/lib/cobbler/kickstarts/default.ks
        if [[ "$?" != "0" ]]; then
            echo "failed to add profile CentOS-7.0-x86_64"
            exit 1
        else
            echo "profile CentOS-7.0-x86_64 is added"
        fi
    else
        echo "profile CentOS-7.0-x86_64 has already existed."
        sudo cobbler profile edit --name=CentOS-7.0-x86_64 --repo=centos_7_0_ppa_repo --distro=CentOS-7.0-x86_64 --ksmeta="tree=http://$IPADDR/cobbler/ks_mirror/CentOS-7.0-x86_64" --kickstart=/var/lib/cobbler/kickstarts/default.ks
        if [[ "$?" != "0" ]]; then
            echo "failed to edit profile CentOS-7.0-x86_64"
            exit 1
        else
            echo "profile CentOS-7.0-x86_64 is updated"
        fi
    fi
fi

if [[ $SUPPORT_UBUNTU_12_04 == "y" ]]; then
    found_ubuntu_12_04_distro=0
    distro=$(cobbler distro find --name=Ubuntu-12.04-x86_64)
    if [ "$distro" == "Ubuntu-12.04-x86_64" ]; then
        found_ubuntu_12_04_distro=1
    fi

    if [ "$found_ubuntu_12_04_distro" == "0" ]; then
        sudo cobbler import --path=/mnt/Ubuntu-12.04-x86_64 --name=Ubuntu-12.04 --arch=x86_64 --kickstart=/var/lib/cobbler/kickstarts/default.seed --breed=ubuntu
        if [[ "$?" != "0" ]]; then
            echo "failed to import /mnt/Ubuntu-12.04-x86_64"
            exit 1
        else
            echo "/mnt/Ubuntu-12.04-x86_64 is imported" 
        fi
    else
        echo "distro Ubuntu-12.04-x86_64 has already existed"
        sudo cobbler distro edit --name=Ubuntu-12.04-x86_64 --arch=x86_64 --breed=ubuntu
        if [[ "$?" != "0" ]]; then
            echo "failed to edit distro Ubuntu-12.04-x86_64"
            exit 1
        else
            echo "distro Ubuntu-12.04-x86_64 is updated"
        fi
    fi

    ubuntu_12_04_found_profile=0
    profile=$(cobbler profile find --name=Ubuntu-12.04-x86_64)
    if [ "$profile" == "Ubuntu-12.04-x86_64" ]; then
        ubuntu_12_04_found_profile=1
    fi

    if [ "$ubuntu_12_04_found_profile" == "0" ]; then
        sudo cobbler profile add --name=Ubuntu-12.04-x86_64 --repo=ubuntu_12_04_ppa_repo --distro=Ubuntu-12.04-x86_64 --ksmeta="tree=http://$IPADDR/cobbler/ks_mirror/Ubuntu-12.04-x86_64" --kickstart=/var/lib/cobbler/kickstarts/default.seed --kopts="netcfg/choose_interface=auto"
        if [[ "$?" != "0" ]]; then
            echo "failed to add profile Ubuntu-12.04-x86_64"
            exit 1
        else
            echo "profile Ubuntu-12.04-x86_64 is added"
        fi
    else
        echo "profile Ubuntu-12.04-x86_64 has already existed."
        sudo cobbler profile edit --name=Ubuntu-12.04-x86_64 --repo=ubuntu_12_04_ppa_repo --distro=Ubuntu-12.04-x86_64 --ksmeta="tree=http://$IPADDR/cobbler/ks_mirror/Ubuntu-12.04-x86_64" --kickstart=/var/lib/cobbler/kickstarts/default.seed --kopts="netcfg/choose_interface=auto"
        if [[ "$?" != "0" ]]; then
            echo "failed to edit profile Ubuntu-12.04-x86_64"
            exit 1
        else
            echo "profile Ubuntu-12.04-x86_64 is updated"
        fi
    fi
    remove_repo=$(cobbler repo find --name=Ubuntu-12.04-x86_64)
    if [ "$remove_repo" == "Ubuntu-12.04-x86_64" ]; then
        sudo cobbler repo remove --name=Ubuntu-12.04-x86_64
    fi
fi

if [[ $SUPPORT_UBUNTU_14_04 == "y" ]]; then
    found_ubuntu_14_04_distro=0
    distro=$(cobbler distro find --name=Ubuntu-14.04-x86_64)
    if [ "$distro" == "Ubuntu-14.04-x86_64" ]; then
        found_ubuntu_14_04_distro=1
    fi

    if [ "$found_ubuntu_14_04_distro" == "0" ]; then
        sudo cobbler import --path=/mnt/Ubuntu-14.04-x86_64 --name=Ubuntu-14.04 --arch=x86_64 --kickstart=/var/lib/cobbler/kickstarts/default.seed --breed=ubuntu
        if [[ "$?" != "0" ]]; then
            echo "failed to import /mnt/Ubuntu-14.04-x86_64"
            exit 1
        else
            echo "/mnt/Ubuntu-14.04-x86_64 is imported" 
        fi
    else
        echo "distro Ubuntu-14.04-x86_64 has already existed"
        sudo cobbler distro edit --name=Ubuntu-14.04-x86_64 --arch=x86_64 --breed=ubuntu
        if [[ "$?" != "0" ]]; then
            echo "failed to edit distro Ubuntu-14.04-x86_64"
            exit 1
        else
            echo "distro Ubuntu-14.04-x86_64 is updated"
        fi
    fi

    ubuntu_14_04_found_profile=0
    profile=$(cobbler profile find --name=Ubuntu-14.04-x86_64)
    if [ "$profile" == "Ubuntu-14.04-x86_64" ]; then
        ubuntu_14_04_found_profile=1
    fi

    if [ "$ubuntu_14_04_found_profile" == "0" ]; then
        sudo cobbler profile add --name=Ubuntu-14.04-x86_64 --repo=ubuntu_14_04_ppa_repo --distro=Ubuntu-14.04-x86_64 --ksmeta="tree=http://$IPADDR/cobbler/ks_mirror/Ubuntu-14.04-x86_64" --kickstart=/var/lib/cobbler/kickstarts/default.seed --kopts="netcfg/choose_interface=auto"
        if [[ "$?" != "0" ]]; then
            echo "failed to add profile Ubuntu-14.04-x86_64"
            exit 1
        else
            echo "profile Ubuntu-14.04-x86_64 is added"
        fi
    else
        echo "profile Ubuntu-14.04-x86_64 has already existed."
        sudo cobbler profile edit --name=Ubuntu-14.04-x86_64 --repo=ubuntu_14_04_ppa_repo --distro=Ubuntu-14.04-x86_64 --ksmeta="tree=http://$IPADDR/cobbler/ks_mirror/Ubuntu-14.04-x86_64" --kickstart=/var/lib/cobbler/kickstarts/default.seed --kopts="netcfg/choose_interface=auto"
        if [[ "$?" != "0" ]]; then
            echo "failed to edit profile Ubuntu-14.04-x86_64"
            exit 1
        else
            echo "profile Ubuntu-14.04-x86_64 is updated"
        fi
    fi
    remove_repo=$(cobbler repo find --name=Ubuntu-14.04-x86_64)
    if [ "$remove_repo" == "Ubuntu-14.04-x86_64" ]; then
        sudo cobbler repo remove --name=Ubuntu-14.04-x86_64
    fi
fi

if [[ $SUPPORT_SLES_11SP3 == "y" ]]; then
    found_sles_11sp3_distro=0
    distro=$(cobbler distro find --name=sles-11sp3-x86_64)
    if [ "$distro" == "sles-11sp3-x86_64" ]; then
        found_sles_11sp3_distro=1
    fi

    if [ "$found_sles_11sp3_distro" == "0" ]; then
        sudo cobbler import --path=/mnt/sles-11sp3-x86_64 --name=sles-11sp3 --arch=x86_64 --kickstart=/var/lib/cobbler/kickstarts/default.xml --breed=suse --os-version=sles11sp3
        if [[ "$?" != "0" ]]; then
            echo "failed to import /mnt/sles-11sp3-x86_64"
            exit 1
        else
            echo "/mnt/sles-11sp3-x86_64 is imported" 
        fi
    else
        echo "distro sles-11sp3-x86_64 has already existed"
        sudo cobbler distro edit --name=sles-11sp3-x86_64 --arch=x86_64 --breed=suse --os-version=sles11sp3
        if [[ "$?" != "0" ]]; then
            echo "failed to edit distro sles-11sp3-x86_64"
            exit 1
        else
            echo "distro sles-11sp3-x86_64 is updated"
        fi
    fi

    sles_11sp3_found_profile=0
    profile=$(cobbler profile find --name=sles-11sp3-x86_64)
    if [ "$profile" == "sles-11sp3-x86_64" ]; then
        sles_11sp3_found_profile=1
    fi

    if [ "$sles_11sp3_found_profile" == "0" ]; then
        sudo cobbler profile add --name=sles-11sp3-x86_64 --repo=sles_11sp3_ppa_repo --distro=sles-11sp3-x86_64 --kickstart=/var/lib/cobbler/kickstarts/default.xml --kopts="textmode=1 install=http://$IPADDR/cobbler/ks_mirror/sles-11sp3-x86_64"
        if [[ "$?" != "0" ]]; then
            echo "failed to add profile sles-11sp3-x86_64"
            exit 1
        else
            echo "profile sles-11sp3-x86_64 is added"
        fi
    else
        echo "profile sles-11sp3-x86_64 has already existed."
        sudo cobbler profile edit --name=sles-11sp3-x86_64 --repo=sles_11sp3_ppa_repo --distro=sles-11sp3-x86_64 --kickstart=/var/lib/cobbler/kickstarts/default.xml --kopts="textmode=1 install=http://$IPADDR/cobbler/ks_mirror/sles-11sp3-x86_64"
        if [[ "$?" != "0" ]]; then
            echo "failed to edit profile sles-11sp3-x86_64"
            exit 1
        else
            echo "profile sles-11sp3-x86_64 is updated"
        fi
    fi
fi

if [[ $SUPPORT_UVP_11SP3 == "y" ]]; then
    found_uvp_11sp3_distro=0
    distro=$(cobbler distro find --name=uvp-11sp3-x86_64)
    if [ "$distro" == "uvp-11sp3-x86_64" ]; then
        found_uvp_11sp3_distro=1
    fi

    if [ "$found_uvp_11sp3_distro" == "0" ]; then
        sudo cobbler import --path=/mnt/sles-11sp3-x86_64 --name=uvp-11sp3 --arch=x86_64 --kickstart=/var/lib/cobbler/kickstarts/default.xml --breed=suse --os-version=sles11sp3
        if [[ "$?" != "0" ]]; then
            echo "failed to import /mnt/sles-11sp3-x86_64"
            exit 1
        else
            echo "/mnt/sles-11sp3-x86_64 is imported" 
        fi
    else
        echo "distro uvp-11sp3-x86_64 has already existed"
        sudo cobbler distro edit --name=uvp-11sp3-x86_64 --arch=x86_64 --breed=suse --os-version=sles11sp3
        if [[ "$?" != "0" ]]; then
            echo "failed to edit distro uvp-11sp3-x86_64"
            exit 1
        else
            echo "distro uvp-11sp3-x86_64 is updated"
        fi
    fi

    uvp_11sp3_found_profile=0
    profile=$(cobbler profile find --name=uvp-11sp3-x86_64)
    if [ "$profile" == "uvp-11sp3-x86_64" ]; then
        uvp_11sp3_found_profile=1
    fi

    if [ "$uvp_11sp3_found_profile" == "0" ]; then
        sudo cobbler profile add --name=uvp-11sp3-x86_64 --repo=sles_11sp3_ppa_repo --distro=uvp-11sp3-x86_64 --kickstart=/var/lib/cobbler/kickstarts/default.xml --kopts="textmode=1 install=http://$IPADDR/cobbler/ks_mirror/sles-11sp3-x86_64" --kopts-post="noexec=on nohz=off console=tty0 console=ttyS0,115200 hugepagesz=2M hpet=enable selinux=0 iommu=pt default_hugepagesz=2M intel_iommu=on pci=realloc crashkernel=192M@48M highres=on nmi_watchdog=1" --ksmeta="image_kernel_version=3.0.93-0.8 image_url=http://@@http_server@@/cblr/aux/uvp-11sp3-x86_64.tar.gz"
        if [[ "$?" != "0" ]]; then
            echo "failed to add profile uvp-11sp3-x86_64"
            exit 1
        else
            echo "profile uvp-11sp3-x86_64 is added"
        fi
    else
        echo "profile sles-11sp3-x86_64 has already existed."
        sudo cobbler profile edit --name=uvp-11sp3-x86_64 --repo=sles_11sp3_ppa_repo --distro=sles-11sp3-x86_64 --kickstart=/var/lib/cobbler/kickstarts/default.xml --kopts="textmode=1 install=http://$IPADDR/cobbler/ks_mirror/sles-11sp3-x86_64" --kopts-post="noexec=on nohz=off console=tty0 console=ttyS0,115200 hugepagesz=2M hpet=enable selinux=0 iommu=pt default_hugepagesz=2M intel_iommu=on pci=realloc crashkernel=192M@48M highres=on nmi_watchdog=1" --ksmeta="image_kernel_version=3.0.93-0.8 image_url=http://@@http_server@@/cblr/aux/uvp-11sp3-x86_64.tar.gz"
        if [[ "$?" != "0" ]]; then
            echo "failed to edit profile uvp-11sp3-x86_64"
            exit 1
        else
            echo "profile uvp-11sp3-x86_64 is updated"
        fi
    fi
fi

sudo cobbler reposync
if [[ "$?" != "0" ]]; then
    echo "cobbler reposync failed"
    exit 1
else
    echo "cobbler repos are synced"
fi

sudo cobbler sync
if [[ "$?" != "0" ]]; then
    echo "cobbler sync failed"
    exit 1
else
    echo "cobbler are synced"
fi

echo "Checking cobbler is OK"
sudo cobbler check
if [[ "$?" != "0" ]]; then
    echo "cobbler check failed"
    exit 1
else
    echo "cobbler check passed"
fi

echo "Cobbler configuration complete!"
