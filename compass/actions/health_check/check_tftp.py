import os
import re
import sys
import xmlrpclib
import commands

from socket import *

import base
import utils as health_check_utils

class TftpCheck(base.BaseCheck):
   
    NAME = "TFTP Check"
    def run(self):
        installer = self.config.OS_INSTALLER
        method_name = "self.check_" + installer + "_tftp()" 
        return eval(method_name)

    def check_cobbler_tftp(self):
        try:
            self.remote = xmlrpclib.Server(
                self.config.COBBLER_INSTALLER_URL,
                allow_none=True)
            self.token = self.remote.login(
              *self.config.COBBLER_INSTALLER_TOKEN)
        except:
            self.set_status(0, "[%s]Error: Cannot login to Cobbler with the tokens provided in the config file" % self.NAME)
            return (self.code, self.messages)

        cobbler_settings = self.remote.get_settings()
        if cobbler_settings['manage_tftp'] == 0:
            self.messages.append('[TFTP]Info: tftp service is not managed by Compass')
            return (self.code, self.messages)
        self.check_tftp_dir()
        print "[Done]"
        self.check_tftp_service()
        print "[Done]"
        if self.code == 1:
            self.messages.append("[TFTP]Info: tftp service health check has completed. No problems found, all systems go.")

        return (self.code, self.messages)
    
    def check_tftp_dir(self):
        print "Checking TFTP directories......",
        if not os.path.exists('/var/lib/tftpboot/'):
            self.set_status(0, "[%s]Error: No tftp-boot libraries found, please check if tftp server is properly installed/managed" % self.NAME)

        return True

    def check_tftp_service(self):
        print "Checking TFTP services......",
        serv_err_msg = health_check_utils.check_service_running(self.NAME, 'xinetd')
        if not serv_err_msg == "":
            self.set_status(0, serv_err_msg)

        if 'tftp' != getservbyport(69):
            self.set_status(0, "[%s]Error: tftp doesn't seem to be listening on Port 60." % self.NAME)

        
        return True
