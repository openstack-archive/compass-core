"""Compass Health Check module for OS Installer"""

import os
import re
import xmlrpclib

import base


class OsInstallerCheck(base.BaseCheck):

    NAME = "OS Installer Check"

    def run(self):
        installer = self.config.OS_INSTALLER
        method_name = 'self.' + installer + '_check()'
        return eval(method_name)

    def cobbler_check(self):
        """Runs cobbler check from xmlrpc client"""

        try:
            self.remote = xmlrpclib.Server(
                self.config.COBBLER_INSTALLER_URL,
                allow_none=True)
            self.token = self.remote.login(
                *self.config.COBBLER_INSTALLER_TOKEN)
        except:
            self.code = 0
            self.messages.append(
                "[OS Installer]Error: Cannot login to Cobbler with "
                "the tokens provided in the config file")
            self.messages.append(
                "[OS Installer]Error: Failed to connect to Cobbler "
                "API, please check if /etc/cobbler/setting "
                "is properly configured")
            return (self.code, self.messages)

        check_result = self.remote.check(self.token)
        if len(check_result) != 0:
            self.code = 0
            for error_msg in check_result:
                self.messages.append("[OS Installer]Error: " + error_msg)

        if len(self.remote.get_distros()) == 0:
            self._set_status(0,
                             "[%s]Error: No Cobbler distros found" % self.NAME)

        if len(self.remote.get_profiles()) == 0:
            self._set_status(0,
                             "[%s]Error: No Cobbler profiles found"
                             % self.NAME)

        found_ppa = False
        if len(self.remote.get_repos()) != 0:
            for repo in self.remote.get_repos():
                if 'ppa_repo' in repo['mirror']:
                    found_ppa = True
                    break
        if found_ppa is False:
            self._set_status(0,
                             "[%s]Error: No repository ppa_repo found"
                             % self.NAME)

        PATH_MAP = {'match_kickstart':      ('/var/lib/cobbler/kickstarts/',
                                             ['default.ks', ]
                                             ),
                    'match_snippets':       ('/var/lib/cobbler/snippets/',
                                             [
                                                 'chef',
                                                 'chef-validator.pem',
                                                 'client.rb',
                                                 'first-boot.json',
                                                 'kickstart_done',
                                                 'kickstart_start',
                                                 'network_config',
                                                 'ntp.conf',
                                                 'partition_disks',
                                                 'partition_select',
                                                 'post_anamon',
                                                 'post_install_network_config',
                                                 'pre_anamon',
                                                 'pre_install_network_config',
                                                 'rsyslogchef',
                                                 'rsyslogconf',
                                                 'yum.conf',
                                             ]
                                             ),
                    'match_ks_mirror':     ('/var/www/cobbler/',
                                            ['ks_mirror']
                                            ),
                    'match_repo_mirror':   ('/var/www/cobbler/',
                                            ['repo_mirror/ppa_repo']
                                            ),
                    'match_iso':           ('/var/lib/cobbler/', ['iso']),
                    }
        not_exists = []
        for key in PATH_MAP.keys():
            for path in PATH_MAP[key][1]:
                if not os.path.exists(PATH_MAP[key][0] + path):
                    not_exists.append(PATH_MAP[key][0] + path)
        if len(not_exists) != 0:
            self._set_status(
                0,
                "[%s]Error: These locations do not exist: %s"
                % (self.NAME, ', '.join(item for item in not_exists)))

        if self.code == 1:
            self.messages.append(
                "[OS Installer]Info: OS Installer health check "
                "has completed. No problems found, all systems go.")

        return (self.code, self.messages)
