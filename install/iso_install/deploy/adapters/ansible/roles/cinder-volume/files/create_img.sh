if [[ ! -f /var/cinder.img ]]; then
  dd if=/dev/zero of=/var/cinder.img bs=1 count=0 seek=$1
fi
