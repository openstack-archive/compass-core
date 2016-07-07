#!/bin/bash
#
#set -x
### Register current user to compass

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
source $DIR/install.conf
echo "The email address you use to register is ${USER_EMAIL}"
password=`< /dev/urandom tr -dc _A-Z-a-z-0-9 | head -c6`
data=`echo "{\"email\":\"${USER_EMAIL}\",\"password\":\"${password}\"}"`
wget -O /tmp/user_info --post-data=$data --header=Content-Type:application/json "http://www.stack360.io/api/users/register"

if [ $? -ne 0 ]; then
echo "Register failed"
exit 1
fi

echo "Register suceeded, your password is $password, please remember your password at all times."
sed -i 's/^CELERY_DEFAULT_QUEUE.*/CELERY_DEFAULT_QUEUE = \"'"${USER_EMAIL}"'\"/g' /etc/compass/celeryconfig
sed -i 's/^CELERY_DEFAULT_EXCHANGE.*/CELERY_DEFAULT_EXCHANGE = \"'"${USER_EMAIL}"'\"/g' /etc/compass/celeryconfig
sed -i 's/^CELERY_DEFAULT_ROUTING_KEY.*/CELERY_DEFAULT_ROUTING_KEY = \"'"${USER_EMAIL}"'\"/g' /etc/compass/celeryconfig

systemctl restart compass-celeryd.service
