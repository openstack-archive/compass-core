#!/bin/bash
set -e
/opt/compass/bin/manage_db.py createdb
service httpd restart
service rsyslog restart
service redis restart
redis-cli flushall
service compass-celeryd restart
service compass-progress-updated restart

