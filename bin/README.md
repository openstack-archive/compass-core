Compass Binaries and  Scripts
=============================

bin/ contains compass heavy-lifting utility scripts and binaries. These scripts are often called by different components. Some are from core python modules and some are from compass daemon and other services. Most files in `bin/` are placed under `/opt/compass/bin/` after install.sh is complete. Some of them will go to `/usr/bin/` or `/etc/init.d/` as system binaries or services.

###Directories and Files

Below is a walkthrough of all directories and files.

    * ansible-callbacks/  - contains callback scripts for ansible installer.
            * playbook_done.py - triggered by ansible when all playbooks are successfully executed.
                                Then the script will call compass API to report ansible "complete" status.
    * chef/   - utility scripts for chef installer.
            * addcookbooks.py - upload all chef cookbooks to the chef server.
            * adddatabags.py - (deprecated) upload all chef databags to the chef server.
            * addroles.py - upload all chef roles to the chef server.
            * clean_clients.sh - remove all chef clients on the chef server.
            * clean_environments.sh - remove all chef environments on the chef server.
            * clean_nodes.sh - remove all chef nodes on the chef server.
    * cobbler/  - utility scripts for cobbler installer
            * remove_systems.sh - remove all systems on the cobbler server.
    * clean_installation_logs.py - remove all the installation logs.
    * clean_installers.py - remove all configurations and data from all installers.
    * client.sh - sample client script to call client.py
    * client.py - compass python client that calls API and deploy a cluster based on given configurations.
    * compass_check.py - binary file that is placed as /usr/bin/compass. This is the main entrance of compass check CLI.
    * compassd - (deprecated) old compass daemon file
    * compass_wsgi.py - compass wsgi module.
    * csvdeploy.py - script that enable the deployment of clusters from spreadsheets.
    * delete_clusters.py - script that deletes all given clusters and their underlying hosts.
    * manage_db.py - utility binary that manages database.
    * poll_switch.py - utility script to poll machine mac addresses that are connected to certain switches.
    * progress_update.py - main script to run as a service to update hosts installing progresses.
    * query_switch.py - independent script to query a switch.
    * refresh.sh - refresh compass-db, restart compass services and clean up all installers.
    * runserver.py - manually run a compass server instance.
    * switch_virtualenv.py.template - template of switch_virtualenv.py. This script enables switching between python
                                      virtual environments.
                                      
###Script Location and Calling Modules
Script name | Location | Called by
--- | --- | ---
ansible-callbacks/playbook_done.py | /opt/compass/bin/ansible-callbacks/playbookd_done.py | ***ansible-playbook***
chef/addcookbooks.py | /opt/compass/bin/addcookbooks.py | ***install/chef.sh***
chef/adddatabags.py(deprecated) | /opt/compass/bin/addcookbooks.py | None
chef/addroles.py | /opt/compass/bin/addroles.py | ***install/chef.sh***
chef/clean_clients.sh | /opt/compass/bin/clean_clients.sh | ***compass.tasks.clean_package_installer***
chef/clean_environments.sh | /opt/compass/bin/clean_environments.sh | ***compass.tasks.clean_package_installer***
chef/clean_nodes.sh | /opt/compass/bin/clean_nodes.sh | ***compass.tasks.clean_package_installer***
cobbler/remove_systems.sh | /opt/compass/bin/remove_systems.sh | ***compass.tasks.clean_os_installer***
clean_installation_logs.py | /opt/compass/bin/clean_installation_logs.py | ***bin/refresh.sh***
clean_installers.py | /opt/compass/bin/clean_installers.py | ***bin/refresh.sh***
client.sh | /opt/compass/bin/client.sh | sample client
client.py | /opt/compass/bin/client.py | ***regtest/regtest.sh***
compsas_check.py | /opt/compass/bin/compass_check.py | ***compass check cli***
compassd(deprecated) | None | None
compass_wsgi.py | /var/www/compass/compass.wsgi | ***Apache daemon***
csvdeploy.py | /opt/compass/bin/csvdeploy.py | command-line script
delete_clusters.py | /opt/compass/bin/delete_clusters.py | command-line script
manage_db.py | /opt/compass/bin/manage_db.py | ***install/compass.sh*** and command-line script
poll_switch.py | /opt/compass/bin/poll_switch.py | command-line script
progress_update.py | /opt/compass/bin/progress_update.py | ***compass-progress-updated daemon***
query_switch.py | /opt/compass/bin/query_switch.py | command-line script
refresh.sh | /opt/compass/bin/refresh.sh | command-line script
runserver.py | /opt/compass/bin/runserver.py | command-line script
switch_virtualenv.py.template | /opt/compass/bin/switch_virtualenv.py | ***all scripts using this library***
