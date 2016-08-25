#!/bin/bash
#
#set -x
### Register current user to compass
USER_EMAIL="aaa@huawei.com"
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
echo "The email address you use to register is ${USER_EMAIL}"
password=`< /dev/urandom tr -dc _A-Z-a-z-0-9 | head -c6`
data=`echo "{\"email\":\"${USER_EMAIL}\",\"password\":\"${password}\"}"`
wget -O /tmp/user_info --post-data=$data --header=Content-Type:application/json "http://www.stack360.io/api/users/register"
wget -O /tmp/aws_credentials "http://www.stack360.io/aws_credentials"
filename='/tmp/aws_credentials'
id=$(sed -n '1p' < $filename)
key=$(sed -n '2p' < $filename)
sudo sed -i "s~ACCESS_ID~$id~g" /etc/compass/celeryconfig
sudo sed -i "s~ACCESS_KEY~$key~g" /etc/compass/celeryconfig

if [ $? -ne 0 ]; then
echo "Register failed"
exit 1
fi

echo "Register suceeded, your password is $password, please remember your password at all times."
sudo sed -i 's/^CELERY_DEFAULT_QUEUE.*/CELERY_DEFAULT_QUEUE = \"'"${USER_EMAIL}"'\"/g' /etc/compass/celeryconfig
sudo sed -i 's/^CELERY_DEFAULT_EXCHANGE.*/CELERY_DEFAULT_EXCHANGE = \"'"${USER_EMAIL}"'\"/g' /etc/compass/celeryconfig
sudo sed -i 's/^CELERY_DEFAULT_ROUTING_KEY.*/CELERY_DEFAULT_ROUTING_KEY = \"'"${USER_EMAIL}"'\"/g' /etc/compass/celeryconfig
