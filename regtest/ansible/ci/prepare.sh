sudo apt-get update -y
sudo apt-get install git python-pip python-dev -y
vagrant --version
if [[ $? != 0 ]]; then
    vagrant_pkg_url=https://dl.bintray.com/mitchellh/vagrant/vagrant_1.7.2_x86_64.deb
    wget ${vagrant_pkg_url}
    sudo dpkg -i $(basename ${vagrant_pkg_url})
else
    echo "vagrant is already installed"
fi
sudo apt-get install libxslt-dev libxml2-dev libvirt-dev build-essential qemu-utils qemu-kvm libvirt-bin virtinst libmysqld-dev -y
sudo service libvirt-bin restart

for plugin in vagrant-libvirt vagrant-mutate; do
    vagrant plugin list |grep $plugin
    if [[ $? != 0 ]]; then
        vagrant plugin install $plugin
    else
        echo "$plugin plugin is already installed"
    fi
done

#precise_box_vb_url=https://cloud-images.ubuntu.com/vagrant/precise/current/precise-server-cloudimg-amd64-vagrant-disk1.box
#precise_box_vb_filename=$(basename ${precise_box_vb_url})
centos65_box_vb_url=https://developer.nrel.gov/downloads/vagrant-boxes/CentOS-6.5-x86_64-v20140504.box
centos65_box_vb_filename=$(basename ${centos65_box_vb_url})
#wget ${precise_box_vb_url}
vagrant box list |grep centos65
if [[ $? != 0 ]]; then
    if [ -f "/opt/regtest/boxes/CentOS-6.5-x86_64-v20140504.box" ]; then
        echo "centos65 box file found"
        mv /opt/regtest/boxes/CentOS-6.5-x86_64-v20140504.box centos65.box
    else
        wget ${centos65_box_vb_url}
        mv ${centos65_box_vb_filename} centos65.box
    vagrant mutate centos65.box libvirt
else
    echo "centos65 box already exists"
fi
