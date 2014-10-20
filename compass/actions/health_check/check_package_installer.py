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

"""Health Check module for Package Installer."""
import logging
import os
import requests

from compass.actions.health_check import base
from compass.actions.health_check import setting as health_check_setting
from compass.actions.health_check import utils as health_check_utils


class PackageInstallerCheck(base.BaseCheck):
    """package installer health check class."""
    NAME = "Package Installer Check"

    def run(self):
        """do health check."""
        method_name = "self." + self.package_installer['name'] + "_check()"
        return eval(method_name)

    def chef_check(self):
        """Checks chef setting, cookbooks and roles."""
        chef_data_map = {
            'CookBook': health_check_setting.COOKBOOKS,
            'Role': health_check_setting.ROLES,
        }

        total_missing = []
        for data_type in chef_data_map.keys():
            total_missing.append(self.check_chef_data(data_type,
                                 chef_data_map[data_type]))
            print "[Done]"

        missing = False
        for item in total_missing:
            if item[1] != []:
                missing = True
                break

        if missing is True:
            messages = []
            for item in total_missing:
                messages.append("[%s]:%s"
                                % (item[0],
                                   ', '.join(missed for missed in item[1])))
            self._set_status(
                0,
                "[%s]Error: Missing modules on chef server: "
                "%s." % (
                    self.NAME,
                    ' ;'.join(message for message in messages)))

        self.check_chef_config_dir()
        print "[Done]"
        if self.code == 1:
            self.messages.append(
                "[%s]Info: Package installer health check "
                "has completed. No problems found, all systems "
                "go." % self.NAME)

        return (self.code, self.messages)

    def check_chef_data(self, data_type, github_url):
        """Checks if chef cookbooks/roles/databags are correct.

        :param data_type  : chef data type
                            should be one of ['CookBook','DataBag','Role']
        :type data_type   : string
        :param github_url : Latest chef data on stackforge/compass-adapters
        :type github_url  : string

        """
        print "Checking Chef %s......" % (data_type.lower().strip() + 's'),
        try:
            import chef
        except Exception:
            self._set_status(
                0,
                "[%s]Error: pychef is not installed." % self.NAME)

            return self.get_status()

        api = chef.autoconfigure()

        github = set([
            item['name']
            for item in requests.get(github_url).json()
        ])
        if data_type == 'CookBook':
            local = set(os.listdir('/var/chef/cookbooks'))
        elif data_type == 'Role':
            local = set([
                name for name, item in chef.Role.list(api=api).iteritems()
            ])
            github = set([
                item['name'].replace(".rb", "").replace(".json", "")
                for item in requests.get(github_url).json()
            ])
        else:
            local = set([
                item for item in eval(
                    'chef.' + data_type + '.list(api=api)'
                )
            ])
        logging.info('github %s: %s', data_type, github)
        logging.info('local %s: %s', data_type, local)
        diff = github - local

        if len(diff) <= 0:
            return (data_type, [])
        else:
            return (data_type, list(diff))

    def check_chef_config_dir(self):
        """Validates chef configuration directories."""

        print "Checking Chef configurations......",
        message = health_check_utils.check_path(self.NAME, '/etc/chef-server/')
        if not message == "":
            self._set_status(0, message)

        message = health_check_utils.check_path(self.NAME, '/opt/chef-server/')
        if not message == "":
            self._set_status(0, message)

        return None
