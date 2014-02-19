"""Health Check module for TFTP service"""

import os
import xmlrpclib
import socket

from compass.actions.health_check import base
from compass.actions.health_check import utils as health_check_utils


class TftpCheck(base.BaseCheck):
    """tftp health check class"""
    NAME = "TFTP Check"

    def run(self):
        """do health check"""
        installer = self.config.OS_INSTALLER
        method_name = "self.check_" + installer + "_tftp()"
        return eval(method_name)

    def check_cobbler_tftp(self):
        """
        Checks if Cobbler manages TFTP service

        :note: we assume TFTP service is running at the
        same machine where this health check runs at
        """

        try:
            remote = xmlrpclib.Server(
                self.config.COBBLER_INSTALLER_URL,
                allow_none=True)
            remote.login(
                *self.config.COBBLER_INSTALLER_TOKEN)
        except:
            self._set_status(
                0,
                "[%s]Error: Cannot login to Cobbler with the tokens "
                " provided in the config file" % self.NAME)
            return (self.code, self.messages)

        cobbler_settings = remote.get_settings()
        if cobbler_settings['manage_tftp'] == 0:
            self.messages.append(
                '[TFTP]Info: tftp service is not managed by Compass')
            return (self.code, self.messages)
        self.check_tftp_dir()
        print "[Done]"
        self.check_tftp_service()
        print "[Done]"
        if self.code == 1:
            self.messages.append(
                "[%s]Info: tftp service health check has completed. "
                "No problems found, all systems go." % self.NAME)

        return (self.code, self.messages)

    def check_tftp_dir(self):
        """Validates TFTP directories and configurations"""

        print "Checking TFTP directories......",
        if not os.path.exists('/var/lib/tftpboot/'):
            self._set_status(
                0,
                "[%s]Error: No tftp-boot libraries found, "
                "please check if tftp server is properly "
                "installed/managed" % self.NAME)

        return True

    def check_tftp_service(self):
        """Checks if TFTP is running on port 69"""

        print "Checking TFTP services......",
        serv_err_msg = health_check_utils.check_service_running(self.NAME,
                                                                'xinetd')
        if not serv_err_msg == "":
            self._set_status(0, serv_err_msg)

        if 'tftp' != socket.getservbyport(69):
            self._set_status(
                0,
                "[%s]Error: tftp doesn't seem to be listening "
                "on Port 60." % self.NAME)

        return True
