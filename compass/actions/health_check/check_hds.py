"""Health Check module for Hardware Discovery"""

import os
import re

import base
import utils as health_check_utils

class HdsCheck(base.BaseCheck):

    NAME = "HDS Check"
    def run(self):
        if self.dist in ("centos", "redhat", "fedora", "scientific linux"):
            pkg_type = "yum"
        else:
            pkg_type = "apt"
        try:
            pkg_module = __import__(pkg_type)
        except:
            self.messages.append("[HDS]Error: No module named %s, please install it first." % pkg_module)
        method_name = 'self.check_' + pkg_type + '_snmp(pkg_module)'
        eval(method_name)
        print "[Done]"
        self.check_snmp_mibs()
        print "[Done]"
        if self.code == 1:
            self.messages.append("[HDS]Info: hds health check has complated. No problems found, all systems go.")
        return (self.code, self.messages)

    def check_yum_snmp(self, pkg_module):
        """
        Check if SNMP yum dependencies are installed

        :param pkg_module  : python yum library
        :type pkg_module   : python module

        """
        print "Checking SNMP Packages......",
        yum_base = pkg_module.YumBase()
        uninstalled = []
        for package in ['net-snmp-utils', 'net-snmp', 'net-snmp-python']:
            if not yum_base.rpmdb.searchNevra(name=package):
                self.messages.append("[HDS]Error: %s package is required for HDS" % package)
                uninstalled.append(package)
        if len(uninstalled) != 0:
            self.set_status(0, "[%s]Info: Uninstalled packages: %s" % (self.NAME, ', '.join(item for item in uninstalled)))
        return True

    def check_apt_snmp(self, pkg_module):
        ## TODO: add ubuntu package check here
        return None

    def check_snmp_mibs(self):
        """Checks if SNMP MIB files are properly placed"""

        print "Checking SNMP MIBs......",
        conf_err_msg = health_check_utils.check_path(self.NAME, '/etc/snmp/snmp.conf')
        if not conf_err_msg == "":
            self.set_status(0, conf_err_msg)

        mibs_err_msg = health_check_utils.check_path(self.NAME, '/usr/local/share/snmp/mibs')
        if not mibs_err_msg == "":
            self.set_status(0, mibs_err_msg)
        return True
