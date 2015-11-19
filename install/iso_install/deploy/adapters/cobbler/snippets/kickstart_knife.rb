mkdir -p /root/.chef
cat << EOL > /root/.chef/knife.rb
log_level        :info
log_location     '/dev/null'
#if $getVar('chef_url', '') != ""
chef_server_url  '$chef_url'
#end if
node_name                'admin'
client_key               '/etc/chef/admin.pem'
validation_client_name   'chef-validator'
validation_key           '/etc/chef/validation.pem'
syntax_check_cache_path  '/root/.chef/syntax_check_cache'
ssl_verify_mode :verify_none
#if $os_version == "rhel7"
verify_api_cert false
#end if
EOL

mkdir -p /root/.chef/trusted_certs
#set certs_path = $getVar("trusted_certs_path", "/var/opt/chef-server/nginx/ca")
#if $certs_path != ""
    #import os
    #import os.path
    #set filenames = $os.listdir($certs_path)
    #for filename in $filenames
        #if $filename.endswith('.crt')
            #set filepath = $os.path.join($certs_path, $filename)
            #set f = $open($filepath)
cat << EOF > /root/.chef/trusted_certs/$filename
            #echo $f.read()
EOF
            #silent $f.close()
        #end if
    #end for
#end if
