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

"""Miscellaneous Health Check for Compass."""
import logging

from compass.actions.health_check import base
from compass.actions.health_check import utils as health_check_utils


class MiscCheck(base.BaseCheck):
    """health check for misc."""
    NAME = "Miscellaneous Check"

    MISC_MAPPING = {
        "yum": "rsyslog ntp iproute openssh-clients python git wget "
               "python-setuptools "
               "amqp mod_wsgi httpd squid "
               "dhcp bind rsync yum-utils xinetd tftp-server gcc "
               "net-snmp-utils net-snmp".split(" "),
        "pip": "netaddr flask flask_script flask_restful amqplib "
               "flask_sqlalchemy paramiko mock celery six discover daemon "
               "unittest2 chef".split(" "),
        "disable": "iptables ip6tables".split(" "),
        "enable": "httpd squid xinetd dhcpd named sshd rsyslog cobblerd "
                  "ntpd compass-celeryd compass-progress-updated".split(" "),
    }

    def run(self):
        """do health check."""
        self.check_linux_dependencies()
        print "[Done]"
        self.check_pip_dependencies()
        print "[Done]"
        self.check_ntp()
        print "[Done]"
        self.check_rsyslogd()
        print "[Done]"
        self.check_chkconfig()
        print "[Done]"
        self.check_selinux()
        print "[Done]"

        if self.code == 1:
            self.messages.append(
                "[%s]Info: Miscellaneous check has completed "
                "No problems found, all systems go." % self.NAME)
        return (self.code, self.messages)

    def check_linux_dependencies(self):
        """Checks if dependencies are installed."""
        print "Checking Linux dependencies....",
        if self.dist in ("centos", "redhat", "fedora", "scientific linux"):
            pkg_type = "yum"
        else:
            pkg_type = "apt"

        try:
            pkg_module = __import__(pkg_type)
        except Exception:
            self._set_status(
                0,
                "[%s]Error: No module named %s, "
                "please install it first." % (self.NAME, pkg_type))
            return True

        logging.info('import %s: %s', pkg_type, pkg_module)
        method_name = 'self.check_' + pkg_type + '_dependencies(pkg_module)'
        eval(method_name)

    def check_yum_dependencies(self, pkg_module):
        """Checks if yum dependencies are installed.

        :param pkg_module  : python yum library
        :type pkg_module   : python module

        """
        print "Checking Yum dependencies......",
        yum_base = pkg_module.YumBase()
        uninstalled = []
        for package in self.MISC_MAPPING["yum"]:
            if len(yum_base.rpmdb.searchNevra(name=package)) == 0:
                self._set_status(
                    0,
                    "[%s]Error: %s package is required"
                    % (self.NAME, package))
                uninstalled.append(package)

        if len(uninstalled) != 0:
            self._set_status(
                0,
                "[%s]Info: Uninstalled yum packages: %s"
                % (self.NAME, ', '.join(item for item in uninstalled)))

        return True

    def check_pip_dependencies(self):
        """Checks if required pip packages are installed."""
        print "Checking pip dependencies......",
        uninstalled = []
        for module in self.MISC_MAPPING['pip']:
            try:
                __import__(module)
            except Exception:
                self._set_status(
                    0,
                    "[%s]Error: pip package %s is requred"
                    % (self.NAME, module))
                uninstalled.append(module)

            if len(uninstalled) != 0:
                self._set_status(
                    0,
                    "[%s]Info: Uninstalled pip packages: %s"
                    % (self.NAME, ', '.join(item for item in uninstalled)))

        return True

    def check_ntp(self):
        """Validates ntp configuration and service."""

        print "Checking NTP......",
        conf_err_msg = health_check_utils.check_path(self.NAME,
                                                     '/etc/ntp.conf')
        if not conf_err_msg == "":
            self._set_status(0, conf_err_msg)

        serv_err_msg = health_check_utils.check_service_running(self.NAME,
                                                                'ntpd')
        if not serv_err_msg == "":
            self._set_status(0, serv_err_msg)

        return True

    def check_rsyslogd(self):
        """Validates rsyslogd configuration and service."""

        print "Checking rsyslog......",
        conf_err_msg = health_check_utils.check_path(self.NAME,
                                                     '/etc/rsyslog.conf')
        if not conf_err_msg == "":
            self._set_status(0, conf_err_msg)

        dir_err_msg = health_check_utils.check_path(self.NAME,
                                                    '/etc/rsyslog.d/')
        if not dir_err_msg == "":
            self._set_status(0, dir_err_msg)

        serv_err_msg = health_check_utils.check_service_running(self.NAME,
                                                                'rsyslogd')
        if not serv_err_msg == "":
            self._set_status(0, serv_err_msg)

        return True

    def check_chkconfig(self):
        """Check if required services are enabled on the start up."""

        print "Checking chkconfig......",
        serv_to_disable = []
        for serv in self.MISC_MAPPING["disable"]:
            if health_check_utils.check_chkconfig(serv) is True:
                self._set_status(
                    0,
                    "[%s]Error: %s is not disabled"
                    % (self.NAME, serv))
                serv_to_disable.append(serv)

        if len(serv_to_disable) != 0:
            self._set_status(
                0,
                "[%s]Info: You need to disable these services "
                "on system start-up: %s"
                % (self.NAME,
                   ", ".join(item for item in serv_to_disable)))

        serv_to_enable = []
        for serv in self.MISC_MAPPING["enable"]:
            if health_check_utils.check_chkconfig(serv) is False:
                self._set_status(
                    0, "[%s]Error: %s is disabled" % (self.NAME, serv))
                serv_to_enable.append(serv)

        if len(serv_to_enable) != 0:
            self._set_status(0, "[%s]Info: You need to enable these "
                                "services on system start-up: %s"
                                % (self.NAME,
                                   ", ".join(item for item in serv_to_enable)))

        return True

    def check_selinux(self):
        """Check if SELinux is disabled."""
        print "Checking Selinux......",
        disabled = False
        with open("/etc/selinux/config") as selinux:
            for line in selinux:
                if "SELINUX=disabled" in line:
                    disabled = True
                    break

        if disabled is False:
            self._set_status(
                0,
                "[%s]Selinux is not disabled, "
                "please disable it in /etc/selinux/config." % self.NAME)

        return True
