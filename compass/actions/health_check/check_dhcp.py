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

"""Health Check module for DHCP service."""
import commands
import os
import re
import socket
import xmlrpclib

from compass.actions.health_check import base


class DhcpCheck(base.BaseCheck):
    """dhcp health check class."""

    NAME = "DHCP Check"

    def run(self):
        """do health check."""
        method_name = "self.check_" + self.os_installer['name'] + "_dhcp()"
        return eval(method_name)

    def check_cobbler_dhcp(self):
        """Checks if Cobbler has taken over DHCP service."""

        try:
            remote = xmlrpclib.Server(
                self.os_installer['cobbler_url'],
                allow_none=True)
            credentials = self.os_installer['credentials']
            remote.login(
                credentials['username'], credentials['password'])
        except Exception:
            self._set_status(
                0,
                "[%s]Error: Cannot login to Cobbler with "
                "the tokens provided in the config file" % self.NAME)
            return (self.code, self.messages)

        cobbler_settings = remote.get_settings()
        if cobbler_settings['manage_dhcp'] == 0:
            self.messages.append(
                "[%s]Info: DHCP service is "
                "not managed by Compass" % self.NAME)
            self.code = 0
            return (self.code, self.messages)

        self.check_cobbler_dhcp_template()
        print "[Done]"
        self.check_dhcp_service()
        self.check_dhcp_netmask()
        print "[Done]"
        if self.code == 1:
            self.messages.append(
                "[%s]Info: DHCP health check has completed. "
                "No problems found, all systems go." % self.NAME)

        return (self.code, self.messages)

    def check_cobbler_dhcp_template(self):
        """Validates Cobbler's DHCP template file."""
        print "Checking DHCP template......",
        if os.path.exists("/etc/cobbler/dhcp.template"):
            var_map = {
                "match_next_server": False,
                "match_subnet": False,
                "match_filename": False,
                "match_range": False,
            }

            ip_regex = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')

            dhcp_template = open("/etc/cobbler/dhcp.template")
            for line in dhcp_template.readlines():
                if line.find("next_server") != -1:
                    elmlist = line.split(" ")
                    for elm in elmlist:
                        if ";" in elm:
                            elm = elm[:-2]

                        if "$next_server" in elm or ip_regex.match(elm):
                            var_map["match_next_server"] = True

                elif line.find("subnet") != -1 and line.find("{") != -1:
                    elmlist = line.split(" ")
                    for elm in elmlist:
                        if ip_regex.match(elm):
                            if elm[-1] == "0" and "255" not in elm:
                                var_map["match_subnet"] = True
                            elif elm[-1] != "0":
                                self.messages.append(
                                    "[%s]Error: Subnet should be set "
                                    "in the form of 192.168.0.0 in"
                                    "/etc/cobbler/dhcp.template" % self.NAME)

                elif line.find("filename") != -1:
                    var_map["match_filename"] = True
                elif line.find("range dynamic-bootp") != -1:
                    elmlist = line.split(" ")
                    ip_count = 0
                    for elm in elmlist:
                        if ";" in elm and "\n" in elm:
                            elm = elm[:-2]

                        if ip_regex.match(elm):
                            ip_count += 1

                    if ip_count != 2:
                        self.messages.append(
                            "[%s]Error: DHCP range should be set "
                            "between two IP addresses in "
                            "/etc/cobbler/dhcp.template" % self.NAME)
                    else:
                        var_map["match_range"] = True

            dhcp_template.close()
            fails = []
            for var in var_map.keys():
                if var_map[var] is False:
                    fails.append(var)

            if len(fails) != 0:
                self._set_status(
                    0,
                    "[%s]Info: DHCP template file "
                    "failed components: %s" % (
                        self.NAME, ' '.join(failed for failed in fails)))

        else:
            self._set_status(
                0,
                "[%s]Error: DHCP template file doesn't exist, "
                "health check failed." % self.NAME)

        return True

    def check_dhcp_netmask(self):
        with open('/etc/dhcp/dhcpd.conf') as conf_reader:
            lines = conf_reader.readlines()
            for line in lines:
                if re.search('^subnet', line):
                    elm_list = line.split(' ')
                    break
            subnet_ip = elm_list[1]
            netmask = elm_list[-2]
            subnet_ip_elm = subnet_ip.split('.')
            netmask_elm = netmask.split('.')
            for index, digit in enumerate(subnet_ip_elm):
                if int(digit) & int(netmask_elm[index]) != int(digit):
                    self._set_status(
                        0,
                        "[%s]Info: DHCP subnet IP and "
                        "netmask do not match" % self.NAME)
                    break
        return True

    def check_dhcp_service(self):
        """Checks if DHCP is running on port 67."""
        print "Checking DHCP service......",
        if not commands.getoutput('pgrep dhcp'):
            self._set_status(
                0,
                "[%s]Error: dhcp service does not "
                "seem to be running" % self.NAME)

        if socket.getservbyport(67) != 'bootps':
            self._set_status(
                0,
                "[%s]Error: bootps is not listening "
                "on port 67" % self.NAME)

        return True
