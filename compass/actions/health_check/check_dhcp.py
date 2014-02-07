"""Health Check module for DHCP service"""

import os
import re
import commands
import xmlrpclib
import sys

from socket import *

import base


class DhcpCheck(base.BaseCheck):

    NAME = "DHCP Check"

    def run(self):
        installer = self.config.OS_INSTALLER
        method_name = "self.check_" + installer + "_dhcp()"
        return eval(method_name)

    def check_cobbler_dhcp(self):
        """Checks if Cobbler has taken over DHCP service"""

        try:
            self.remote = xmlrpclib.Server(
                self.config.COBBLER_INSTALLER_URL,
                allow_none=True)
            self.token = self.remote.login(
                *self.config.COBBLER_INSTALLER_TOKEN)
        except:
            self._set_status(
                0,
                "[%s]Error: Cannot login to Cobbler with "
                "the tokens provided in the config file" % self.NAME)
            return (self.code, self.messages)

        cobbler_settings = self.remote.get_settings()
        if cobbler_settings['manage_dhcp'] == 0:
            self.messages.append(
                "[%s]Info: DHCP service is not managed by Compass"
                % self.NAME)
            return (self.code, self.messages)
        self.check_cobbler_dhcp_template()
        print "[Done]"
        self.check_dhcp_service()
        print "[Done]"
        if self.code == 1:
            self.messages.append(
                "[%s]Info: DHCP health check has completed. "
                "No problems found, all systems go." % self.NAME)
        return (self.code, self.messages)

    def check_cobbler_dhcp_template(self):
        """Validates Cobbler's DHCP template file"""

        print "Checking DHCP template......",
        if os.path.exists("/etc/cobbler/dhcp.template"):
            VAR_MAP = {"match_next_server": False,
                       "match_subnet":      False,
                       "match_filename":    False,
                       "match_range":       False,
                       }

            ip_regex = re.compile('^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')

            f = open("/etc/cobbler/dhcp.template")
            for line in f.readlines():
                if line.find("next_server") != -1:
                    elmlist = line.split(" ")
                    for elm in elmlist:
                        if ";" in elm:
                            elm = elm[:-2]
                        if "$next_server" in elm or ip_regex.match(elm):
                            VAR_MAP["match_next_server"] = True

                elif line.find("subnet") != -1 and line.find("{") != -1:
                    elmlist = line.split(" ")
                    for elm in elmlist:
                        if ip_regex.match(elm):
                            if elm[-1] == "0" and "255" not in elm:
                                VAR_MAP["match_subnet"] = True
                            elif elm[-1] != "0":
                                self.messages.append(
                                    "[%s]Error: Subnet should be set "
                                    "in the form of 192.168.0.0 in"
                                    "/etc/cobbler/dhcp.template"
                                    % self.NAME)
                elif line.find("filename") != -1:
                    VAR_MAP["match_filename"] = True
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
                        VAR_MAP["match_range"] = True

            f.close()
            failed = []
            for var in VAR_MAP.keys():
                if VAR_MAP[var] is False:
                    failed.append(var)
            if len(failed) != 0:
                self._set_status(0,
                                 "[%s]Info: DHCP template file "
                                 "failed components: %s"
                                 % (self.NAME, ' '.join(f for f in failed)))
        else:
            self._set_status(0,
                             "[%s]Error: DHCP template file doesn't exist, "
                             "health check failed." % self.NAME)
        return True

    def check_dhcp_service(self):
        """Checks if DHCP is running on port 67"""

        print "Checking DHCP service......",
        if not 'dhcp' in commands.getoutput('ps -ef'):
            self._set_status(
                0,
                "[%s]Error: dhcp service does not seem to be running"
                % self.NAME)
        if getservbyport(67) != 'bootps':
            self._set_status(
                0,
                "[%s]Error: bootps is not listening on port 67"
                % self.NAME)
        return True
