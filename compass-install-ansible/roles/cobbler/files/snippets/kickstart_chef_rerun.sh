cat << EOF > /etc/chef/rerun.sh
#raw
#!/bin/bash
echo "rerun chef-client on \`date\`" &>> /tmp/chef.log
clients=\$(pgrep chef-client)
if [ "\$?" == "0" ]; then
    echo "there are chef-clients '\$clients' running" &>> /tmp/chef.log
    exit 1
fi
chef-client &>> /tmp/chef.log
if [ "\$?" != "0" ]; then
    echo "chef-client run failed"  &>> /tmp/chef.log
else
    echo "chef-client run success" &>> /tmp/chef.log
fi
#end raw
EOF
chmod +x /etc/chef/rerun.sh

