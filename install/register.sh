#!/bin/bash
#
#set -x
### Register current user to compass
source install.conf
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
echo "The email address you use to register is ${USER_EMAIL}"
password=`< /dev/urandom tr -dc _A-Z-a-z-0-9 | head -c6`
USER_PASSWORD="${USER_PASSWORD:-$password}"
data=`echo "{\"email\":\"${USER_EMAIL}\",\"password\":\"${USER_PASSWORD}\"}"`
COMPASS_API_SERVER="c.stack360.io"
if [ "$FULL_COMPASS_SERVER" == "true" ]; then
    COMPASS_API_SERVER="127.0.0.1"
fi
wget -O /tmp/user_info --post-data=$data --header=Content-Type:application/json "http://$COMPASS_API_SERVER/api/users/register"
if [ $? -ne 0 ]; then
echo "Register failed"
exit 1
fi

echo "Register suceeded, your password is $USER_PASSWORD, please remember your password at all times."
sudo sed -i 's/^CELERY_DEFAULT_QUEUE.*/CELERY_DEFAULT_QUEUE = \"'"${USER_EMAIL}"'\"/g' /etc/compass/celeryconfig
sudo sed -i 's/^CELERY_DEFAULT_EXCHANGE.*/CELERY_DEFAULT_EXCHANGE = \"'"${USER_EMAIL}"'\"/g' /etc/compass/celeryconfig
sudo sed -i 's/^CELERY_DEFAULT_ROUTING_KEY.*/CELERY_DEFAULT_ROUTING_KEY = \"'"${USER_EMAIL}"'\"/g' /etc/compass/celeryconfig

systemctl restart compass-celeryd.service
