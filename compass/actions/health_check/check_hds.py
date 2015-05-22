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

"""Health Check module for Hardware Discovery."""
import logging

from compass.actions.health_check import base
from compass.actions.health_check import utils as health_check_utils


class HdsCheck(base.BaseCheck):
    """hds health check class."""
    NAME = "HDS Check"

    def run(self):
        """do health check."""
        if self.dist in ("centos", "redhat", "fedora", "scientific linux"):
            pkg_type = "yum"
        else:
            pkg_type = "apt"

        try:
            pkg_module = __import__(pkg_type)
        except Exception:
            self._set_status(
                0, "[%s]Error: No module named %s please install it first."
                   % (self.NAME, pkg_type)
            )
            return (self.code, self.messages)

        logging.info('import %s: %s', pkg_type, pkg_module)
        method_name = 'self.check_' + pkg_type + '_snmp(pkg_module)'
        eval(method_name)
        print "[Done]"
        self.check_snmp_mibs()
        print "[Done]"
        if self.code == 1:
            self.messages.append("[%s]Info: hds health check has complated. "
                                 "No problems found, all systems go."
                                 % self.NAME)

        return (self.code, self.messages)

    def check_yum_snmp(self, pkg_module):
        """Check if SNMP yum dependencies are installed

        :param pkg_module  : python yum library
        :type pkg_module   : python module

        """
        print "Checking SNMP Packages......",
        yum_base = pkg_module.YumBase()
        uninstalled = []
        for package in ['net-snmp-utils', 'net-snmp', 'net-snmp-python']:
            if len(yum_base.rpmdb.searchNevra(name=package)) == 0:
                self.messages.append("[%s]Error: %s package is required "
                                     "for HDS" % (self.NAME, package))
                uninstalled.append(package)

        if len(uninstalled) != 0:
            self._set_status(0, "[%s]Info: Uninstalled packages: %s"
                                % (self.NAME,
                                   ', '.join(item for item in uninstalled)))

        return True

    def check_apt_snmp(self, pkg_module):
        """do apt health check."""
        return None

    def check_snmp_mibs(self):
        """Checks if SNMP MIB files are properly placed."""

        print "Checking SNMP MIBs......",
        conf_err_msg = health_check_utils.check_path(self.NAME,
                                                     '/etc/snmp/snmp.conf')
        if not conf_err_msg == "":
            self._set_status(0, conf_err_msg)

        mibs_err_msg = health_check_utils.check_path(
            self.NAME,
            '/usr/local/share/snmp/mibs')
        if not mibs_err_msg == "":
            self._set_status(0, mibs_err_msg)

        return True
