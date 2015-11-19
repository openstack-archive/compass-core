if [ -d "/var/local/osd" ]; then
echo "clear /var/local/osd"
rm -r /var/local/osd/
umount /var/local/osd
rm -r /var/local/osd
fi


#safe check
ps -ef |grep lvremove |awk '{print $2}' |xargs kill -9
ps -ef |grep vgremove |awk '{print $2}' |xargs kill -9
ps -ef |grep vgcreate |awk '{print $2}' |xargs kill -9
ps -ef |grep lvcreate |awk '{print $2}' |xargs kill -9

if [ -L "/dev/cinder-volumes/ceph0" ]; then
echo "remove lv vg"
lvremove -f /dev/cinder-volumes/ceph0
fi


echo "lvcreate"
lvcreate -l 100%FREE -nceph0 cinder-volumes
echo "mkfs"
mkfs.xfs -f /dev/cinder-volumes/ceph0

if [ ! -d "/var/local/osd" ]; then
echo "mount osd"
mkdir -p /var/local/osd
mount /dev/cinder-volumes/ceph0 /var/local/osd
fi

