#!/bin/bash
set -e
service mysqld restart
service mysqld status || exit $?
/opt/compass/bin/manage_db.py createdb
/opt/compass/bin/clean_installers.py --noasync
/opt/compass/bin/clean_installation_logs.py
rm -rf /var/ansible/run/*
service httpd restart
service httpd status || exit $?
service rsyslog restart
service rsyslog status || exit $?
service redis restart
service redis status || exit $?
redis-cli flushall
service cobblerd restart
service cobblerd status || exit $?
service compass-celeryd restart
service compass-celeryd status || exit $?
service compass-progress-updated restart
service compass-progress-updated status || exit $?

