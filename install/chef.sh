#!/bin/bash
#

# create backup dir
sudo mkdir -p /root/backup/chef

sudo rpm -q chef-server
if [[ "$?" != "0" ]]; then
    download $CHEF_SRV chef-server install || exit $?
else
    echo "chef-server has already installed"
fi

# configure chef-server
sudo rm -rf ~/chef-server-cleanse-*
sudo chef-server-ctl cleanse
sudo mkdir -p /etc/chef-server
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

if [[ -e /var/chef ]]; then
    sudo rm -rf /var/chef
fi
sudo mkdir -p /var/chef/cookbooks/
sudo cp -r $ADAPTERS_HOME/chef/cookbooks/* /var/chef/cookbooks/
if [ $? -ne 0 ]; then
    echo "failed to copy cookbooks to /var/chef/cookbooks/"
    exit 1
fi
sudo mkdir -p /var/chef/databags/
sudo cp -r $ADAPTERS_HOME/chef/databags/* /var/chef/databags/
if [ $? -ne 0 ]; then
    echo "failed to copy databags to /var/chef/databags/"
    exit 1
fi
sudo mkdir -p /var/chef/roles/
sudo cp -r $ADAPTERS_HOME/chef/roles/* /var/chef/roles/
if [ $? -ne 0 ]; then
    echo "failed to copy roles to /var/chef/roles/"
    exit 1
fi

# configure chef client and knife
rpm -q chef
if [[ "$?" != "0" ]]; then
    download $CHEF_CLIENT `basename $CHEF_CLIENT` install || exit $?
else
    echo "chef has already installed"
fi

sudo mkdir -p ~/.chef

sudo knife configure -y -i --defaults -r ~/chef-repo -s https://localhost:443 -u $USER --admin-client-name admin --admin-client-key /etc/chef-server/admin.pem --validation-client-name chef-validator --validation-key /etc/chef-server/chef-validator.pem <<EOF
$CHEF_PASSWORD
EOF
sudo sed -i "/node_name/c\node_name                \'admin\'" /$USER/.chef/knife.rb
sudo sed -i "/client_key/c\client_key               \'\/etc\/chef-server\/admin.pem\'" /$USER/.chef/knife.rb
