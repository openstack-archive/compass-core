"""Health Check module for DNS service"""

import os
import re
import xmlrpclib
import commands

from socket import *

import base

class DnsCheck(base.BaseCheck):

    NAME = "DNS Check"
    def run(self):
        installer = self.config.OS_INSTALLER
        method_name = "self.check_" + installer + "_dns()"
        return eval(method_name)

    def check_cobbler_dns(self):
        """Checks if Cobbler has taken over DNS service"""

        try:
            self.remote = xmlrpclib.Server(
                self.config.COBBLER_INSTALLER_URL,
                allow_none=True)
            self.token = self.remote.login(
              *self.config.COBBLER_INSTALLER_TOKEN)
        except:
            self._set_status(0, "[%s]Error: Cannot login to Cobbler with the tokens provided in the config file" % self.NAME)
            return (self.code, self.messages)

        cobbler_settings = self.remote.get_settings()
        if cobbler_settings['manage_dns'] == 0:
            self.messages.append('[DNS]Info: DNS is not managed by Compass')
            return (self.code, self.messages)
        self.check_cobbler_dns_template()
        print "[Done]"
        self.check_dns_service()
        print "[Done]"
        if self.code == 1:
            self.messages.append('[DNS]Info: DNS health check has complated. No problems found, all systems go.')
        return (self.code, self.messages)

    def check_cobbler_dns_template(self):
        """Validates Cobbler's DNS template file"""

        print "Checking DNS template......",
        if os.path.exists("/etc/cobbler/named.template"):
            VAR_MAP = { "match_port"   : False,
                        "match_allow_query" : False,
                      }
            f = open("/etc/cobbler/named.template")
            host_ip = gethostbyname(gethostname())
            missing_query = []
            for line in f.readlines():
                if "listen-on port 53" in line and host_ip in line:
                    VAR_MAP["match_port"] = True
                if "allow-query" in line:
                    for subnet in ["127.0.0.0/8", "10.0.0.0/8", "192.168.0.0/16", "172.16.0.0/12"]:
                        if not subnet in line:
                            missing_query.append(subnet)
            f.close()

            if VAR_MAP["match_port"] == False:
                self.messages.append('[DNS]Error: named service port and/or IP is misconfigured in /etc/cobbler/named.template')
            if len(missing_query) != 0:
                self.messages.append('[DNS]Error: Missing allow_query values in /etc/cobbler/named.template:%s' % ', '.join(subnet for subnet in missing_query))
            else:
                VAR_MAP["match_allow_query"] = True

            failed = []
            for var in VAR_MAP.keys():
                if VAR_MAP[var] == False:
                    failed.append(var)
            if len(failed) != 0:
                self._set_status(0, "[%s]Info: DNS template file failed components: %s" % (self.NAME, ' '.join(f for f in failed)))
        else:
            self._set_status(0, "[%s]Error: named template file doesn't exist, health check failed." % self.NAME)
        return True

    def check_dns_service(self):
        """Checks if DNS is running on port 53"""

        print "Checking DNS service......",
        if not 'named' in commands.getoutput('ps -ef'):
            self._set_status(0, "[%s]Error: named service does not seem to be running" % self.NAME)

        if getservbyport(53) != 'domain':
            self._set_status(0, "[%s]Error: domain service is not listening on port 53" % self.NAME)
        return None
