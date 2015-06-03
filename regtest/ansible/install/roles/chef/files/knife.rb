log_level                :info
log_location             STDOUT
node_name                'admin'
client_key               '/etc/chef-server/admin.pem'
validation_client_name   'chef-validator'
validation_key           '/etc/chef-server/chef-validator.pem'
chef_server_url          'https://localhost:443'
syntax_check_cache_path  '/root/.chef/syntax_check_cache'
cookbook_path [ '/root/chef-repo/cookbooks' ]
