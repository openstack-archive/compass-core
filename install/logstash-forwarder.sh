#!/bin/bash
#

echo "Installing logstash-forwarder"
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
source $DIR/install.conf

sudo cp -rf $COMPASSDIR/misc/logstash-forwarder/logstash-forwarder.repo /etc/yum.repos.d/logstash-forwarder.repo
sudo yum -y install logstash-forwarder
sudo rm -rf /etc/logstash-forwarder.conf
sudo cp -rf $COMPASSDIR/misc/logstash-forwarder/logstash-forwarder.conf /etc/logstash-forwarder.conf
sudo mkdir -p /etc/pki/tls/certs
sudo cp -rf $COMPASSDIR/misc/logstash-forwarder/logstash-forwarder.crt /etc/pki/tls/certs/logstash-forwarder.crt

sudo systemctl restart logstash-forwarder.service
sleep 3
echo "checking if logstash-forwarder is running"
sudo systemctl status logstash-forwarder.service
if [[ "$?" != 0 ]]; then
    echo "logstash-forwarder is not running"
    exit
fi
