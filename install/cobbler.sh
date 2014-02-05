#!/bin/bash
#

echo "Installing cobbler related packages"
sudo yum -y install cobbler cobbler-web createrepo mkisofs python-cheetah  python-simplejson python-urlgrabber PyYAML Django cman debmirror pykickstart -y
if [[ "$?" != "0" ]]; then
    echo "failed to install cobbler related packages"
    exit 1
else
    echo "cobbler related packages are installed"
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
sudo cp -rf $ADAPTER_HOME/cobbler/conf/settings /etc/cobbler/settings
sudo sed -i "s/next_server:[ \t]*\$next_server/next_server: $NEXTSERVER/g" /etc/cobbler/settings
sudo sed -i "s/server:[ \t]*\$ipaddr/server: $ipaddr/g" /etc/cobbler/settings
sudo sed -i "s/default_name_servers:[ \t]*\['\$ipaddr'\]/default_name_servers: \['$ipaddr'\]/g" /etc/cobbler/settings
domains=$(echo $NAMESERVER_DOMAINS | sed "s/,/','/g")
sudo sed -i "s/manage_forward_zones:[ \t]*\[\]/manage_forward_zones: \['$domains'\]/g" /etc/cobbler/settings
export cobbler_passwd=$(openssl passwd -1 -salt 'huawei' '123456')
sudo sed -i "s,^default_password_crypted:[ \t]\+\"\(.*\)\",default_password_crypted: \"$cobbler_passwd\",g" /etc/cobbler/settings
sudo chmod 644 /etc/cobbler/settings

# update dhcp.template
sudo cp -rn /etc/cobbler/dhcp.template /root/backup/cobbler/
sudo rm -f /etc/cobbler/dhcp.template
sudo cp -rf $ADAPTER_HOME/cobbler/conf/dhcp.template /etc/cobbler/dhcp.template
subnet=$(ipcalc $SUBNET -n |cut -f 2 -d '=')
sudo sed -i "s/subnet \$subnet netmask \$netmask/subnet $subnet netmask $netmask/g" /etc/cobbler/dhcp.template
sudo sed -i "s/option routers \$gateway/option routers $OPTION_ROUTER/g" /etc/cobbler/dhcp.template
sudo sed -i "s/option subnet-mask \$netmask/option subnet-mask $netmask/g" /etc/cobbler/dhcp.template
sudo sed -i "s/option domain-name-servers \$ipaddr/option domain-name-servers $ipaddr/g" /etc/cobbler/dhcp.template
sudo sed -i "s/range dynamic-bootp \$ip_range/range dynamic-bootp $IP_RANGE/g" /etc/cobbler/dhcp.template
sudo sed -i "s/local-address \$ipaddr/local-address $ipaddr/g" /etc/cobbler/dhcp.template
sudo chmod 644 /etc/cobbler/dhcp.template

# update tftpd.template
sudo cp -rn /etc/cobbler/tftpd.template /root/backup/cobbler/
sudo rm -f /etc/cobbler/tftpd.template
sudo cp -rf $ADAPTER_HOME/cobbler/conf/tftpd.template /etc/cobbler/tftpd.template
sudo chmod 644 /etc/cobbler/tftpd.template

# update named.template
sudo cp -rn /etc/cobbler/named.template /root/backup/cobbler/
sudo rm -f /etc/cobbler/named.template
sudo cp -rf $ADAPTER_HOME/cobbler/conf/named.template /etc/cobbler/named.template
sudo sed -i "s/listen-on port 53 { \$ipaddr; }/listen-on port 53 \{ $ipaddr; \}/g" /etc/cobbler/named.template
subnet_escaped=$(echo $SUBNET | sed -e 's/[\/&]/\\&/g')
sudo sed -i "s/allow-query { 127.0.0.0\/8; \$subnet; }/allow-query \{ 127.0.0.0\/8; $subnet_escaped; \}/g" /etc/cobbler/named.template
sudo chmod 644 /etc/cobbler/named.template

# update zone.template
sudo cp -rn /etc/cobbler/zone.template /root/backup/cobbler/
sudo rm -f /etc/cobbler/zone.template
sudo cp -rf $ADAPTER_HOME/cobbler/conf/zone.template /etc/cobbler/zone.template
sudo sed -i "s/\$hostname IN A \$ipaddr/$HOSTNAME IN A $ipaddr/g" /etc/cobbler/zone.template
sudo chmod 644 /etc/cobbler/zone.template

# update modules.conf
sudo cp -rn /etc/cobbler/modules.conf /root/backup/cobbler/
sudo rm -f /etc/cobbler/modules.conf
sudo cp -rf $ADAPTER_HOME/cobbler/conf/modules.conf /etc/cobbler/modules.conf
sudo chmod 644 /etc/cobbler/modules.conf

echo "setting up cobbler web password: default user is cobbler"

CBLR_USER=${CBLR_USER:-"cobbler"}
CBLR_PASSWD=${CBLR_PASSWD:-"cobbler"}
(echo -n "$CBLR_USER:Cobbler:" && echo -n "$CBLR_USER:Cobbler:$CBLR_PASSWD" | md5sum - | cut -d' ' -f1) > /etc/cobbler/users.digest

# update cobbler config
sudo cp -rn /var/lib/cobbler/snippets /root/backup/cobbler/
sudo cp -rn /var/lib/cobbler/kickstarts/ /root/backup/cobbler/
sudo rm -rf /var/lib/cobbler/snippets/*
sudo cp -rf $ADAPTER_HOME/cobbler/snippets/* /var/lib/cobbler/snippets/
sudo chmod 777 /var/lib/cobbler/snippets
sudo chmod 666 /var/lib/cobbler/snippets/*
sudo sed -i "s/# \$compass_ip \$compass_hostname/$ipaddr $HOSTNAME/g" /var/lib/cobbler/snippets/hosts
sudo rm -f /var/lib/cobbler/kickstarts/default.ks
sudo cp -rf $ADAPTER_HOME/cobbler/kickstarts/default.ks /var/lib/cobbler/kickstarts/
sudo chmod 666 /var/lib/cobbler/kickstarts/default.ks

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
fi

echo "disable selinux temporarily"
echo 0 > /selinux/enforce

sudo service httpd restart
sudo service cobblerd restart
sudo cobbler get-loaders
sudo cobbler sync
sudo service xinetd restart
sudo cobbler check

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
if [[ "$?" == "0" ]]; then
  echo "cobblerd is running."
else
  echo "cobblerd is not running"
  exit 1
fi

# create repo
sudo mkdir -p /var/lib/cobbler/repo_mirror/ppa_repo
found_ppa_repo=0
for repo in $(cobbler repo list); do
if [ "$repo" == "ppa_repo" ]; then
found_ppa_repo=1
fi
done

if [ "$found_ppa_repo" == "0" ]; then
sudo cobbler repo add --mirror=/var/lib/cobbler/repo_mirror/ppa_repo --name=ppa_repo --mirror-locally=Y
if [[ "$?" != "0" ]]; then
    echo "failed to add ppa_repo"
    exit 1
else
    echo "ppa_repo is added"
fi
else
echo "repo ppa_repo has already existed."
fi

# download packages
cd /var/lib/cobbler/repo_mirror/ppa_repo/
sudo wget -c --progress=bar:force -O chef-11.8.0-1.el6.${IMAGE_ARCH}.rpm http://opscode-omnibus-packages.s3.amazonaws.com/el/${IMAGE_VERSION_MAJOR}/${IMAGE_ARCH}/chef-11.8.0-1.el6.${IMAGE_ARCH}.rpm

sudo wget -c --progress=bar:force -O ntp-4.2.6p5-1.el6.${IMAGE_TYPE}.$IMAGE_ARCH.rpm ftp://rpmfind.net/linux/${IMAGE_TYPE,,}/${IMAGE_VERSION}/os/${IMAGE_ARCH}/Packages/ntp-4.2.6p5-1.el6.${IMAGE_TYPE,,}.${IMAGE_ARCH}.rpm 

sudo wget -c --progress=bar:force -O openssh-clients-5.3p1-94.1.el6.${IMAGE_ARCH}.rpm http://vault.${IMAGE_TYPE,,}.org/${IMAGE_VERSION}/os/Source/SPackages/openssh-5.3p1-94.el6.src.rpm

sudo wget -c --progress=bar:force -O iproute-2.6.32-31.el6.${IMAGE_ARCH}.rpm ftp://rpmfind.net/linux/${IMAGE_TYPE,,}/${IMAGE_VERSION_MAJOR}/os/${IMAGE_ARCH}/Packages/iproute-2.6.32-31.el6.${IMAGE_ARCH}.rpm

sudo wget -c --progress=bar:force -O wget-1.12-1.8.el6.${IMAGE_ARCH}.rpm ftp://rpmfind.net/linux/${IMAGE_TYPE,,}/${IMAGE_VERSION_MAJOR}/os/${IMAGE_ARCH}/Packages/wget-1.12-1.8.el6.${IMAGE_ARCH}.rpm

sudo wget -c --progress=bar:force -O ntpdate-4.2.6p5-1.el6.${IMAGE_TYPE}.${IMAGE_ARCH}.rpm ftp://rpmfind.net/linux/${IMAGE_TYPE,,}/${IMAGE_VERSION_MAJOR}/os/${IMAGE_ARCH}/Packages/ntpdate-4.2.6p5-1.el6.${IMAGE_TYPE,,}.${IMAGE_ARCH}.rpm

cd ..
sudo createrepo ppa_repo
if [[ "$?" != "0" ]]; then
    echo "failed to createrepo ppa_repo"
    exit 1
else
    echo "ppa_repo is created"
fi

sudo cobbler reposync

# import cobbler distro
sudo mkdir -p /var/lib/cobbler/iso
sudo wget -c --progress=bar:force -O /var/lib/cobbler/iso/${IMAGE_NAME}-${IMAGE_ARCH}.iso "$IMAGE_SOURCE"
if [[ "$?" != "0" ]]; then
    echo "failed to download images $IMAGE_SOURCE"
    exit 1
else
    echo "$IMAGE_SOURCE is downloaded"
fi

sudo mkdir -p /mnt/${IMAGE_NAME}-${IMAGE_ARCH}
if [ $(mount | grep -c /mnt/${IMAGE_NAME}-${IMAGE_ARCH}) != 1 ]; then
sudo mount -o loop /var/lib/cobbler/iso/${IMAGE_NAME}-${IMAGE_ARCH}.iso /mnt/${IMAGE_NAME}-${IMAGE_ARCH}
if [[ "$?" != "0" ]]; then
    echo "failed to mount image /mnt/${IMAGE_NAME}-${IMAGE_ARCH}"
    exit 1
else
    echo "/mnt/${IMAGE_NAME}-${IMAGE_ARCH} is mounted"
fi
else
echo "/mnt/${IMAGE_NAME}-${IMAGE_ARCH} has already mounted"
fi

# add distro
found_distro=0
for distro in $(cobbler distro list); do
if [ "$distro" == "${IMAGE_NAME}-${IMAGE_ARCH}" ]; then
found_distro=1
fi
done

if [ "$found_distro" == "0" ]; then
sudo cobbler import --path=/mnt/${IMAGE_NAME}-${IMAGE_ARCH} --name=${IMAGE_NAME} --arch=${IMAGE_ARCH} --kickstart=/var/lib/cobbler/kickstarts/default.ks --breed=redhat
if [[ "$?" != "0" ]]; then
    echo "failed to import /mnt/${IMAGE_NAME}-${IMAGE_ARCH}"
    exit 1
else
    echo "/mnt/${IMAGE_NAME}-${IMAGE_ARCH} is imported" 
fi
else
echo "distro $IMAGE_NAME has already existed"
fi

# add profile
found_profile=0
for profile in $(cobbler profile list); do
if [ "$profile" == "${IMAGE_NAME}-${IMAGE_ARCH}" ]; then
found_profile=1
fi
done

if [ "$found_profile" == "0" ]; then
sudo cobbler profile add --name="${IMAGE_NAME}-${IMAGE_ARCH}" --repo=ppa_repo --distro="${IMAGE_NAME}-${IMAGE_ARCH}" --ksmeta="tree=http://$ipaddr/cobbler/ks_mirror/${IMAGE_NAME}-${IMAGE_ARCH}" --kickstart=/var/lib/cobbler/kickstarts/default.ks
if [[ "$?" != "0" ]]; then
    echo "failed to add profile ${IMAGE_NAME}-${IMAGE_ARCH}"
    exit 1
else
    echo "profile ${IMAGE_NAME}-${IMAGE_ARCH} is added"
fi
else
echo "profile $IMAGE_NAME has already existed."
sudo cobbler profile edit --name="${IMAGE_NAME}-${IMAGE_ARCH}" --repo=ppa_repo
if [[ "$?" != "0" ]]; then
    echo "failed to edit profile ${IMAGE_NAME}-${IMAGE_ARCH}"
    exit 1
else
    echo "profile ${IMAGE_NAME}-${IMAGE_ARCH} is updated"
fi
fi

echo "Cobbler configuration complete!"
