echo "#!/bin/bash" > /target/etc/chef/rerun.sh; \
echo "echo \"rerun chef-client on \`date\`\" &>> /tmp/chef.log" >> /target/etc/chef/rerun.sh; \
echo "clients=\\$(pgrep chef-client)" >> /target/etc/chef/rerun.sh; \
echo "if [ \"\\$?\" == \"0\" ]; then" >> /target/etc/chef/rerun.sh; \
echo "    echo \"there are chef-clients '\\$clients' running\" &>> /tmp/chef.log" >> /target/etc/chef/rerun.sh; \
echo "    exit 1" >> /target/etc/chef/rerun.sh; \
echo "fi" >> /target/etc/chef/rerun.sh; \
echo "chef-client &>> /tmp/chef.log" >> /target/etc/chef/rerun.sh; \
echo "if [ \"\\$?\" != \"0\" ]; then" >> /target/etc/chef/rerun.sh; \
echo "    echo \"chef-client run failed\"  &>> /tmp/chef.log" >> /target/etc/chef/rerun.sh; \
echo "else" >> /target/etc/chef/rerun.sh; \
echo "    echo \"chef-client run success\" &>> /tmp/chef.log" >> /target/etc/chef/rerun.sh; \
echo "fi" >> /target/etc/chef/rerun.sh; \
chmod +x /target/etc/chef/rerun.sh; \
