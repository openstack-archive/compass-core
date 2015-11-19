sleep 10
glance --os-username=admin --os-password={{ ADMIN_PASS }} --os-tenant-name=admin --os-auth-url=http://{{ internal_vip.ip }}:35357/v2.0 image-create --name="cirros" --disk-format=qcow2 --container-format=bare --is-public=true < /opt/{{ build_in_image_name }} && touch glance.import.completed
