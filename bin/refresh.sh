#!/bin/bash
set -e
# systemctl restart mysql.service
# systemctl status mysql.service || exit $?
# /opt/compass/bin/manage_db.py createdb
/opt/compass/bin/clean_installers.py --noasync
/opt/compass/bin/clean_installation_logs.py
rm -rf /var/ansible/run/*
# systemctl restart httpd.service
# systemctl status httpd.service || exit $?
systemctl restart rsyslog.service
systemctl status rsyslog.service || exit $?
systemctl restart redis.service
systemctl status  redis.service || exit $?
redis-cli flushall
systemctl restart cobblerd.service
systemctl status cobblerd.service || exit $?
systemctl restart compass-celeryd.service
systemctl status compass-celeryd.service || exit $?
# systemctl restart compass-progress-updated.service
# systemctl status compass-progress-updated.service || exit $?

