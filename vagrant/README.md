# compass-vbox
vbox setup for compass

## how to use it

### requirements

* Ubuntu-14.04(12.04 not tested but should work)
* Virtualbox >= 4.3.18
* Oracle VM VirtualBox extension pack for 4.3.18r96516 to support pxeboot
* x86_64 CPU architechture
* Git installed

run:

```
./launch.sh
```

or 

```
./launch.sh --recreate
```

the "recreate" flag will destroy all configured vms and hostonly networks in VirtualBox.

After launch finishes, to access compass server:

```
vagrant ssh
```

To use compass-web UI, go to a browser and enter [http://192.168.33.10](http://192.168.33.10) in the address bar.

Please refer to [http://www.syscompass.org/user.html](http://www.syscompass.org/user.html) for instructions of Compass UI.

### Note:

* When "discover machines", use 127.0.0.1 as Switch IP. Use any values for *Version* and *Community*, leave *Filters* blank.

* Please use 192.168.33.0/24 as your eth0 subnet during network configurations as VirtualBox has already been set as so.

* Please use 192.168.33.10 as the *Gateway* IP. Compass UI has the default value "10.145.88.1", please relace it.

### When to check status:

* After hitting *Deploy*, and the cluster state turns to "Installing". Turn on four vms in VirtualBox.

* When all host states have turned to 50%. ssh to compass server and

```
tail -f /var/ansible/run/{{ cluster_name }}/ansible.log

```

Currently customized service credentials are not supported(will be soon). Default credentials for horizon is "admin/admin_secret"

### Ansible code

* All ansible-related code on github: [https://github.com/stackforge/compass-adatpers](https://github.com/stackforge/compass-adapters), switch to branch *dev/experimental* and ansible files are under /ansible directory

* On the Compass virtualbox, to access ansible playbooks, go to ```/var/ansible/openstack_juno```. To check/modify the ansible code on any existing environment, go to ```/var/ansible/run/{{ cluster_name }}```

### Debugging and refreshing compass

If there's an unknown error, the best log files to follow: ```/var/log/compass/celery.log``` and ```/var/log/compass/compass.log```

To clean up an existing compass cluster, do ```sudo /opt/compass/bin/refresh.sh```

To make sure refresh has cleaned up the ansible running directory, check if ```/var/ansible/run``` is empty

### DO NOT:

* Select adapters other than "OpenStack Juno"
