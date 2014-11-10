#!/bin/bash
#

echo "Installing chef"
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
source $DIR/install.conf
if [ -f $DIR/env.conf ]; then
    source $DIR/env.conf
else
    echo "failed to load environment"
    exit 1
fi
source $DIR/install_func.sh

echo "Installing chef related packages"

# create backup dir
sudo mkdir -p /root/backup/chef

sudo rpm -q chef-server
if [[ "$?" != "0" ]]; then
    download $CHEF_SRV chef-server install || exit $?
else
    echo "chef-server has already installed"
fi


echo "reconfigure chef server"
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
fi

echo "configure chef client and knife"
# configure chef client and knife
rpm -q chef
if [[ "$?" != "0" ]]; then
    download $CHEF_CLIENT `basename $CHEF_CLIENT` install || exit $?
else
    echo "chef has already installed"
fi

sudo mkdir -p ~/.chef

sudo knife configure -y -i --defaults -r ~/chef-repo -s https://$IPADDR:443 -u $USER --admin-client-name admin --admin-client-key /etc/chef-server/admin.pem --validation-client-name chef-validator --validation-key /etc/chef-server/chef-validator.pem <<EOF
$CHEF_PASSWORD
EOF
sudo sed -i "/node_name/c\node_name                \'admin\'" /$USER/.chef/knife.rb
sudo sed -i "/client_key/c\client_key               \'\/etc\/chef-server\/admin.pem\'" /$USER/.chef/knife.rb


sudo rm -rf /var/chef
sudo mkdir -p /var/chef/cookbooks/
sudo cp -r $ADAPTERS_HOME/chef/cookbooks/* /var/chef/cookbooks/
if [ $? -ne 0 ]; then
    echo "failed to copy cookbooks to /var/chef/cookbooks/"
    exit 1
fi
sudo mkdir -p /var/chef/roles/
sudo cp -r $ADAPTERS_HOME/chef/roles/* /var/chef/roles/
if [ $? -ne 0 ]; then
    echo "failed to copy roles to /var/chef/roles/"
    exit 1
fi

knife cookbook upload --all --cookbook-path /var/chef/cookbooks
if [[ "$?" != "0" ]]; then
    echo "failed to add cookbooks"
    exit 1
else
    echo "cookbooks are added to chef server"
fi

knife role from file /var/chef/roles/*.json
if [[ "$?" != "0" ]]; then
    echo "failed to add roles"
    exit 1
else
    echo "roles are added to chef server"
fi
