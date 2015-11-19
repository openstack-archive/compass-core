cat << EOL > /etc/chef/client.rb
log_level        :info
log_location     '/dev/null'
#if $getVar('chef_url', '') != ""
chef_server_url  '$chef_url'
#elif $getVar("compass_server","") != ""
chef_server_url  'https://$compass_server'
#else
chef_server_url  'https://$server'
#end if
validation_client_name 'chef-validator'
json_attribs nil
pid_file '/var/run/chef-client.pid'
# Using default node name (fqdn)
no_lazy_load true
ssl_verify_mode :verify_none
EOL

mkdir -p /etc/chef/trusted_certs
#set certs_path = $getVar("trusted_certs_path", "/var/opt/chef-server/nginx/ca")
#if $certs_path != ""
    #import os
    #import os.path
    #set filenames = $os.listdir($certs_path)
    #for filename in $filenames
        #if $filename.endswith('.crt')
            #set filepath = $os.path.join($certs_path, $filename)
            #set f = $open($filepath)
cat << EOF > /etc/chef/trusted_certs/$filename
            #echo $f.read()
EOF
            #silent $f.close()
        #end if
    #end for
#end if
