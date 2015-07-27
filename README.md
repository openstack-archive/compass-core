Compass
=======

## Overview


As a platform-independent deployment automation system, Compass simplifies the complex and error-prone deployment process of various distributed systems such as Openstack, Ceph and so on. It dramatically reduces the time of datacenter server management. Compass, designed with an extensible architecture, can be easily integrated with most of the popular automation
tools (Cobbler, Chef, Ansible) and allows third-parties (vendors) plugins for hardware discovery.

#### [Visit Our Official Project Webiste](http://www.syscompass.org/)

#### [Visit Our Wiki Page for OpenStack Users](https://wiki.openstack.org/wiki/Compass)


##Quick Guide to Developers

###Get started with coding and contributing

** Before everything, setup your environment:**

i. Make sure MySQL is installed on your development box:

    e.g., ```brew install mysql``` (for your Mac OSX box)

ii. Dedicatedly create a virtual environment for your development. You can use  [virtualenvwrapper](http://virtualenvwrapper.readthedocs.org/) to help you manage your virtual environment.

  ```$mkvirtualenv compass-core``` (skip this if you already created compass-core-env)

  ```$workon compass-core``` (get into compass-core-env)

_Note: the above assumes you use virtualenvwrapper to manage your virtualenv_

**1. Checkout source**

    (compass-core-env)$git checkout https://github.com/stackforge/compass-core.git

**2. Run the tests making sure you are working on a clean and working code base**  (i.e., did someone else break the code)

``` (compass-core-env)$tox -r ```

**3. Write your  change, and make sure test your code thoroughly** (otherwise, reviewers won't approve it)

``` (compass-core-env)$git branch -b [TOPIC]```

working, working, working on the [TOPIC] branch ...

``` (compass-core-env)$tox -r ``` (make sure your new code still works)

**4. Submit for review**

```(compass-core-env)$git review ```





### Directories (How codebase is organized)

    * bin/ - contains Compass utility scripts

    * compass/ - contains all Compass business logic including database & backend

        *  api/ - contains Compass RESTful APIs implementation

        * actions/ - interface to essential functionalities executed by Celery tasks, including deploy, find servers and so on

        * apiclient/ - contains Compass RESTful API client

        * db/ - contains database model and supported database operations

        * deployment/ - contains the module for deploying a distributed system from OS installation to package installation based on user configuration via RESTful or Web UI.

        * hdsdiscovery/ - contains the module for learning server hardware spec

        * log_analyzor/ - library to calculate installation progress by processing logs from the servers being deployed

        * tasks/ - definition of Celery tasks triggering Compass actions

        * utils/ - contains utility functions for other modules

        * tests/ - unittests level testing code

        * tests_serverside/ - tests that Compass's functionality to communicate with a known chef server

    * install/ - contains scripts for Compass installation on virtual machine or bare metal server

    * service/ - contains Compass messaging service and cluster installation progress service

    * vagrant/ - contains scripts of downloading compass-adapters and installing the target systems onto the virtual machine(s), this directory is for testing purpose

    * regtest/ - contains the scripts that will be used by the continuous integrations.

    * monitor/ - contains a script monitor Compass server's resource utilization during an installation

    * misc/ - configuration files for Compass server setup

    * conf/ - configuration files related to newly supported target systems will be added here.


Quick Guide to Users
--------------------

### Install Compass from source?

 1. Run `git clone -b dev/exeperimental git://git.openstack.org/stackforge/compass-core.git`
 2. Run `cd compass` to the Compass project directory.
 3. Run `./install/install.sh` to setup compass environment. Please note that before you execute `install.sh`, you may setup your environment variables in `install/install.conf`, explanations and examples of those variables can be found in `install.conf`.
 4. Run `./bin/refresh.sh` to initialize database.
 6. Run `service compass-celeryd start` to start compass celery daemon service.
 7. Run `service compass-progress-updated start` to start compass progress update daemon service.

### How to play Compass?

 1. Make sure your host is one of: mac/ubuntu trusty/ubuntu precise.
 2. Make sure your OS and CPU architecture are both 64-bit.
 3. Make sure you have virtualbox installed.
 4. Make sure you have virtualbox extension pack installed to support pxe.
 5. Run `git clone -b dev/experimental git://git.openstack.org/stackforge/compass-core.git`
 6. Go to directory `compass-core/vagrant`
 7. Run `./launch.sh`
 Note: all the vboxnet interfaces and compass related vms should be removed prior to another launch.


 ### FAQ

  * Why doesn't celery start?  What should I do if I get `celery died but pid file exists` message after running `service compassd status`?

   1. Simply remove celery pid file (`/var/run/celery.pid`).
   2. Try running `export C_FORCE_ROOT=1`
   3. Restart Compass celery daemon.

  * How to check if the compass services run properly?
   1. Run `service compass-celeryd status` and `compass-progress-updated status` to check compass services status.
   2. Run `service httpd status` to check web service status.

  * How to troubleshoot if `compassd` can not start the services?
    1. Try to remove /var/run/celeryd.pid to release the celeryd lock
    2. Try to remove /var/run/progress_update.pid to release the progress_update lock.

  * How to use compass to install distributed systems?

   Access http://<server_ip>. `http://www.syscompass.org/install.html` has some UI instructions.

  * How to run unittest?
     1. `. ~/.virtualenvs/compass-core/bin/activate` to activate compass python venv
     2. go to compass-core directory
     3. make sure you have dependency packages installed, if you used compass install scripts to install compass, they are already installed
     4. run `tox -epy26` or `tox -pey27` depending on your python version.

  * Where to find the log file?
    1. `/var/log/compass/compass.log` is the compass web log.
    2. `/var/log/compass/celery.log` is the celery log, celery logs contain most important debugging information.
    3. The redirected celeryd stdout/stderr is at `/tmp/celeryd.log`.
    4. The redirected progress_update.py stdout/stderr is at `/tmp/progress_update.log`
    5. The web server (httpd) log files are under `/var/log/httpd/`.

  * Where to find the compass config file?
    1. the compass setting file is at /etc/compass/setting.
    2. the default global config file for installing distributed system is at /etc/compass/setting
    3. the default celery config file is at /etc/compass/celeryconfig
    4. adapters, templates and flavor configs are at /etc/compass/ as well.


  * Where are the utility scripts for compass?
   They are at `/opt/compass/bin/`

-(Xicheng)I am adding this line as a trigger to see if CI works, testing..sfdsf
