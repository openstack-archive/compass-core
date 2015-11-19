#set ip_address = ""
#set ikeys = $interfaces.keys()
#for $iname in $ikeys
    #set $idata = $interfaces[$iname]
    #set $static        = $idata["static"]
    #set $management    = $idata["management"]
    #set $ip            = $idata["ip_address"]
    #if $management and $ip
        #set $ip_address = $ip
    #end if
#end for

#set $proxy_url = ""
#set $local_repo_url = ""
#if $getVar("local_repo","") != ""
    #set $local_repo_url = $local_repo
#end if
#if $getVar("proxy","") != ""
    #set $proxy_url = $proxy
#end if

#if $getVar('compass_server', '') != ""
    #set srv = $getVar('compass_server','')
#else
    #set srv = $getVar('server','')
#end if

cat << EOF > /etc/chef/chef_client_run.sh
#!/bin/bash
touch /var/log/chef.log
PIDFILE=/tmp/chef_client_run.pid
if [ -f \\$PIDFILE ]; then
    pid=\\$(cat \\$PIDFILE)
    if [ -f /proc/\\$pid/exe ]; then
        echo "there are chef_client_run.sh running with pid \\$pid" >> /var/log/chef.log 2>&1
        exit 1
    fi
fi
echo \\$$ > \\$PIDFILE
while true; do
    echo "run chef-client on \`date\`" >> /var/log/chef.log 2>&1
    clients=\\$(pgrep chef-client)
    if [[ "\\$?" == "0" ]]; then
        echo "there are chef-clients '\\$clients' running" >> /var/log/chef.log 2>&1
        break
    else
        echo "knife search nodes" >> /var/log/chef.log 2>&1
        USER=root HOME=/root knife node list |grep \\$HOSTNAME. >> /var/log/chef.log 2>&1
        nodes=\\$(USER=root HOME=/root knife node list |grep \\$HOSTNAME.)
        echo "found nodes \\$nodes" >> /var/log/chef.log 2>&1
        all_nodes_success=1
        for node in \\$nodes; do
            mkdir -p /var/log/chef/\\$node
            if [ ! -f /etc/chef/\\$node.json ]; then
                cat << EOL > /etc/chef/\\$node.json
{
    "local_repo": "$local_repo_url",
    "proxy_url": "$proxy_url",
    "ip_address": "$ip_address"
}
EOL
            fi
            if [ ! -f "/etc/chef/\\$node.pem" ]; then
                cat << EOL > /etc/rsyslog.d/\\$node.conf
\\\\$ModLoad imfile
\\\\$InputFileName /var/log/chef/\\$node/chef-client.log
\\\\$InputFileReadMode 0
\\\\$InputFileTag \\$node
\\\\$InputFileStateFile chef_\\${node}_log
\\\\$InputFileSeverity notice
\\\\$InputFileFacility local3
\\\\$InputRunFileMonitor
\\\\$InputFilePollInterval 1
#if $getVar("compass_server","") != ""
local3.info @$compass_server:514
#else
local3.info @@$server:514
#end if
EOL
                rm -rf /var/lib/rsyslog/chef_\\$node_log
                service rsyslog restart
            fi
            if [ -f "/etc/chef/\\$node.done" ]; then
                USER=root HOME=/root chef-client --node-name \\$node -j /etc/chef/\\$node.json --client_key /etc/chef/\\$node.pem >> /var/log/chef.log 2>&1
            else
                USER=root HOME=/root chef-client --node-name \\$node -j /etc/chef/\\$node.json --client_key /etc/chef/\\$node.pem -L /var/log/chef/\\$node/chef-client.log >> /var/log/chef.log 2>&1
            fi
            if [ "\\$?" != "0" ]; then
                echo "chef-client --node-name \\$node run failed"  >> /var/log/chef.log 2>&1
                all_nodes_success=0
            else
                echo "chef-client --node-name \\$node run success" >> /var/log/chef.log 2>&1
                touch /etc/chef/\\$node.done
                wget -O /tmp/package_state.\\$node --post-data='{"ready": true}' --header=Content-Type:application/json "http://$srv/api/clusterhosts/\\${node}/state_internal"
            fi
        done
        if [ \\$all_nodes_success -eq 0 ]; then
            sleep 1m
        else
            break
        fi
    fi
done
EOF
chmod +x /etc/chef/chef_client_run.sh
