#!/bin/bash
set -e
service mysqld restart
/opt/compass/bin/manage_db.py createdb
/opt/compass/bin/clean_installers.py --noasync
/opt/compass/bin/clean_installation_logs.py
rm -rf /var/ansible/run/*
service httpd restart
service rsyslog restart
service redis restart
sleep 10
redis-cli flushall
service cobblerd restart
chef-server-ctl restart
service compass-celeryd restart
service compass-progress-updated restart

