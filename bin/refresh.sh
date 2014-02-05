#!/bin/bash
/opt/compass/bin/manage_db.py checkdb
if [[ "$?" == "0" ]]; then
/opt/compass/bin/manage_db.py clean_clusters
fi
/opt/compass/bin/manage_db.py createdb
/opt/compass/bin/manage_db.py sync_switch_configs 
/opt/compass/bin/manage_db.py sync_from_installers
service compassd restart
service httpd restart
service rsyslog restart
