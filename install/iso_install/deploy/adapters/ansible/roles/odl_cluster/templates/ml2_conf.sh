cat <<EOT>> /etc/neutron/plugins/ml2/ml2_conf.ini
[ml2_odl]
password = admin
username = admin
url = http://{{ internal_vip.ip }}:8080/controller/nb/v2/neutron
EOT
