#!/bin/bash

knife configure -y -i --defaults -r ~/chef-repo -s https://localhost:443 -u root --admin-client-name admin --admin-client-key /etc/chef-server/admin.pem --validation-client-name chef-validator --validation-key /etc/chef-server/chef-validator.pem <<EOF
'randomphrase'
EOF
