cat <<EOT>> /etc/neutron/plugins/ml2/ml2_conf.ini
[ml2_onos]
password = admin
username = admin
url_path = http://{{ ip_settings[groups['onos'][0]]['mgmt']['ip'] }}:8181/onos/vtn
EOT

