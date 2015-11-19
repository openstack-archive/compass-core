# Verify the Identity Service installation
export OS_PASSWORD={{ ADMIN_PASS }}
export OS_TENANT_NAME=admin
export OS_AUTH_URL=http://{{ internal_vip.ip }}:35357/v2.0
export OS_USERNAME=ADMIN

