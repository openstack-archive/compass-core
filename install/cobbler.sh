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
sudo rm -rf /var/lib/cobbler/snippets/*
sudo cp -rf $ADAPTERS_HOME/cobbler/snippets/* /var/lib/cobbler/snippets/
sudo cp -rf $ADAPTERS_HOME/cobbler/scripts/* /var/lib/cobbler/scripts/
sudo cp -rf $ADAPTERS_HOME/cobbler/triggers/* /var/lib/cobbler/triggers/
sudo chmod 777 /var/lib/cobbler/snippets
sudo chmod 777 /var/lib/cobbler/scripts
sudo chmod -R 666 /var/lib/cobbler/snippets/*
sudo chmod -R 666 /var/lib/cobbler/scripts/*
sudo chmod -R 755 /var/lib/cobbler/triggers
sudo rm -f /var/lib/cobbler/kickstarts/default.ks
sudo rm -f /var/lib/cobbler/kickstarts/default.seed
sudo cp -rf $ADAPTERS_HOME/cobbler/kickstarts/default.ks /var/lib/cobbler/kickstarts/
sudo cp -rf $ADAPTERS_HOME/cobbler/kickstarts/default.seed /var/lib/cobbler/kickstarts/
sudo chmod 666 /var/lib/cobbler/kickstarts/default.ks
sudo chmod 666 /var/lib/cobbler/kickstarts/default.seed
sudo mkdir -p /var/www/cblr_ks
sudo chmod 755 /var/www/cblr_ks
sudo cp -rf $ADAPTERS_HOME/cobbler/conf/cobbler.conf /etc/httpd/conf.d/
chmod 644 /etc/httpd/conf.d/cobbler.conf

sudo cp -rn /etc/xinetd.d /root/backup/
sudo sed -i 's/disable\([ \t]\+\)=\([ \t]\+\)yes/disable\1=\2no/g' /etc/xinetd.d/rsync
sudo sed -i 's/^@dists=/# @dists=/g' /etc/debmirror.conf
sudo sed -i 's/^@arches=/# @arches=/g' /etc/debmirror.conf

echo "disable iptables"
sudo service iptables stop
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
mkdir -p /var/log/cobbler
mkdir -p /var/log/cobbler/tasks
mkdir -p /var/log/cobbler/anamon
chmod -R 777 /var/log/cobbler


sudo service httpd restart
sudo service cobblerd restart
sudo cobbler get-loaders
sudo cobbler sync
sudo service xinetd restart

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

# create centos repo
sudo rm -rf /var/lib/cobbler/repo_mirror/centos_ppa_repo
sudo mkdir -p /var/lib/cobbler/repo_mirror/centos_ppa_repo
found_centos_ppa_repo=0
for repo in $(cobbler repo list); do
    if [ "$repo" == "centos_ppa_repo" ]; then
        found_centos_ppa_repo=1
    fi
done

if [ "$found_centos_ppa_repo" == "0" ]; then
    sudo cobbler repo add --mirror=/var/lib/cobbler/repo_mirror/centos_ppa_repo --name=centos_ppa_repo --mirror-locally=Y --arch=${CENTOS_IMAGE_ARCH}
    if [[ "$?" != "0" ]]; then
        echo "failed to add centos_ppa_repo"
        exit 1
    else
        echo "centos_ppa_repo is added"
    fi
else
    echo "repo centos_ppa_repo has already existed."
fi

# download packages
cd /var/lib/cobbler/repo_mirror/centos_ppa_repo/
fastesturl http://mirrors.hustunique.com http://mirror.centos.org
if [[ "$?" != "0" ]]; then
    echo "failed to determine the fastest url for downloading centos ppa packages"
    exit 1
fi
read -r PPA_REPO_URL</tmp/url
centos_ppa_repo_packages="
ntp-4.2.6p5-1.${CENTOS_IMAGE_TYPE_OTHER}${CENTOS_IMAGE_VERSION_MAJOR}.${CENTOS_IMAGE_TYPE,,}.${CENTOS_IMAGE_ARCH}.rpm
openssh-clients-5.3p1-94.${CENTOS_IMAGE_TYPE_OTHER}${CENTOS_IMAGE_VERSION_MAJOR}.${CENTOS_IMAGE_ARCH}.rpm
openssh-5.3p1-94.${CENTOS_IMAGE_TYPE_OTHER}${CENTOS_IMAGE_VERSION_MAJOR}.${CENTOS_IMAGE_ARCH}.rpm
iproute-2.6.32-31.${CENTOS_IMAGE_TYPE_OTHER}${CENTOS_IMAGE_VERSION_MAJOR}.${CENTOS_IMAGE_ARCH}.rpm
wget-1.12-1.8.${CENTOS_IMAGE_TYPE_OTHER}${CENTOS_IMAGE_VERSION_MAJOR}.${CENTOS_IMAGE_ARCH}.rpm
ntpdate-4.2.6p5-1.${CENTOS_IMAGE_TYPE_OTHER}${CENTOS_IMAGE_VERSION_MAJOR}.${CENTOS_IMAGE_TYPE,,}.${CENTOS_IMAGE_ARCH}.rpm
yum-plugin-priorities-1.1.30-14.${CENTOS_IMAGE_TYPE_OTHER}${CENTOS_IMAGE_VERSION_MAJOR}.noarch.rpm"
for f in $centos_ppa_repo_packages; do
    download $PPA_REPO_URL/${CENTOS_IMAGE_TYPE,,}/${CENTOS_IMAGE_VERSION}/os/${CENTOS_IMAGE_ARCH}/Packages/$f $f copy /var/lib/cobbler/repo_mirror/centos_ppa_repo/ || exit $?
done

centos_ppa_repo_rsyslog_packages="
json-c-0.10-2.${CENTOS_IMAGE_TYPE_OTHER}${CENTOS_IMAGE_VERSION_MAJOR}.${CENTOS_IMAGE_ARCH}.rpm
libestr-0.1.9-1.${CENTOS_IMAGE_TYPE_OTHER}${CENTOS_IMAGE_VERSION_MAJOR}.${CENTOS_IMAGE_ARCH}.rpm
libgt-0.3.11-1.${CENTOS_IMAGE_TYPE_OTHER}${CENTOS_IMAGE_VERSION_MAJOR}.${CENTOS_IMAGE_ARCH}.rpm
liblogging-1.0.4-1.${CENTOS_IMAGE_TYPE_OTHER}${CENTOS_IMAGE_VERSION_MAJOR}.${CENTOS_IMAGE_ARCH}.rpm
rsyslog-7.6.3-1.${CENTOS_IMAGE_TYPE_OTHER}${CENTOS_IMAGE_VERSION_MAJOR}.${CENTOS_IMAGE_ARCH}.rpm"
for f in $centos_ppa_repo_rsyslog_packages; do
    download http://rpms.adiscon.com/v7-stable/epel-${CENTOS_IMAGE_VERSION_MAJOR}/${CENTOS_IMAGE_ARCH}/RPMS/$f $f copy /var/lib/cobbler/repo_mirror/centos_ppa_repo/ || exit $?
done

# download chef client for centos ppa repo
download $CENTOS_CHEF_CLIENT `basename $CENTOS_CHEF_CLIENT` copy /var/lib/cobbler/repo_mirror/centos_ppa_repo/

# create centos repo
cd ..
sudo createrepo centos_ppa_repo
if [[ "$?" != "0" ]]; then
    echo "failed to createrepo centos_ppa_repo"
    exit 1
else
    echo "centos_ppa_repo is created"
fi

# create ubuntu repo
sudo rm -rf /var/lib/cobbler/repo_mirror/ubuntu_ppa_repo
sudo mkdir -p /var/lib/cobbler/repo_mirror/ubuntu_ppa_repo
found_ubuntu_ppa_repo=0
for repo in $(cobbler repo list); do
    if [ "$repo" == "ubuntu_ppa_repo" ]; then
        found_ubuntu_ppa_repo=1
    fi
done

if [ "$found_ubuntu_ppa_repo" == "0" ]; then
    sudo cobbler repo add --mirror=/var/lib/cobbler/repo_mirror/ubuntu_ppa_repo --name=ubuntu_ppa_repo --mirror-locally=Y --arch=${UBUNTU_IMAGE_ARCH} --apt-dists=ppa --apt-components=main
    if [[ "$?" != "0" ]]; then
        echo "failed to add ubuntu_ppa_repo"
        exit 1
    else
        echo "ubuntu_ppa_repo is added"
    fi
else
    echo "repo ubuntu_ppa_repo has already existed."
fi

cd /var/lib/cobbler/repo_mirror/ubuntu_ppa_repo/
if [ ! -e /var/lib/cobbler/repo_mirror/ubuntu_ppa_repo/conf/distributions ]; then
    echo "create ubuntu ppa repo distribution"
    mkdir -p /var/lib/cobbler/repo_mirror/ubuntu_ppa_repo/conf
    cat << EOF > /var/lib/cobbler/repo_mirror/ubuntu_ppa_repo/conf/distributions
Origin: ppa
Label: ppa_repo
Suite: stable
Codename: ppa
Version: 0.1
Architectures: i386 amd64 source
Components: main
Description: ppa repo
EOF
    chmod 644 /var/lib/cobbler/repo_mirror/ubuntu_ppa_repo/conf/distributions
else
    echo "ubuntu ppa repo distribution file exists."
fi

# download chef client for ubuntu ppa repo
download $UBUNTU_CHEF_CLIENT `basename $UBUNTU_CHEF_CLIENT` copy /var/lib/cobbler/repo_mirror/ubuntu_ppa_repo/ || exit $?

cd ..
find ubuntu_ppa_repo -name \*.deb -exec reprepro -Vb ubuntu_ppa_repo includedeb ppa {} \;
if [ "$?" != "0" ]; then
    echo "failed to create ubuntu_ppa_repo"
    exit 1
else
    echo  "ubuntu_ppa_repo is created"
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
fastesturl $CENTOS_IMAGE_SOURCE_ASIA $CENTOS_SOURCE_MIRROR
if [[ "$?" != "0" ]]; then
    echo "failed to determine the fastest source for centos iso"
    exit 1
fi
read -r CENTOS_SOURCE</tmp/url
download "$CENTOS_SOURCE" ${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH}.iso copy /var/lib/cobbler/iso/ || exit $?
sudo mkdir -p /mnt/${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH}
if [ $(mount | grep -c "/mnt/${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH} ") -eq 0 ]; then
    sudo mount -o loop /var/lib/cobbler/iso/${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH}.iso /mnt/${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH}
    if [[ "$?" != "0" ]]; then
        echo "failed to mount image /mnt/${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH}"
        exit 1
    else
        echo "/mnt/${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH} is mounted"
    fi
else
    echo "/mnt/${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH} has already mounted"
fi

fastesturl $UBUNTU_IMAGE_SOURCE_ASIA $UBUNTU_IMAGE_SOURCE
if [[ "$?" != "0" ]]; then
    echo "failed to determine the fastest source for ubuntu iso"
    exit 1
fi
read -r UBUNTU_SOURCE</tmp/url
download "$UBUNTU_SOURCE" ${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH}.iso copy /var/lib/cobbler/iso/ || exit $?
sudo mkdir -p /mnt/${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH}
if [ $(mount | grep -c "/mnt/${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH} ") -eq 0 ]; then
    sudo mount -o loop /var/lib/cobbler/iso/${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH}.iso /mnt/${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH}
    if [[ "$?" != "0" ]]; then
        echo "failed to mount image /mnt/${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH}"
        exit 1
    else
        echo "/mnt/${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH} is mounted"
    fi
else
    echo "/mnt/${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH} has already mounted"
fi

# add distro
found_centos_distro=0
for distro in $(cobbler distro list); do
    if [ "$distro" == "${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH}" ]; then
        found_centos_distro=1
    fi
done

if [ "$found_centos_distro" == "0" ]; then
    sudo cobbler import --path=/mnt/${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH} --name=${CENTOS_IMAGE_NAME} --arch=${CENTOS_IMAGE_ARCH} --kickstart=/var/lib/cobbler/kickstarts/default.ks --breed=redhat
    if [[ "$?" != "0" ]]; then
        echo "failed to import /mnt/${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH}"
        exit 1
    else
        echo "/mnt/${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH} is imported" 
    fi
else
    echo "distro ${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH} has already existed"
    sudo cobbler distro edit --name=${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH} --arch=${CENTOS_IMAGE_ARCH} --breed=redhat
    if [[ "$?" != "0" ]]; then
        echo "failed to edit distro ${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH}"
        exit 1
    else
        echo "distro ${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH} is updated"
    fi
fi

found_ubuntu_distro=0
for distro in $(cobbler distro list); do
    if [ "$distro" == "${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH}" ]; then
        found_ubuntu_distro=1
    fi
done

if [ "$found_ubuntu_distro" == "0" ]; then
    sudo cobbler import --path=/mnt/${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH} --name=${UBUNTU_IMAGE_NAME} --arch=${UBUNTU_IMAGE_ARCH} --kickstart=/var/lib/cobbler/kickstarts/default.seed --breed=ubuntu
    if [[ "$?" != "0" ]]; then
        echo "failed to import /mnt/${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH}"
        exit 1
    else
        echo "/mnt/${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH} is imported" 
    fi
else
    echo "distro ${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH} has already existed"
    sudo cobbler distro edit --name=${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH} --arch=${UBUNTU_IMAGE_ARCH} --breed=ubuntu
    if [[ "$?" != "0" ]]; then
        echo "failed to edit distro ${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH}"
        exit 1
    else
        echo "distro ${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH} is updated"
    fi
fi

# add profile
centos_found_profile=0
for profile in $(cobbler profile list); do
    if [ "$profile" == "${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH}" ]; then
        centos_found_profile=1
    fi
done

if [ "$centos_found_profile" == "0" ]; then
    sudo cobbler profile add --name="${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH}" --repo=centos_ppa_repo --distro="${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH}" --ksmeta="tree=http://$IPADDR/cobbler/ks_mirror/${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH}" --kickstart=/var/lib/cobbler/kickstarts/default.ks
    if [[ "$?" != "0" ]]; then
        echo "failed to add profile ${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH}"
        exit 1
    else
        echo "profile ${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH} is added"
    fi
else
    echo "profile ${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH} has already existed."
    sudo cobbler profile edit --name="${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH}" --repo=centos_ppa_repo --distro="${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH}" --ksmeta="tree=http://$IPADDR/cobbler/ks_mirror/${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH}" --kickstart=/var/lib/cobbler/kickstarts/default.ks
    if [[ "$?" != "0" ]]; then
        echo "failed to edit profile ${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH}"
        exit 1
    else
        echo "profile ${CENTOS_IMAGE_NAME}-${CENTOS_IMAGE_ARCH} is updated"
    fi
fi

ubuntu_found_profile=0
for profile in $(cobbler profile list); do
    if [ "$profile" == "${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH}" ]; then
        ubuntu_found_profile=1
    fi
done

if [ "$ubuntu_found_profile" == "0" ]; then
    sudo cobbler profile add --name="${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH}" --repo=ubuntu_ppa_repo --distro="${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH}" --ksmeta="tree=http://$IPADDR/cobbler/ks_mirror/${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH}" --kickstart=/var/lib/cobbler/kickstarts/default.seed --kopts="netcfg/choose_interface=auto"
    if [[ "$?" != "0" ]]; then
        echo "failed to add profile ${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH}"
        exit 1
    else
        echo "profile ${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH} is added"
    fi
else
    echo "profile ${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH} has already existed."
    sudo cobbler profile edit --name="${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH}" --repo=ubuntu_ppa_repo --distro="${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH}" --ksmeta="tree=http://$IPADDR/cobbler/ks_mirror/${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH}" --kickstart=/var/lib/cobbler/kickstarts/default.seed --kopts="netcfg/choose_interface=auto"
    if [[ "$?" != "0" ]]; then
        echo "failed to edit profile ${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH}"
        exit 1
    else
        echo "profile ${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH} is updated"
    fi
fi

#clean ubuntu repo
sudo cobbler repo remove --name=${UBUNTU_IMAGE_NAME}-${UBUNTU_IMAGE_ARCH}

sudo cobbler reposync
if [[ "$?" != "0" ]]; then
    echo "cobbler reposync failed"
    exit 1
else
    echo "cobbler repos are synced"
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
