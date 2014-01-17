import os
import re
import commands

import base
import utils as health_check_utils
from celery.task.control import inspect

class CeleryCheck(base.BaseCheck):

    NAME = "Celery Check"
    def run(self):
        self.check_compass_celery_setting()
        print "[Done]"
        self.check_celery_backend()
        print "[Done]"
        if self.code == 1:
            self.messages.append("[Celery]Info: Celery health check has completed. No problems found, all systems go.")
        return (self.code, self.messages)

    def check_compass_celery_setting(self):
        print "Checking Celery setting......",
        SETTING_MAP = { 'logfile'    :  'CELERY_LOGFILE',
                        'configdir'  :  'CELERYCONFIG_DIR',
                        'configfile' :  'CELERYCONFIG_FILE',
                      }

        res = health_check_utils.validate_setting('Celery', self.config, 'CELERY_LOGFILE')
        if res == True:
            logfile = self.config.CELERY_LOGFILE
        else:
            logfile = ""
            self.set_status(0, res)

        res = health_check_utils.validate_setting('Celery', self.config, 'CELERYCONFIG_DIR')
        if res == True:
            configdir = self.config.CELERYCONFIG_DIR
        else:
            configdir = ""
            self.set_status(0, res)

        res = health_check_utils.validate_setting('Celery', self.config, 'CELERYCONFIG_FILE')
        if res == True:
            configfile = self.config.CELERYCONFIG_FILE
        else:
            configfile = ""
            self.set_status(0, res)

        unset = []
        for item in ['logfile', 'configdir', 'configfile']:
            if eval(item) == "":
                unset.append(SETTING_MAP[item])
        if len(unset) != 0:
            self.set_status(0, "[%s]Error: Unset celery settings: %s in /etc/compass/setting" % (self.NAME, ', '.join(item for item in unset)))
        return True

    def check_celery_backend(self):
        print "Checking Celery Backend......",
        if not 'celeryd' in commands.getoutput('ps -ef'):
            self.set_status(0, "[%s]Error: celeryd is not running" % self.NAME)
            return True

        if not os.path.exists('/etc/compass/celeryconfig'):
            self.set_status(0, "[%s]Error: No celery config file found for Compass" % self.NAME) 
            return True
        
        try:
            insp = inspect()
            celery_stats = inspect.stats(insp)
            if not celery_stats:
                self.set_status(0, "[%s]Error: No running Celery workers were found." % self.NAME)
        except IOError as e:
            self.set_status(0, "[%s]Error: Failed to connect to the backend: %s" % (self.NAME, str(e)))
            from errno import errorcode
            if len(e.args) > 0 and errorcode.get(e.args[0]) == 'ECONNREFUSED':
                self.messages.append("[Celery]Error: Seems like RabbitMQ server isn't running")
        return True
