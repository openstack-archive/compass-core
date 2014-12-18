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

PPA_REPO_URL=`fastesturl http://mirror.centos.org http://mirrors.hustunique.com`
# create centos repo
if [[ $SUPPORT_CENTOS_6_5 == "y" ]]; then
    sudo rm -rf /var/lib/cobbler/repo_mirror/centos_6_5_ppa_repo
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
    cd /var/lib/cobbler/repo_mirror/centos_6_5_ppa_repo/
    centos_6_5_ppa_repo_packages="
ntp-4.2.6p5-1.el6.centos.x86_64.rpm
openssh-clients-5.3p1-94.el6.x86_64.rpm
iproute-2.6.32-31.el6.x86_64.rpm
wget-1.12-1.8.el6.x86_64.rpm
ntpdate-4.2.6p5-1.el6.centos.x86_64.rpm
yum-plugin-priorities-1.1.30-14.el6.noarch.rpm
parted-2.1-21.el6.x86_64.rpm"
    for f in $centos_6_5_ppa_repo_packages; do
        download -u $PPA_REPO_URL/centos/6.5/os/x86_64/Packages/$f $f copy /var/lib/cobbler/repo_mirror/centos_6_5_ppa_repo/ || exit $?
    done

    centos_6_5_ppa_repo_rsyslog_packages="
json-c-0.10-2.el6.x86_64.rpm
libestr-0.1.9-1.el6.x86_64.rpm
libgt-0.3.11-1.el6.x86_64.rpm
liblogging-1.0.4-1.el6.x86_64.rpm
rsyslog-7.6.3-1.el6.x86_64.rpm"

    for f in $centos_6_5_ppa_repo_rsyslog_packages; do
        download -u http://rpms.adiscon.com/v7-stable/epel-6/x86_64/RPMS/$f $f copy /var/lib/cobbler/repo_mirror/centos_6_5_ppa_repo/ || exit $?
    done

    # download chef client for centos ppa repo
    download -u $CENTOS_6_5_CHEF_CLIENT -u $CENTOS_6_5_CHEF_CLIENT_HUAWEI `basename $CENTOS_6_5_CHEF_CLIENT` copy /var/lib/cobbler/repo_mirror/centos_6_5_ppa_repo/

    # create centos repo
    cd ..
    sudo createrepo centos_6_5_ppa_repo
    if [[ "$?" != "0" ]]; then
        echo "failed to createrepo centos_6_5_ppa_repo"
        exit 1
    else
        echo "centos_6_5_ppa_repo is created"
    fi
fi

if [[ $SUPPORT_CENTOS_6_6 == "y" ]]; then
    sudo rm -rf /var/lib/cobbler/repo_mirror/centos_6_6_ppa_repo
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
    cd /var/lib/cobbler/repo_mirror/centos_6_6_ppa_repo/
    centos_6_6_ppa_repo_packages="
ntp-4.2.6p5-1.el6.centos.x86_64.rpm
openssh-5.3p1-104.el6.x86_64.rpm
openssh-clients-5.3p1-104.el6.x86_64.rpm
iproute-2.6.32-32.el6_5.x86_64.rpm
wget-1.12-5.el6.x86_64.rpm
ntpdate-4.2.6p5-1.el6.centos.x86_64.rpm
yum-plugin-priorities-1.1.30-30.el6.noarch.rpm
parted-2.1-25.el6.x86_64.rpm"
    for f in $centos_6_6_ppa_repo_packages; do
        download -u $PPA_REPO_URL/centos/6.6/os/x86_64/Packages/$f $f copy /var/lib/cobbler/repo_mirror/centos_6_6_ppa_repo/ || exit $?
    done

    centos_6_6_ppa_repo_rsyslog_packages="
json-c-0.10-2.el6.x86_64.rpm
libestr-0.1.9-1.el6.x86_64.rpm
libgt-0.3.11-1.el6.x86_64.rpm
liblogging-1.0.4-1.el6.x86_64.rpm
rsyslog-7.6.3-1.el6.x86_64.rpm"

    for f in $centos_6_6_ppa_repo_rsyslog_packages; do
        download -u http://rpms.adiscon.com/v7-stable/epel-6/x86_64/RPMS/$f $f copy /var/lib/cobbler/repo_mirror/centos_6_6_ppa_repo/ || exit $?
    done

    download -u $CENTOS_6_6_CHEF_CLIENT -u $CENTOS_6_6_CHEF_CLIENT_HUAWEI $CENTOS_6_6_CHEF_CLIENT_SOURCE `basename $CENTOS_6_6_CHEF_CLIENT` copy /var/lib/cobbler/repo_mirror/centos_6_6_ppa_repo/

    cd ..
    sudo createrepo centos_6_6_ppa_repo
    if [[ "$?" != "0" ]]; then
        echo "failed to createrepo centos_6_6_ppa_repo"
        exit 1
    else
        echo "centos_6_6_ppa_repo is created"
    fi
fi

if [[ $SUPPORT_CENTOS_7_0 == "y" ]]; then
    sudo rm -rf /var/lib/cobbler/repo_mirror/centos_7_0_ppa_repo
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
    cd /var/lib/cobbler/repo_mirror/centos_7_0_ppa_repo/
    centos_7_0_ppa_repo_packages="
ntp-4.2.6p5-18.el7.centos.x86_64.rpm
openssh-6.4p1-8.el7.x86_64.rpm
openssh-clients-6.4p1-8.el7.x86_64.rpm
iproute-3.10.0-13.el7.x86_64.rpm
wget-1.14-10.el7.x86_64.rpm
ntpdate-4.2.6p5-18.el7.centos.x86_64.rpm
yum-plugin-priorities-1.1.31-24.el7.noarch.rpm
json-c-0.11-3.el7.x86_64.rpm
parted-3.1-17.el7.x86_64.rpm"
    for f in $centos_7_0_ppa_repo_packages; do
        download -u $PPA_REPO_URL/centos/7.0.1406/os/x86_64/Packages/$f $f copy /var/lib/cobbler/repo_mirror/centos_7_0_ppa_repo/ || exit $?
    done

    centos_7_0_ppa_repo_rsyslog_packages="
libestr-0.1.9-1.el7.x86_64.rpm
libgt-0.3.11-1.el7.x86_64.rpm
liblogging-1.0.4-1.el7.x86_64.rpm
rsyslog-7.6.3-1.el7.x86_64.rpm"

    for f in $centos_7_0_ppa_repo_rsyslog_packages; do
        download -u http://rpms.adiscon.com/v7-stable/epel-7/x86_64/RPMS/$f $f copy /var/lib/cobbler/repo_mirror/centos_7_0_ppa_repo/ || exit $?
    done

    # download chef client for centos ppa repo
    CENTOS_7_0_CHEF_CLIENT_SOURCE=`fastesturl "$CENTOS_7_0_CHEF_CLIENT" "$CENTOS_7_0_CHEF_CLIENT_HUAWEI"`
    download -u $CENTOS_7_0_CHEF_CLIENT -u $CENTOS_7_0_CHEF_CLIENT_HUAWEI `basename $CENTOS_7_0_CHEF_CLIENT` copy /var/lib/cobbler/repo_mirror/centos_7_0_ppa_repo/

    # create centos repo
    cd ..
    sudo createrepo centos_7_0_ppa_repo
    if [[ "$?" != "0" ]]; then
        echo "failed to createrepo centos_7_0_ppa_repo"
        exit 1
    else
        echo "centos_7_0_ppa_repo is created"
    fi
fi


# create ubuntu repo
if [[ $SUPPORT_UBUNTU_12_04 == "y" ]]; then
    sudo rm -rf /var/lib/cobbler/repo_mirror/ubuntu_12_04_ppa_repo
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

    cd /var/lib/cobbler/repo_mirror/ubuntu_12_04_ppa_repo/
    if [ ! -e /var/lib/cobbler/repo_mirror/ubuntu_12_04_ppa_repo/conf/distributions ]; then
        echo "create ubuntu 12.04 ppa repo distribution"
        mkdir -p /var/lib/cobbler/repo_mirror/ubuntu_12_04_ppa_repo/conf
        cat << EOF > /var/lib/cobbler/repo_mirror/ubuntu_12_04_ppa_repo/conf/distributions
Origin: ppa
Label: ppa_repo
Suite: stable
Codename: ppa
Version: 0.1
Architectures: i386 amd64 source
Components: main
Description: ppa repo
EOF
        chmod 644 /var/lib/cobbler/repo_mirror/ubuntu_12_04_ppa_repo/conf/distributions
    else
        echo "ubuntu 12.04 ppa repo distribution file exists."
    fi

    # download chef client for ubuntu ppa repo
    download -u $UBUNTU_12_04_CHEF_CLIENT -u $UBUNTU_12_04_CHEF_CLIENT_HUAWEI `basename $UBUNTU_12_04_CHEF_CLIENT` copy /var/lib/cobbler/repo_mirror/ubuntu_12_04_ppa_repo/ || exit $?

    cd ..
    find ubuntu_12_04_ppa_repo -name \*.deb -exec reprepro -Vb ubuntu_12_04_ppa_repo includedeb ppa {} \;
    if [ "$?" != "0" ]; then
        echo "failed to create ubuntu_12_04_ppa_repo"
        exit 1
    else
        echo  "ubuntu_12_04_ppa_repo is created"
    fi
fi

if [[ $SUPPORT_UBUNTU_14_04 == "y" ]]; then
    sudo rm -rf /var/lib/cobbler/repo_mirror/ubuntu_14_04_ppa_repo
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

    cd /var/lib/cobbler/repo_mirror/ubuntu_14_04_ppa_repo/
    if [ ! -e /var/lib/cobbler/repo_mirror/ubuntu_14_04_ppa_repo/conf/distributions ]; then
        echo "create ubuntu 14.04 ppa repo distribution"
        mkdir -p /var/lib/cobbler/repo_mirror/ubuntu_14_04_ppa_repo/conf
        cat << EOF > /var/lib/cobbler/repo_mirror/ubuntu_13_04__ppa_repo/conf/distributions
Origin: ppa
Label: ppa_repo
Suite: stable
Codename: ppa
Version: 0.1
Architectures: i386 amd64 source
Components: main
Description: ppa repo
EOF
        chmod 644 /var/lib/cobbler/repo_mirror/ubuntu_14_04_ppa_repo/conf/distributions
    else
        echo "ubuntu 14.04 ppa repo distribution file exists."
    fi

    # download chef client for ubuntu ppa repo
    download -u $UBUNTU_14_04_CHEF_CLIENT -u $UBUNTU_14_04_CHEF_CLIENT_HUAWEI `basename $UBUNTU_14_04_CHEF_CLIENT` copy /var/lib/cobbler/repo_mirror/ubuntu_14_04_ppa_repo/ || exit $?

    cd ..
    find ubuntu_14_04_ppa_repo -name \*.deb -exec reprepro -Vb ubuntu_14_04_ppa_repo includedeb ppa {} \;
    if [ "$?" != "0" ]; then
        echo "failed to create ubuntu_12_04_ppa_repo"
        exit 1
    else
        echo  "ubuntu_14_04_ppa_repo is created"
    fi
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
    download -u $CENTOS_6_5_IMAGE_SOURCE_ASIA -u $CENTOS_6_5_IMAGE_SOURCE CentOS-6.5-x86_64.iso copy /var/lib/cobbler/iso/ || exit $?
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
    download -u $CENTOS_6_6_IMAGE_SOURCE_ASIA -u $CENTOS_6_6_IMAGE_SOURCE CentOS-6.6-x86_64.iso copy /var/lib/cobbler/iso/ || exit $?
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
    download -u $CENTOS_7_0_IMAGE_SOURCE_ASIA -u $CENTOS_7_0_IMAGE_SOURCE CentOS-7.0-x86_64.iso copy /var/lib/cobbler/iso/ || exit $?
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
    download -u $UBUNTU_12_04_IMAGE_SOURCE_ASIA -u $UBUNTU_12_04_IMAGE_SOURCE Ubuntu-12.04-x86_64.iso copy /var/lib/cobbler/iso/ || exit $?
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
    download -u $UBUNTU_14_04_IMAGE_SOURCE_ASIA -u $UBUNTU_14_04_IMAGE_SOURCE Ubuntu-14.04-x86_64.iso copy /var/lib/cobbler/iso/ || exit $?
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

# add distro
if [[ $SUPPORT_CENTOS_6_5 == "y" ]]; then
    found_centos_6_5_distro=0
    for distro in $(cobbler distro list); do
        if [ "$distro" == "CentOS-6.5-x86_64" ]; then
            found_centos_6_5_distro=1
        fi
    done

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
    for profile in $(cobbler profile list); do
        if [ "$profile" == "CentOS-6.5-x86_64" ]; then
            centos_6_5_found_profile=1
        fi
    done

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
    for distro in $(cobbler distro list); do
        if [ "$distro" == "CentOS-6.6-x86_64" ]; then
            found_centos_6_6_distro=1
        fi
    done

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
    for profile in $(cobbler profile list); do
        if [ "$profile" == "CentOS-6.6-x86_64" ]; then
            centos_6_6_found_profile=1
        fi
    done

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
    for distro in $(cobbler distro list); do
        if [ "$distro" == "CentOS-7.0-x86_64" ]; then
            found_centos_7_0_distro=1
        fi
    done

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
    for distro in $(cobbler distro list); do
        if [ "$distro" == "Ubuntu-12.04-x86_64" ]; then
            found_ubuntu_12_04_distro=1
        fi
    done

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
    for profile in $(cobbler profile list); do
        if [ "$profile" == "Ubuntu-12.04-x86_64" ]; then
            ubuntu_12_04_found_profile=1
        fi
    done

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
    sudo cobbler repo remove --name=Ubuntu-12.04-x86_64
fi

if [[ $SUPPORT_UBUNTU_14_04 == "y" ]]; then
    found_ubuntu_14_04_distro=0
    for distro in $(cobbler distro list); do
        if [ "$distro" == "Ubuntu-14.04-x86_64" ]; then
            found_ubuntu_14_04_distro=1
        fi
    done

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
    for profile in $(cobbler profile list); do
        if [ "$profile" == "Ubuntu-14.04-x86_64" ]; then
            ubuntu_14_04_found_profile=1
        fi
    done

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
    sudo cobbler repo remove --name=Ubuntu-14.04-x86_64
fi


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
