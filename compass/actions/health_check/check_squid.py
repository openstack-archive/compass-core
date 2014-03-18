# Copyright 2014 Huawei Technologies Co. Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Health Check module for Squid service."""
import commands
import os
import pwd
import socket

from compass.actions.health_check import base
from compass.actions.health_check import utils as health_check_utils


class SquidCheck(base.BaseCheck):
    """Squid health check class."""
    NAME = "Squid Check"

    def run(self):
        """do health check."""
        self.check_squid_files()
        print "[Done]"
        self.check_squid_service()
        print "[Done]"
        if self.code == 1:
            self.messages.append(
                "[%s]Info: Squid health check has completed. "
                "No problems found, all systems go." % self.NAME)
        return (self.code, self.messages)

    def check_squid_files(self):
        """Validates squid config, cache directory and ownership."""
        print "Checking Squid Files......",
        var_map = {
            'match_squid_conf': False,
            'match_squid_cache': False,
            'match_squid_ownership': False,
        }

        conf_err_msg = health_check_utils.check_path(
            self.NAME,
            "/etc/squid/squid.conf")
        if not conf_err_msg == "":
            self._set_status(0, conf_err_msg)
        elif int(oct(os.stat('/etc/squid/squid.conf').st_mode)) < 100644:
            self._set_status(
                0,
                "[%s]Error: squid.conf has incorrect "
                "file permissions" % self.NAME)
        else:
            var_map['match_squid_conf'] = True

        squid_path_err_msg = health_check_utils.check_path(
            self.NAME, '/var/squid/')
        if not squid_path_err_msg == "":
            self._set_status(0, squid_path_err_msg)
        elif health_check_utils.check_path(
            self.NAME,
            '/var/squid/cache'
        ) != "":
            self._set_status(
                0,
                health_check_utils.check_path(
                    self.NAME,
                    '/var/squid/cache'
                )
            )
        else:
            var_map['match_squid_cache'] = True
            uid = os.stat('/var/squid/').st_uid
            gid = os.stat('/var/squid/').st_gid
            if uid != gid or pwd.getpwuid(23).pw_name != 'squid':
                self._set_status(
                    0,
                    "[%s]Error: /var/squid directory ownership "
                    "misconfigured" % self.NAME)
            else:
                var_map['match_squid_ownership'] = True

        fails = []
        for key in var_map.keys():
            if var_map[key] is False:
                fails.append(key)

        if len(fails) != 0:
            self.messages.append(
                "[%s]Info: Failed components for squid config: "
                "%s" % (
                    self.NAME,
                    ', '.join(item for item in fails)
                )
            )
        return True

    def check_squid_service(self):
        """Checks if squid is running on port 3128."""

        print "Checking Squid service......",
        if 'squid' not in commands.getoutput('ps -ef'):
            self._set_status(
                0,
                "[%s]Error: squid service does not seem "
                "running" % self.NAME)

        try:
            if 'squid' != socket.getservbyport(3128):
                self._set_status(
                    0,
                    "[%s]Error: squid is not listening on "
                    "3128" % self.NAME)

        except Exception:
            self._set_status(
                0,
                "[%s]Error: No service is listening on 3128, "
                "squid failed" % self.NAME)

        return True
