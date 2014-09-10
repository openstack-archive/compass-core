#!/bin/bash
set -e
service mysqld restart
/opt/compass/bin/manage_db.py createdb
echo "You may run '/opt/compass/bin/clean_nodes.sh' to clean nodes on chef server"
echo "You may run '/opt/compass/bin/clean_clients.sh' to clean clients on chef server"
echo "you may run '/opt/compass/bin/clean_environments.sh' to clean environments on chef server"
echo "you may run '/opt/compass/bin/remove_systems.sh' to clean systems on cobbler"
/opt/compass/bin/clean_installation_logs.py
service httpd restart
service rsyslog restart
service redis restart
sleep 10
redis-cli flushall
service compass-celeryd restart
service compass-progress-updated restart

