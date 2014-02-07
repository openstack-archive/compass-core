#!/bin/bash
#

# create backup dir
sudo mkdir -p /root/backup/chef

sudo rpm -q chef-server
if [[ "$?" != "0" ]]; then
sudo rpm -Uvh $CHEF_SRV
if [[ "$?" != "0" ]]; then
    echo "failed to rpm install $CHEF_SRV"
    exit 1
fi
else
    echo "chef-server has already installed"
fi

# configure chef-server
sudo chef-server-ctl cleanse
mkdir -p /etc/chef-server
sudo cp -rn /etc/chef-server/chef-server.rb /root/backup/chef/
sudo rm -f /etc/chef-server/chef-server.rb
sudo cp -rf $COMPASSDIR/misc/chef-server/chef-server.rb /etc/chef-server/chef-server.rb
sudo chmod 644 /etc/chef-server/chef-server.rb
sudo chef-server-ctl reconfigure
sudo chef-server-ctl test
if [[ "$?" != "0" ]]; then
    echo "chef-server-ctl test failed"
    exit 1
fi

# configure chef client and knife
rpm -q chef
if [[ "$?" != "0" ]]; then
sudo wget -c --progress=bar:force -O /tmp/chef_install.sh http://www.opscode.com/chef/install.sh
if [[ "$?" != "0" ]]; then
    echo "failed to download chef install script"
    exit 1
else
    echo "chef install script is downloaded"
fi
sudo chmod 755 /tmp/chef_install.sh
sudo /tmp/chef_install.sh
if [[ "$?" != "0" ]]; then
    echo "chef install failed"
    exit 1
else
    echo "chef is installed"
fi
else
echo "chef has already installed"
fi

sudo mkdir -p ~/.chef

sudo knife configure -y -i --defaults -r ~/chef-repo -s https://localhost:443 -u $USER --admin-client-name admin --admin-client-key /etc/chef-server/admin.pem --validation-client-name chef-validator --validation-key /etc/chef-server/chef-validator.pem <<EOF
$CHEF_PASSWORD
EOF
sudo sed -i "/node_name/c\node_name                \'admin\'" /$USER/.chef/knife.rb
sudo sed -i "/client_key/c\client_key               \'\/etc\/chef-server\/admin.pem\'" /$USER/.chef/knife.rb
