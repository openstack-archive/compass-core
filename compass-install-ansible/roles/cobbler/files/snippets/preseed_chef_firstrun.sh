echo "#!/bin/bash" > /target/etc/chef/firstrun.sh; \
echo "touch /tmp/chef.log" >> /target/etc/chef/firstrun.sh; \
echo "while true; do" >> /target/etc/chef/firstrun.sh; \
echo "  echo \"firstrun.sh chef-client on \`date\`\" &>> /tmp/chef.log" >> /target/etc/chef/firstrun.sh; \
echo "  clients=\\$(pgrep chef-client)" >> /target/etc/chef/firstrun.sh; \
echo "  if [ \"\\$?\" == \"0\" ]; then" >> /target/etc/chef/firstrun.sh; \
echo "      echo \"there are chef-clients '\\$clients' running\" &>> /tmp/chef.log" >> /target/etc/chef/firstrun.sh; \
echo "      sleep 1m" >> /target/etc/chef/firstrun.sh; \
echo "  else" >> /target/etc/chef/firstrun.sh; \
echo "      chef-client -L /var/log/chef-client.log &>> /tmp/chef.log" >> /target/etc/chef/firstrun.sh; \
echo "      if [ \"\\$?\" != \"0\" ]; then" >> /target/etc/chef/firstrun.sh; \
echo "          echo \"chef-client run failed\"  &>> /tmp/chef.log" >> /target/etc/chef/firstrun.sh; \
echo "          sleep 1m" >> /target/etc/chef/firstrun.sh; \
echo "      else" >> /target/etc/chef/firstrun.sh; \
echo "          echo \"chef-client run success\" &>> /tmp/chef.log" >> /target/etc/chef/firstrun.sh; \
echo "          break" >> /target/etc/chef/firstrun.sh; \
echo "      fi" >> /target/etc/chef/firstrun.sh; \
echo "  fi" >> /target/etc/chef/firstrun.sh; \
echo "done" >> /target/etc/chef/firstrun.sh; \
chmod +x /target/etc/chef/firstrun.sh; \
