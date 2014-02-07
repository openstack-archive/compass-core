"""Miscellaneous Health Check for Compass"""

import os
import re
import commands
import base
import utils as health_check_utils


class MiscCheck(base.BaseCheck):

    NAME = "Miscellaneous Check"

    MISC_MAPPING = {
        "yum":      "rsyslog ntp iproute openssh-clients python git wget "
                    "python-setuptools python-netaddr python-flask "
                    "python-flask-sqlalchemy python-amqplib amqp "
                    "python-paramiko python-mock mod_wsgi httpd squid "
                    "dhcp bind rsync yum-utils xinetd tftp-server gcc "
                    "net-snmp-utils net-snmp python-daemon".split(" "),

        "pip":      "flask-script flask-restful celery six discover "
                    "unittest2 chef".replace("-", "_").split(" "),

        "disable":  "iptables ip6tables".split(" "),

        "enable":   "httpd squid xinetd dhcpd named sshd rsyslog cobblerd "
                    "ntpd compassd".split(" "),
    }

    def run(self):
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
        """Checks if dependencies are installed"""

        print "Checking Linux dependencies....",
        if self.dist in ("centos", "redhat", "fedora", "scientific linux"):
            pkg_type = "yum"
        else:
            pkg_type = "apt"
        try:
            pkg_module = __import__(pkg_type)
        except:
            self._set_status(
                0,
                "[%s]Error: No module named %s, "
                "please install it first." % (self.NAME, pkg_module))
        method_name = 'self.check_' + pkg_type + '_dependencies(pkg_module)'
        eval(method_name)

    def check_yum_dependencies(self, pkg_module):
        """
        Checks if yum dependencies are installed.

        :param pkg_module  : python yum library
        :type pkg_module   : python module

        """
        print "Checking Yum dependencies......",
        yum_base = pkg_module.YumBase()
        uninstalled = []
        for package in self.MISC_MAPPING["yum"]:
            if not yum_base.rpmdb.searchNevra(name=package):
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
        """Checks if required pip packages are installed"""

        print "Checking pip dependencies......",
        uninstalled = []
        for module in self.MISC_MAPPING['pip']:
            try:
                __import__(module)
            except:
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
        """Validates ntp configuration and service"""

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
        """Validates rsyslogd configuration and service"""

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
        """Check if required services are enabled on the start up"""

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
        """Check if SELinux is disabled"""

        print "Checking Selinux......",
        f = open("/etc/selinux/config")
        disabled = False
        for line in f.readlines():
            if "SELINUX=disabled" in line:
                disabled = True
                break
        if disabled is False:
            self._set_status(
                0,
                "[%s]Selinux is not disabled, "
                "please disable it in /etc/selinux/config." % self.NAME)

        return True
