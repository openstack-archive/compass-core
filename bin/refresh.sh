#!/bin/bash
set -e
service mysqld restart
service mysqld status || exit $?
/opt/compass/bin/manage_db.py createdb
/opt/compass/bin/clean_installers.py --noasync
/opt/compass/bin/clean_installation_logs.py
rm -rf /var/ansible/run/*
service httpd restart
sleep 10
service httpd status || exit $?
service rsyslog restart
sleep 10
service rsyslog status || exit $?
service redis restart
sleep 10
service redis status || exit $?
redis-cli flushall
service cobblerd restart
sleep 10
service cobblerd status || exit $?
chef-server-ctl restart
sleep 10
chef-server-ctl status || exit $?
service compass-celeryd restart
sleep 10
service compass-celeryd status || exit $?
service compass-progress-updated restart
sleep 10
service compass-progress-updated status || exit $?

