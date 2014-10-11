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

"""Health Check module for DNS service."""

import commands
import os
import socket
import xmlrpclib

from compass.actions.health_check import base


class DnsCheck(base.BaseCheck):
    """dns health check class."""
    NAME = "DNS Check"

    def run(self):
        """do health check."""
        method_name = "self.check_" + self.os_installer['name'] + "_dns()"
        return eval(method_name)

    def check_cobbler_dns(self):
        """Checks if Cobbler has taken over DNS service."""
        try:
            remote = xmlrpclib.Server(
                self.os_installer['cobbler_url'],
                allow_none=True)
            credentials = self.os_installer['credentials']
            remote.login(
                credentials['username'], credentials['password'])
        except Exception:
            self._set_status(0,
                             "[%s]Error: Cannot login to Cobbler "
                             "with the tokens provided in the config file"
                             % self.NAME)
            return (self.code, self.messages)

        cobbler_settings = remote.get_settings()
        if cobbler_settings['manage_dns'] == 0:
            self.messages.append('[DNS]Info: DNS is not managed by Compass')
            return (0, self.messages)
        self.check_cobbler_dns_template()
        print "[Done]"
        self.check_dns_service()
        print "[Done]"
        if self.code == 1:
            self.messages.append(
                "[%s]Info: DNS health check has complated. "
                "No problems found, all systems go." % self.NAME)
        return (self.code, self.messages)

    def check_cobbler_dns_template(self):
        """Validates Cobbler's DNS template file."""

        print "Checking DNS template......",
        if os.path.exists("/etc/cobbler/named.template"):
            var_map = {
                "match_port": False,
                "match_allow_query": False,
            }
            named_template = open("/etc/cobbler/named.template")
            host_ip = socket.gethostbyname(socket.gethostname())
            missing_query = []
            for line in named_template.readlines():
                if "listen-on port 53" in line and host_ip in line:
                    var_map["match_port"] = True

                if "allow-query" in line:
                    for subnet in ["127.0.0.0/8"]:
                        if subnet not in line:
                            missing_query.append(subnet)

            named_template.close()

            if var_map["match_port"] is False:
                self.messages.append(
                    "[%s]Error: named service port "
                    "and/or IP is misconfigured in "
                    "/etc/cobbler/named.template" % self.NAME)

            if len(missing_query) != 0:
                self.messages.append(
                    "[%s]Error: Missing allow_query values in "
                    "/etc/cobbler/named.template:%s" % (
                        self.NAME,
                        ', '.join(subnet for subnet in missing_query)))
            else:
                var_map["match_allow_query"] = True

            fails = []
            for var in var_map.keys():
                if var_map[var] is False:
                    fails.append(var)

            if len(fails) != 0:
                self._set_status(
                    0,
                    "[%s]Info: DNS template failed components: "
                    "%s" % (
                        self.NAME,
                        ' '.join(failed for failed in fails)))

        else:
            self._set_status(
                0,
                "[%s]Error: named template file doesn't exist, "
                "health check failed." % self.NAME)

        return True

    def check_dns_service(self):
        """Checks if DNS is running on port 53."""

        print "Checking DNS service......",
        if 'named' not in commands.getoutput('ps -ef'):
            self._set_status(
                0,
                "[%s]Error: named service does not seem to be "
                "running" % self.NAME)

        if socket.getservbyport(53) != 'domain':
            self._set_status(
                0,
                "[%s]Error: domain service is not listening on port "
                "53" % self.NAME)

        return None
