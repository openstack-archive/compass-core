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
sudo yum -y install cobbler cobbler-web createrepo mkisofs python-cheetah python-simplejson python-urlgrabber PyYAML Django corosync pykickstart
sudo yum -y upgrade yum-utils
if [[ "$?" != "0" ]]; then
    echo "failed to install cobbler related packages"
    exit 1
#else
    # patch cobbler code
#    find /usr/lib -name manage_bind.py |xargs  perl -pi.old -e 's/(\s+)(self\.logger\s+\= logger)/$1$2\n$1if self\.logger is None:\n$1    import clogger\n$1    self\.logger = clogger.Logger\(\)/'
fi

# cobbler snippet uses netaddr to calc subnet and ip addr
sudo pip install netaddr
if [[ "$?" != "0" ]]; then
    echo "failed to install pip packages"
    exit 1
fi

sudo systemctl enable cobblerd.service

# create backup dir
sudo mkdir -p /root/backup/cobbler

# update bootloaders
download -u "$COBBLER_LOADERS_SOURCE" -u "$COBBLER_LOADERS_SOURCE_ASIA" loaders.tar.gz unzip /var/lib/cobbler || exit $?

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
if [[ -f /etc/cobbler/dhcp.template ]]; then
    sudo cp -rn /etc/cobbler/dhcp.template /root/backup/cobbler/
fi
sudo cp -rf $DIR/dhcp.template /etc/cobbler/dhcp.template
export netaddr=$(ipcalc $IPADDR $NETMASK -n |cut -f 2 -d '=')
export netprefix=$(ipcalc $IPADDR $NETMASK -p |cut -f 2 -d '=')
export subnet=${netaddr}/${netprefix}
sudo sed -i "s/subnet \$subnet netmask \$netmask/subnet $netaddr netmask $NETMASK/g" /etc/cobbler/dhcp.template
sudo sed -i "s/option routers \$gateway/option routers $OPTION_ROUTER/g" /etc/cobbler/dhcp.template
sudo sed -i "s/option subnet-mask \$netmask/option subnet-mask $NETMASK/g" /etc/cobbler/dhcp.template
sudo sed -i "s/option domain-name-servers \$ipaddr/option domain-name-servers $IPADDR/g" /etc/cobbler/dhcp.template
sudo sed -i "s/range dynamic-bootp \$ip_range/range dynamic-bootp $IP_START $IP_END/g" /etc/cobbler/dhcp.template
sudo sed -i "s/local-address \$ipaddr/local-address $IPADDR/g" /etc/cobbler/dhcp.template
sudo sed -i "s/next-server \$next_server/next-server $NEXTSERVER/g" /etc/cobbler/dhcp.template
sudo chmod 644 /etc/cobbler/dhcp.template
sudo cp -f /etc/cobbler/dhcp.template /etc/dhcp/dhcpd.conf

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
sudo cp  $COMPASSDIR/misc/rsync /etc/xinetd.d/

#sudo sed -i 's/^@dists=/# @dists=/g' /etc/debmirror.conf
#sudo sed -i 's/^@arches=/# @arches=/g' /etc/debmirror.conf

sudo rm -rf /var/lib/cobbler/config/systems.d/*

sudo systemctl stop firewalld

# echo "disable selinux temporarily"
# echo 0 > /selinux/enforce

# make log dir
sudo mkdir -p /var/log/cobbler
sudo mkdir -p /var/log/cobbler/tasks
sudo mkdir -p /var/log/cobbler/anamon
sudo chmod -R 777 /var/log/cobbler

sudo systemctl restart httpd.service
sudo systemctl restart cobblerd.service
sudo systemctl restart named.service
sudo systemctl restart xinetd.service
sudo systemctl restart dhcpd.service

sudo sleep 10

echo "Checking if httpd is running"
sudo systemctl status httpd.service
if [[ "$?" != "0" ]]; then
    echo "httpd is not running"
    exit 1
fi

echo "Checking if dhcpd is running"
sudo systemctl status dhcpd.service
if [[ "$?" != "0" ]]; then
    echo "dhcpd is not running"
    exit 1
fi

echo "Checking if named is running"
sudo systemctl status named.service
if [[ "$?" != "0" ]]; then
    echo "named is not running"
    exit 1
fi

echo "Checking if xinetd is running"
sudo systemctl status xinetd.service
if [[ "$?" != "0" ]]; then
    echo "xinetd is not running"
    exit 1
fi

echo "Checking if cobblerd is running"
sudo systemctl status cobblerd.service
if [[ "$?" != "0" ]]; then
    echo "cobblerd is not running"
    exit 1
fi

sudo cobbler get-loaders
if [[ "$?" != "0" ]]; then
    echo "failed to get loaders for cobbler"
    exit 1
fi

for i in $UBUNTU_14_04_03_IMAGE_SOURCE; do
    sudo mkdir -p /var/lib/cobbler/iso
    download  -u "$i" `basename "$i"` copy /var/lib/cobbler/iso/ || exit $?
    name=`basename "$i" | sed -e 's/.iso//g' -e 's/-amd64//g' -e 's/-x86_64//g'`-x86_64
    if [[ `mount | grep "$name"` -eq 0 ]]; then
        sudo mkdir -p /mnt/$name    
        sudo mount -o loop /var/lib/cobbler/iso/`basename $i` /mnt/$name
        if [[ "$?" != "0" ]]; then
            echo "failed to mount image /mnt/$name"
            exit 1
        fi

        cobbler import --path=/mnt/$name \
                       --name $name \
                       --arch=x86_64 \
                       --kickstart=/var/lib/cobbler/kickstarts/default.seed \
                       --breed=ubuntu
        if [[ "$?" != "0" ]]; then
            echo "failed to import /mnt/$i"
            exit 1
        fi
    fi
done

for i in $CENTOS_7_2_IMAGE_SOURCE; do
    sudo mkdir -p /var/lib/cobbler/iso
    download  -u "$i" `basename "$i"` copy /var/lib/cobbler/iso/ || exit $?
    name=`basename "$i" | sed -e 's/.iso//g' -e 's/-amd64//g' -e 's/-x86_64//g'`-x86_64
    if [[ `mount | grep "$name"` -eq 0 ]]; then
        sudo mkdir -p /mnt/$name
        sudo mount -o loop /var/lib/cobbler/iso/`basename $i` /mnt/$name
        if [[ "$?" != "0" ]]; then
            echo "failed to mount image /mnt/$name"
            exit 1
        fi

        cobbler import --path=/mnt/$name \
                       --name $name \
                       --arch=x86_64 \
                       --kickstart=/var/lib/cobbler/kickstarts/default.ks \
                       --breed=redhat
        if [[ "$?" != "0" ]]; then
            echo "failed to import /mnt/$i"
            exit 1
        fi
    fi
    
done

cobbler repo list | xargs -n 1 cobbler repo remove --name

for i in $UBUNTU_14_04_03_PPA_REPO_SOURCE; do
     download -u "$i" `basename "$i"` unzip /var/lib/cobbler/repo_mirror || exit $?
     filename=`basename $i | sed 's/.tar.gz//g'`
     cobbler repo add --name $filename --mirror=/var/lib/cobbler/repo_mirror/$filename \
                      --mirror-locally=Y --arch=x86_64 --apt-dists=trusty --apt-components=main

     if [[ "$?" != "0" ]]; then
         echo "failed to add repo $i"
         exit 1
     fi
done

for i in $CENTOS_7_2_PPA_REPO_SOURCE; do
     download -u "$i" `basename "$i"` unzip /var/lib/cobbler/repo_mirror || exit $?
     filename=`basename $i | sed 's/.tar.gz//g'`
     cobbler repo add --name $filename --mirror=/var/lib/cobbler/repo_mirror/$filename \
                      --mirror-locally=Y --arch=x86_64
     if [[ "$?" != "0" ]]; then
         echo "failed to add repo $i"
         exit 1
     fi
done

for i in $UBUNTU_14_04_03_IMAGE_SOURCE; do
    name=`basename "$i" | sed -e 's/.iso//g' -e 's/-amd64//g' -e 's/-x86_64//g'`-x86_64
    cobbler profile edit --name=$name \
            --distro=$name --ksmeta="tree=http://$IPADDR/cobbler/ks_mirror/$name" \
            --kickstart=/var/lib/cobbler/kickstarts/default.seed \
            --kopts="netcfg/choose_interface=auto console='ttyS0,115200n8' console=tty0 biosdevname=0" \
            --kopts-post="console='ttyS0,115200n8' console=tty0 biosdevname=0"
done

for i in $CENTOS_7_2_IMAGE_SOURCE; do
    name=`basename "$i" | sed -e 's/.iso//g' -e 's/-amd64//g' -e 's/-x86_64//g'`-x86_64
    cobbler profile edit --name=$name \
            --distro=$name --ksmeta="tree=http://$IPADDR/cobbler/ks_mirror/$name" \
            --kickstart=/var/lib/cobbler/kickstarts/default.ks
done

sudo cobbler reposync
if [[ "$?" != "0" ]]; then
    echo "cobbler reposync failed"
    exit 1
fi

sudo cobbler sync
if [[ "$?" != "0" ]]; then
    echo "cobbler sync failed"
    exit 1
fi

echo "Checking cobbler is OK"
sudo cobbler check
if [[ "$?" != "0" ]]; then
    echo "cobbler check failed"
    exit 1
fi

echo "Cobbler configuration complete!"
