"""Health Check module for Squid service"""

import os
import re
import commands
import pwd

from socket import *

import base
import utils as health_check_utils

class SquidCheck(base.BaseCheck):

    NAME = "Squid Check"
    def run(self):
        self.check_squid_files()
        print "[Done]"
        self.check_squid_service()
        print "[Done]"
        if self.code == 1:
            self.messages.append('[Squid]Info: Squid health check has completed. No problems found, all systems go.')
        return (self.code, self.messages)

    def check_squid_files(self):
        """Validates squid config, cache directory and ownership"""

        print "Checking Squid Files......",
        VAR_MAP = { 'match_squid_conf'      : False,
                    'match_squid_cache'     : False,
                    'match_squid_ownership' : False,
                  }

        conf_err_msg = health_check_utils.check_path(self.NAME, "/etc/squid/squid.conf")
        if not conf_err_msg == "":
            self.set_status(0, conf_err_msg)
        elif int(oct(os.stat('/etc/squid/squid.conf').st_mode)) < 644:
            self.set_status(0, "[%s]Error: squid.conf has incorrect file permissions" % self.NAME)
        else:
            VAR_MAP['match_squid_conf'] = True

        squid_path_err_msg = health_check_utils.check_path(self.NAME, '/var/squid/')
        if not squid_path_err_msg == "":
            self.set_stauts(0, squid_path_err_msg)
        elif health_check_utils.check_path(self.NAME, '/var/squid/cache') != "":
            self.set_status(0, health_check_utils.check_path(self.NAME, '/var/squid/cache'))
        else:
            VAR_MAP['match_squid_cache'] = True
            uid = os.stat('/var/squid/').st_uid
            gid = os.stat('/var/squid/').st_gid
            if uid != gid or pwd.getpwuid(23).pw_name != 'squid':
                self.set_status(0, "[%s]Error: /var/squid directory ownership misconfigured" % self.NAME)
            else:
                VAR_MAP['match_squid_ownership'] = True

        failed = []
        for key in VAR_MAP.keys():
            if VAR_MAP[key] == False:
                failed.append(key)
        if len(failed) != 0:
            self.messages.append("[Squid]Info: Failed components for squid config: %s" % ', '.join(item for item in failed))
        return True

    def check_squid_service(self):
        """Checks if squid is running on port 3128"""

        print "Checking Squid service......",
        if not 'squid' in commands.getoutput('ps -ef'):
            self.set_status(0, "[%s]Error: squid service does not seem running" % self.NAME)

        try:
            if 'squid' != getservbyport(3128):
                self.set_status(0, "[%s]Error: squid is not listening on 3128" % self.NAME)
        except:
            self.set_status(0, "[%s]Error: No service is listening on 3128, squid failed" % self.NAME)
        return True
