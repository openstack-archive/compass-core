echo "log_level        :info" > /target/etc/chef/client.rb; \
echo "log_location     '/dev/null'" >> /target/etc/chef/client.rb; \
#if $getVar('chef_url', '') != ""
echo "chef_server_url  '$chef_url'" >> /target/etc/chef/client.rb; \
#end if
#if $getVar('proxy', '') != "" 
echo "http_proxy       '$proxy'" >> /target/etc/chef/client.rb; \
echo "https_proxy      '$proxy'" >> /target/etc/chef/client.rb; \
echo "ENV['http_proxy'] = '$proxy'" >> /target/etc/chef/client.rb; \
echo "ENV['https_proxy'] = '$proxy'" >> /target/etc/chef/client.rb; \
echo "ENV['HTTP_PROXY'] = '$proxy'" >> /target/etc/chef/client.rb; \
echo "ENV['HTTPS_PROXY'] = '$proxy'" >> /target/etc/chef/client.rb; \
#end if
#if $getVar('ignore_proxy', '') != ""
echo "no_proxy         '$ignore_proxy'" >> /target/etc/chef/client.rb; \
echo "ENV['no_proxy'] = '$ignore_proxy'" >> /target/etc/chef/client.rb; \
echo "ENV['NO_PROXY'] = '$ignore_proxy'" >> /target/etc/chef/client.rb; \
#end if
#if $getVar('chef_node_name', '') != ""
echo "node_name        '$chef_node_name'" >> /target/etc/chef/client.rb; \
#end if
echo "validation_client_name 'chef-validator'" >> /target/etc/chef/client.rb; \
echo "json_attribs nil" >> /target/etc/chef/client.rb; \
echo "pid_file '/var/run/chef-client.pid'" >> /target/etc/chef/client.rb; \
echo "# Using default node name (fqdn)" >> /target/etc/chef/client.rb; \
echo "no_lazy_load true" >> /target/etc/chef/client.rb; \
