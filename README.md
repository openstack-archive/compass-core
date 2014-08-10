Compass
=======


A Deoployment Automation System. See Wiki page at https://wiki.openstack.org/wiki/Compass.

Two other related github repos are:

 * compass-web: http://github.com/stackforge/compass-web. The frontend layer of the Compass. It is built with client side MVC model with JavaScript.
 * compass-adapters: http://github.com/stackforge/compass-adapters. The add-on modules for Compass adapters. Currently, this hosts Cobbler related data file (kickstart, snippet, etc), and chef cookbooks for OpenStack and other software packages.

Note: We are currently actively developing an improved version of Compass on dev/experimental branch. The target release date is end of August.

How to install Compass?
-----------------------
 1. Run `git clone https://github.com/huawei-cloud/compass`
 2. Run `cd compass` to the Compass project directory.
 3. Run `./install/install.sh` to setup compass environment. Please note that before you execute `install.sh`, you may setup your environment variables in `install/install.conf`, explanations and examples of those variables can be found in `install.conf`.
 4. Run `source /etc/profile` to setup compass profile.
 5. Run `./bin/refresh.sh` to initialize database.
 6. Run `service compassd start` to start compass daemon services.

FAQ
---

 * Why doesn't celery start?  What should I do if I get `celery died but pid file exists` message after running `service compassd status`?

  1. Simply remove celery pid file (`/var/run/celery.pid`).
  2. Try running `export C_FORCE_ROOT=1`
  3. Restart Compass daemon.

 * How to restart compass service?
  1. Run `service compassd restart`
  2. Run `service httpd restart` to restart web service.

 * How to check if the compass services run properly?
  1. Run `service compassd status` to check compass services status.
  2. Run `service httpd status` to check web service status.

 * How to troubleshoot if `compassd` can not start the services?
   1. Try to remove /var/run/celeryd.pid to release the celeryd lock
   2. Try to remove /var/run/progress_update.pid to release the progress_update lock.

 * How to use compass to install distributed systems?

  Access http://<server_ip>/ods/ods.html. In the current version, we only support OpenStack deployment with a simplified configuration. Follow the simple wizard from the Web UI.

 * How to run unittest?
    `COMPASS_SETTING=<your own compass setting> python -m discover -s compass/tests`

 * Where to find the log file?
   1. `/var/log/compass/compass.log` is the compass web log.
   2. `/var/log/compass/celery.log` is the celery log
   3. The redirected celeryd stdout/stderr is at `/tmp/celeryd.log`.
   4. The redirected progress_update.py stdout/stderr is at `/tmp/progress_update.log`
   5. The web server (httpd) log files are under `/var/log/httpd/`.

 * Where to find the compass config file?
   1. the compass setting file is at /etc/compass/setting.
   2. the default global config file for installing distributed system is at /etc/compass/setting
   3. the default celery config file is at /etc/compass/celeryconfig

 * Where is the default database file?
  It is at `/opt/compass/db/app.db`

 * Where is the utility scripts for compass?
  It is at `/opt/compass/bin/`
