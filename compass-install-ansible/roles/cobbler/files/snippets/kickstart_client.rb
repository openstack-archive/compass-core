cat << EOL > /etc/chef/client.rb
log_level        :info
log_location     '/dev/null'
#if $getVar('chef_url', '') != ""
chef_server_url  '$chef_url'
#end if
#if $getVar('proxy', '') != "" 
http_proxy       '$proxy'
https_proxy      '$proxy'
ENV['http_proxy'] = '$proxy'
ENV['https_proxy'] = '$proxy'
ENV['HTTP_PROXY'] = '$proxy'
ENV['HTTPS_PROXY'] = '$proxy'
#end if
#if $getVar('ignore_proxy', '') != ""
no_proxy         '$ignore_proxy'
ENV['no_proxy'] = '$ignore_proxy'
ENV['NO_PROXY'] = '$ignore_proxy'
#end if
#if $getVar('chef_node_name', '') != ""
node_name        '$chef_node_name'
#end if
validation_client_name 'chef-validator'
json_attribs nil
pid_file '/var/run/chef-client.pid'
# Using default node name (fqdn) 
no_lazy_load true
EOL
