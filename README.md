Compass
=======

A Deoployment Automation System. See Wiki page at https://wiki.openstack.org/wiki/Compass.

Porject homepage: http://www.syscompass.org/

How to use in production environments: http://www.syscompass.org/install.html

Try compass out: http://www.syscompass.org/user.html

Quick Guide
-----------

How to install Compass?
-----------------------
 1. Run `git clone -b dev/exeperimental git://git.openstack.org/stackforge/compass-core.git`
 2. Run `cd compass` to the Compass project directory.
 3. Run `./install/install.sh` to setup compass environment. Please note that before you execute `install.sh`, you may setup your environment variables in `install/install.conf`, explanations and examples of those variables can be found in `install.conf`.
 4. Run `./bin/refresh.sh` to initialize database.
 6. Run `service compass-celeryd start` to start compass celery daemon service.
 7. Run `service compass-progress-updated start` to start compass progress update daemon service.

How to play Compass?
--------------------
 1. Make sure your host is one of: mac/ubuntu trusty/ubuntu precise.
 2. Make sure your OS and CPU architecture are both 64-bit.
 3. Make sure you have virtualbox installed.
 4. Make sure you have virtualbox extension pack installed to support pxe.
 5. Run `git clone -b dev/experimental git://git.openstack.org/stackforge/compass-core.git`
 6. Go to directory `compass-core/vagrant`
 7. Run `./launch.sh`
 Note: all the vboxnet interfaces and compass related vms should be removed prior to another launch.

FAQ
---

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
