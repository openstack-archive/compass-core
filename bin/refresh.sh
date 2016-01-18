#!/bin/bash
set -e
which systemctl
if [[ "$?" == "0" ]]; then
service mysqld restart
service mysqld status || exit $?
else
systemctl restart mysql.service
systemctl status mysql.service || exit $?
fi
/opt/compass/bin/manage_db.py createdb
/opt/compass/bin/clean_installers.py --noasync
/opt/compass/bin/clean_installation_logs.py
rm -rf /var/ansible/run/*
which systemctl
if [[ "$?" == "0" ]]; then
service httpd restart
service httpd status || exit $?
service rsyslog restart
service rsyslog status || exit $?
service redis restart
service redis status || exit $?
else
systemctl restart httpd.service
systemctl status httpd.service || exit $?
systemctl restart rsyslog.service
systemctl status rsyslog.service || exit $?
systemctl restart redis.service
systemctl status  redis.service || exit $?
fi
redis-cli flushall
which systemctl
if [[ "$?" == "0" ]]; then
service cobblerd restart
service cobblerd status || exit $?
service compass-celeryd restart
service compass-celeryd status || exit $?
service compass-progress-updated restart
service compass-progress-updated status || exit $?
else
systemctl restart cobblerd.service
systemctl status cobblerd.service || exit $?
systemctl restart compass-celeryd.service
systemctl status compass-celeryd.service || exit $?
systemctl restart compass-progress-updated.service
systemctl status compass-progress-updated.service || exit $?
fi
