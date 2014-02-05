#!/bin/bash

echo "Installing cobbler related packages"
sudo yum -y install cobbler cobbler-web createrepo mkisofs python-cheetah  python-simplejson python-urlgrabber PyYAML Django cman debmirror pykickstart -y

sudo chkconfig cobblerd on

# create backup dir
sudo mkdir /root/backup # create backup folder

# configure ntp
sudo cp /etc/ntp.conf /root/backup/
# update ntp.conf
sudo sed -i 's/^#server[ \t]\+127.127.1.0/server 127.127.1.0/g' /etc/ntp.conf
sudo service ntpd stop
sudo ntpdate 0.centos.pool.ntp.org
sudo service ntpd start

##export ipaddr=$(ifconfig $NIC | grep 'inet addr:' | cut -d: -f2 | awk '{ print $1}')
export cobbler_passwd=$(openssl passwd -1 -salt 'huawei' '123456')

# configure dhcpd
##SUBNET=${SUBNET:-$(ipcalc $(ip address| grep "global $NIC" |cut -f 6 -d ' ') -n|cut -f 2 -d '=')}

##OPTION_ROUTER=${OPTION_ROUTER:-$(ifconfig $NIC | grep 'inet addr:' | cut -d: -f2 | awk '{ print $1}')}

##IP_RANGE=${IP_RANGE:-$(echo "$(echo "$ipaddr"|cut -f 1 -d '.').$(echo "$ipaddr"|cut -f 2 -d '.').$(echo "$ipaddr"|cut -f 3 -d '.').100 $(echo "$ipaddr"|cut -f 1 -d '.').$(echo "$ipaddr"|cut -f 2 -d '.').$(echo "$ipaddr"|cut -f 3 -d '.').254")}

##NEXTSERVER=${NEXTSERVER:-$ipaddr}

sudo mkdir /root/backup/cobbler
sudo cp /etc/cobbler/settings /root/backup/cobbler/
sudo cp /etc/cobbler/dhcp.template /root/backup/cobbler/
sudo cp /etc/cobbler/tfptd.template /root/backup/cobbler/

# Dumps the variables to dhcp template
subnet=$(ipcalc $SUBNET -n |cut -f 2 -d '=')
sudo sed -i "s/subnet 192.168.1.0 netmask 255.255.255.0/subnet $subnet netmask $netmask/g" /etc/cobbler/dhcp.template
sudo sed -i "/option routers[ \t]\+[a-zA-Z0-9]\+.[a-zA-Z0-9]\+.[a-zA-Z0-9]\+.[a-zA-Z0-9]\+/c\     option routers             $OPTION_ROUTER;" /etc/cobbler/dhcp.template
sudo sed -i "s/option subnet-mask[ \t]\+255.255.255.0/option subnet-mask         $netmask/g" /etc/cobbler/dhcp.template
sudo sed -i "/option domain-name-servers/c\	option domain-name-servers	$ipaddr;" /etc/cobbler/dhcp.template
sudo sed -i "/range dynamic-bootp/c\     range dynamic-bootp        $IP_RANGE;" /etc/cobbler/dhcp.template
sudo sed -i 's/^\([ \t]*\).*fixed-address.*$/\1#pass/g' /etc/cobbler/dhcp.template
sudo sed -i "/allow bootp/a deny unknown-clients;\nlocal-address $ipaddr;" /etc/cobbler/dhcp.template

# update tftpd.template
sudo rm -f /etc/cobbler/tftpd.template
sudo cp -rf $ADAPTER_HOME/cobbler/conf/tftpd.template /etc/cobbler/tftpd.template
sudo chmod 644 /etc/cobbler/tftpd.template

# Set up other setting options in cobbler/settings
sudo sed -i "/next_server/c\next_server: $NEXTSERVER" /etc/cobbler/settings
sudo sed -i "s/server:[ \t]\+127.0.0.1/server: $ipaddr/g" /etc/cobbler/settings
sudo sed -i 's/manage_dhcp:[ \t]\+0/manage_dhcp: 1/g' /etc/cobbler/settings
sudo sed -i 's/manage_dns:[ \t]\+0/manage_dns: 1/g' /etc/cobbler/settings
sudo sed -i 's/manage_tftpd:[ \t]\+0/manage_tftpd: 1/g' /etc/cobbler/settings
sudo sed -i 's/anamon_enabled:[ \t]\+0/anamon_enabled: 1/g' /etc/cobbler/settings
sudo sed -i "s/default_name_servers:.*/default_name_servers: \['$ipaddr'\]/g" /etc/cobbler/settings
sudo sed -i 's/enable_menu:[ \t]\+1/enable_menu: 0/g' /etc/cobbler/settings
domains=$(echo $NAMESERVER_DOMAINS | sed "s/,/','/g")
sudo sed -i "s/manage_forward_zones:.*/manage_forward_zones: \['$domains'\]/g" /etc/cobbler/settings
sudo sed -i 's/pxe_just_once:[ \t]\+0/pxe_just_once: 1/g' /etc/cobbler/settings
sudo sed -i "s,^default_password_crypted:[ \t]\+\"\(.*\)\",default_password_crypted: \"$cobbler_passwd\",g" /etc/cobbler/settings
sudo sed -i 's/^RewriteRule/# RewriteRule/g' /etc/httpd/conf.d/cobbler_web.conf
sudo sed -i 's/^Listen\([ \t]\+\)443/Listen\1445/g' /etc/httpd/conf.d/ssl.conf
sudo sed -i 's/^<VirtualHost\(.*\):443>/<VirtualHost\1:445>/g' /etc/httpd/conf.d/ssl.conf


sudo mkdir /root/backup/selinux
sudo cp /etc/selinux/config /root/backup/selinux/
sudo sed -i '/SELINUX/s/enforcing/disabled/' /etc/selinux/config

sudo cp /etc/cobbler/modules.conf /root/backup/cobbler/
sudo sed -i 's/module\([ \t]\+\)=\([ \t]\+\)authn_denyall/module\1=\2authn_configfile/g' /etc/cobbler/modules.conf

echo "setting up cobbler web password: default user is cobbler"

CBLR_USER=${CBLR_USER:-"cobbler"}
CBLR_PASSWD=${CBLR_PASSWD:-"cobbler"}
(echo -n "$CBLR_USER:Cobbler:" && echo -n "$CBLR_USER:Cobbler:$CBLR_PASSWD" | md5sum - | cut -d' ' -f1) >> /etc/cobbler/users.digest

sudo sed -i "s/listen-on[ \t]\+.*;/listen-on port 53 \{ $ipaddr; \};/g" /etc/cobbler/named.template
subnet_escaped=$(echo $SUBNET | sed -e 's/[\/&]/\\&/g')
sudo sed -i "s/allow-query[ \t]\+.*/allow-query\t\{ 127.0.0.0\/8; 10.0.0.0\/8; 192.168.0.0\/16; 172.16.0.0\/12; $subnet_escaped; \};/g" /etc/cobbler/named.template

echo "$HOSTNAME IN A $ipaddr" >> /etc/cobbler/zone.template

sudo cp /etc/xinetd.d/rsync /root/backup/
sudo sed -i 's/disable\([ \t]\+\)=\([ \t]\+\)yes/disable\1=\2no/g' /etc/xinetd.d/rsync
sudo sed -i 's/^@dists=/# @dists=/g' /etc/debmirror.conf
sudo sed -i 's/^@arches=/# @arches=/g' /etc/debmirror.conf

echo "disable iptables"
sudo service iptables stop

echo "disable selinux temporarily"
echo 0 > /selinux/enforce

echo "Checking if httpd is running"
sudo ps cax | grep httpd > /dev/null
if [ $? -eq 0 ]; then
  echo "httpd is running."
else
  echo "httpd is not running. Starting httpd"
  sudo service httpd start
fi

sudo service cobblerd restart
sudo cobbler get-loaders
sudo cobbler check
sudo cobbler sync

echo "Checking if dhcpd is running"
sudo ps cax | grep dhcpd > /dev/null
if [ $? -eq 0 ]; then
  echo "dhcpd is running."
else
  echo "dhcpd is not running. Starting httpd"
  sudo service dhcpd start
fi

echo "Checking if named is running"
ps cax | grep named > /dev/null
if [ $? -eq 0 ]; then
  echo "named is running."
else
  echo "named is not running. Starting httpd"
  sudo service named start
fi

# create repo
sudo mkdir -p /var/lib/cobbler/repo_mirror/ppa_repo
sudo cobbler repo add --mirror=/var/lib/cobbler/repo_mirror/ppa_repo --name=ppa_repo --mirror-locally=Y
# download packages
cd /var/lib/cobbler/repo_mirror/ppa_repo/
sudo curl http://opscode-omnibus-packages.s3.amazonaws.com/el/6/x86_64/chef-11.8.0-1.el6.x86_64.rpm > chef-11.8.0-1.el6.x86_64.rpm

sudo curl ftp://ftp.muug.mb.ca/mirror/centos/6.5/os/x86_64/Packages/ntp-4.2.6p5-1.el6.centos.x86_64.rpm > ntp-4.2.6p5-1.el6.centos.x86_64.rpm

sudo curl http://vault.centos.org/6.4/os/Source/SPackages/openssh-5.3p1-84.1.el6.src.rpm > openssh-clients-5.3p1-84.1.el6.x86_64.rpm

sudo curl ftp://ftp.muug.mb.ca/mirror/centos/6.5/os/x86_64/Packages/iproute-2.6.32-31.el6.x86_64.rpm > iproute-2.6.32-31.el6.x86_64.rpm

sudo curl ftp://ftp.muug.mb.ca/mirror/centos/6.5/os/x86_64/Packages/wget-1.12-1.8.el6.x86_64.rpm > wget-1.12-1.8.el6.x86_64.rpm

sudo curl ftp://ftp.muug.mb.ca/mirror/centos/6.5/os/x86_64/Packages/ntpdate-4.2.6p5-1.el6.centos.x86_64.rpm > ntpdate-4.2.6p5-1.el6.centos.x86_64.rpm

cd ..
sudo createrepo ppa_repo
sudo cobbler reposync

# import cobbler distro
##export ipaddr=$(ifconfig $NIC | grep 'inet addr:' | cut -d: -f2 | awk '{ print $1}')
sudo mkdir -p /var/lib/cobbler/iso
sudo curl "$IMAGE_SOURCE" > /var/lib/cobbler/iso/$IMAGE_NAME.iso
sudo mkdir -p /mnt/$IMAGE_NAME
sudo mount -o loop /var/lib/cobbler/iso/$IMAGE_NAME.iso /mnt/$IMAGE_NAME
sudo cobbler import --path=/mnt/$IMAGE_NAME --name=$IMAGE_NAME --arch=x86_64
# manually run distro add and profile add if cobbler import fails
sudo cobbler distro add --name="$IMAGE_NAME" --kernel="/var/www/cobbler/ks_mirror/$IMAGE_NAME-x86_64/isolinux/vmlinuz" --initrd="/var/www/cobbler/ks_mirror/$IMAGE_NAME-x86_64/isolinux/initrd.img" --arch=x86_64 --breed=redhat
sudo cobbler profile add --name="$IMAGE_NAME" --repo=ppa_repo --distro=$IMAGE_NAME --ksmeta="tree=http://$ipaddr/cobbler/ks_mirror/$IMAGE_NAME-x86_64" --kickstart=/var/lib/cobbler/kickstarts/default.ks

echo "Cobbler configuration complete!"
