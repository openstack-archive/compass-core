# See http://docs.opscode.com/config_rb_knife.html for more information on knife configuration options
# The files will be placed in the same directory.
# The files will be placed in ~/.chef/

current_dir = File.dirname(__FILE__)
log_level                :info
log_location             STDOUT
node_name                "compassdocker"
client_key               "#{current_dir}/compassdocker.pem"
validation_client_name   "chef-validator"
validation_key           "#{current_dir}/chef-validator.pem"
chef_server_url          "https://192.168.100.35:443"
cache_type               'BasicFile'
cache_options( :path => "#{ENV['HOME']}/.chef/checksums" )
#cookbook_path            ["#{current_dir}/../cookbooks"]

