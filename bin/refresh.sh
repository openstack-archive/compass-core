#!/bin/bash
let initial_run=0
while [ $# -gt 0 ]; do
    case "$1" in
        -i|--init) let initial_run=1; shift ;;
        *) shift ;;
    esac
done
if [ $initial_run -eq 0 ]; then
/opt/compass/bin/manage_db.py clean_clusters
fi
/opt/compass/bin/manage_db.py createdb
/opt/compass/bin/manage_db.py sync_from_installers
service compassd restart
service httpd restart
service rsyslog restart
