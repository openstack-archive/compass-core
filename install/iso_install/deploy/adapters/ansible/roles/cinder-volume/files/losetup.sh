loop_dev=`losetup -a |grep "/var/cinder.img"|awk -F':' '{print $1}'`
if [[ -z $loop_dev ]]; then
  losetup -f --show /var/cinder.img
else
  echo $loop_dev
fi

