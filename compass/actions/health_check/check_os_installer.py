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

"""Compass Health Check module for OS Installer."""

import os
import xmlrpclib

from compass.actions.health_check import base


class OsInstallerCheck(base.BaseCheck):
    """os installer health check."""
    NAME = "OS Installer Check"

    def run(self):
        """do health check."""
        method_name = 'self.' + self.os_installer['name'] + '_check()'
        return eval(method_name)

    def cobbler_check(self):
        """Runs cobbler check from xmlrpc client."""
        try:
            remote = xmlrpclib.Server(
                self.os_installer['cobbler_url'],
                allow_none=True)
            credentials = self.os_installer['credentials']
            token = remote.login(
                credentials['username'], credentials['password'])
        except Exception:
            self.code = 0
            self.messages.append(
                "[%s]Error: Cannot login to Cobbler with "
                "the tokens provided in the config file"
                % self.NAME)
            self.messages.append(
                "[%s]Error: Failed to connect to Cobbler "
                "API, please check if /etc/cobbler/setting "
                "is properly configured" % self.NAME)
            return (self.code, self.messages)

        check_result = remote.check(token)

        for index, message in enumerate(check_result):
            if "SELinux" in message:
                check_result.pop(index)

        if len(check_result) != 0:
            self.code = 0
            for error_msg in check_result:
                self.messages.append("[%s]Error: " % self.NAME + error_msg)

        if len(remote.get_distros()) == 0:
            self._set_status(0,
                             "[%s]Error: No Cobbler distros found" % self.NAME)

        if len(remote.get_profiles()) == 0:
            self._set_status(0,
                             "[%s]Error: No Cobbler profiles found"
                             % self.NAME)

        found_ppa = False
        if len(remote.get_repos()) != 0:
            for repo in remote.get_repos():
                if 'ppa_repo' in repo['mirror']:
                    found_ppa = True
                    break

        if found_ppa is False:
            self._set_status(0,
                             "[%s]Error: No repository ppa_repo found"
                             % self.NAME)

        path_map = {
            'match_kickstart': (
                '/var/lib/cobbler/kickstarts/',
                ['default.ks', 'default.seed']
            ),
            'match_snippets': (
                '/var/lib/cobbler/snippets/',
                [
                    'kickstart_done',
                    'kickstart_start',
                    'kickstart_pre_partition_disks',
                    'kickstart_partition_disks',
                    'kickstart_pre_anamon',
                    'kickstart_post_anamon',
                    'kickstart_pre_install_network_config',
                    'kickstart_network_config',
                    'kickstart_post_install_network_config',
                    'kickstart_chef',
                    'kickstart_ntp',
                    'kickstart_yum_repo_config',
                    'preseed_pre_partition_disks',
                    'preseed_partition_disks',
                    'preseed_pre_anamon',
                    'preseed_post_anamon',
                    'preseed_pre_install_network_config',
                    'preseed_network_config',
                    'preseed_post_install_network_config',
                    'preseed_chef',
                    'preseed_ntp',
                    'preseed_apt_repo_config',
                ]
            ),
            'match_ks_mirror': (
                '/var/www/cobbler/',
                ['ks_mirror']
            ),
            'match_repo_mirror': (
                '/var/www/cobbler/',
                ['repo_mirror']
            ),
            'match_iso': (
                '/var/lib/cobbler/',
                ['iso']
            ),
        }
        not_exists = []
        for key in path_map.keys():
            for path in path_map[key][1]:
                if not os.path.exists(path_map[key][0] + path):
                    not_exists.append(path_map[key][0] + path)

        if len(not_exists) != 0:
            self._set_status(
                0,
                "[%s]Error: These locations do not exist: "
                "%s" % (
                    self.NAME,
                    ', '.join(item for item in not_exists)
                )
            )

        if self.code == 1:
            self.messages.append(
                "[%s]Info: OS Installer health check has completed."
                " No problems found, all systems go." % self.NAME)

        return (self.code, self.messages)
