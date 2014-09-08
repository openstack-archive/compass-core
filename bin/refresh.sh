#!/bin/bash
set -e
service mysqld restart
/opt/compass/bin/manage_db.py createdb
/opt/compass/bin/clean_nodes.sh
/opt/compass/bin/clean_clients.sh
/opt/compass/bin/clean_environments.sh
/opt/compass/bin/remove_systems.sh
/opt/compass/bin/clean_installation_logs.py
service httpd restart
service rsyslog restart
service redis restart
sleep 10
redis-cli flushall
service compass-celeryd restart
service compass-progress-updated restart

