# Kickstart for Profile: CentOS6.4_x86-64-1
# Distro: CentOS6.4

# System Authorization
auth --useshadow --enablemd5

# System Bootloader
bootloader --location=mbr

# Clear MBR
zerombr

# Use Text Mode
text

# Disable Firewall
firewall --disabled

# Run the Setup Agent on first-boot
firstboot --disable

# System Keyboard
keyboard us

# Language Setting
lang en_US

# Installation Loggin Level
logging --level=info

# Network Installation
url --url=$tree


$SNIPPET('kickstart_network_config')
$SNIPPET('kickstart_partition_disks')
$SNIPPET('kickstart_yum_repo_config')

# Root Password
#if $getVar('password', '') != ""
rootpw --iscrypted $password
#else
rootpw root
#end if

# Selinux Disable
selinux --disabled

# No X Window System
skipx

# System Timezone
#if $getVar('timezone', '') != ""
timezone --utc $timezone
#else
timezone --utc US/Pacific
#end if

# Install
install

# Reboot After Installation
reboot

%pre
$SNIPPET('log_ks_pre')
$SNIPPET('kickstart_start')
$SNIPPET('kickstart_pre_install_network_config')
$SNIPPET('kickstart_pre_partition_disks')

# Enable installation monitoring
$SNIPPET('kickstart_pre_anamon')

# Packages
%packages --nobase
@core 
iproute
chef
ntp
openssh-clients
wget
json-c
libestr
libgt
liblogging
rsyslog

%post --log=/var/log/post_install.log
$SNIPPET('log_ks_post')
$SNIPPET('kickstart_post_install_kernel_options')
$SNIPPET('kickstart_post_install_network_config')

chkconfig iptables off
chkconfig ip6tables off

$SNIPPET('kickstart_yum.conf')
$SNIPPET('kickstart_ssh')
$SNIPPET('kickstart_ntp')
$SNIPPET('kickstart_limits.conf')
$SNIPPET('kickstart_sysctl.conf')
$SNIPPET('kickstart_rsyslog.conf')
#if $getVar('tool', '') != ''
    #set $kickstart_tool = "kickstart_%s" % $tool
$SNIPPET($kickstart_tool)
#end if
$SNIPPET('kickstart_post_anamon')
$SNIPPET('kickstart_done')
