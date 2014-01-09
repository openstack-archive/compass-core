#!bin/bash

##export ipaddr=$(ifconfig $NIC | grep 'inet addr:' | cut -d: -f2 | awk '{ print $1}')
echo "$ipaddr    $HOSTNAME" >> /etc/hosts
sudo rpm -Uvh $CHEF_SRV

# configure rsyslog
cp /etc/rsyslog.conf /root/backup/
# update rsyslog.conf
sudo sed -i '
/#### GLOBAL DIRECTIVES ####/ i\
\$WorkDirectory /var/lib/rsyslog\
\
\# Added for chef logfiles\
\$template Chef_log,"/var/log/cobbler/anamon/%hostname%/chef-client.log"\
\$template Raw, "%rawmsg%"\
' /etc/rsyslog.conf
sudo sed -i '
/# ### begin forwarding rule ###/ i\
local3.*        -?Chef_log\
' /etc/rsyslog.conf
sudo sed -i 's/^#$ModLoad[ \t]\+imtcp/$ModLoad imtcp/g' /etc/rsyslog.conf
sudo sed -i '/$InputTCPServerRun/c\$InputTCPServerRun 514' /etc/rsyslog.conf
sudo service rsyslog restart

# configure chef-server
sudo mkdir /root/backup/chef-server
sudo cp /opt/chef-server/embedded/conf/nginx.conf /root/backup/chef-server/
sudo sed -i 's/listen\([ \t]\+\)80;/listen\18080;/g' /opt/chef-server/embedded/conf/nginx.conf
sudo chef-server-ctl reconfigure
sudo cp /var/opt/chef-server/nginx/etc/nginx.conf /root/backup/chef-server/etc-nginx.conf
sudo sed -i 's/listen\([ \t]\+\)80;/listen\18080;/g' /var/opt/chef-server/nginx/etc/nginx.conf
sudo chef-server-ctl restart
sudo chef-server-ctl test

# configure chef client and knife
sudo curl -L http://www.opscode.com/chef/install.sh | sudo bash

sudo mkdir ~/.chef

sudo knife configure -y -i --defaults -r ~/chef-repo -s https://localhost:443 -u $USER --admin-client-name admin --admin-client-key /etc/chef-server/admin.pem --validation-client-name chef-validator --validation-key /etc/chef-server/chef-validator.pem <<EOF
root1234
EOF
sudo sed -i "/node_name/c\node_name                \'admin\'" /$USER/.chef/knife.rb
sudo sed -i "/client_key/c\client_key               \'\/etc\/chef-server\/admin.pem\'" /$USER/.chef/knife.rb
