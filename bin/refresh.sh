#!/bin/bash
/opt/compass/bin/manage_db.py checkdb
if [[ "$?" == "0" ]]; then
/opt/compass/bin/manage_db.py clean_clusters
fi
/opt/compass/bin/manage_db.py dropdb &> /dev/null
/opt/compass/bin/manage_db.py createdb
/opt/compass/bin/manage_db.py sync_switch_configs 
/opt/compass/bin/manage_db.py sync_from_installers
service httpd restart
service rsyslog restart
service redis restart
redis-cli flushall
service mysqld restart
service compassd restart

