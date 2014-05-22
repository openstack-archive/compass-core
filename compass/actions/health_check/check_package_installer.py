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

import os
import requests
import subprocess

from compass.actions.health_check import base
from compass.actions.health_check import setting as health_check_setting
from compass.actions.health_check import utils as health_check_utils


class PackageInstallerCheck(base.BaseCheck):
    """package installer health check class."""
    NAME = "Package Installer Check"

    def run(self):
        """do health check."""
        installer = self.config.PACKAGE_INSTALLER
        method_name = "self." + installer + "_check()"
        return eval(method_name)

    def chef_check(self):
        """Checks chef setting, cookbooks, databags and roles."""
        for data_type in ['Cookbook', 'Role', 'Databag']:
            self.check_chef_data(data_type)
            if self.code != 1:
                return (self.code, self.messages)

            print "[Done]"

        self.check_chef_config_dir()
        print "[Done]"
        if self.code == 1:
            self.messages.append(
                "[%s]Info: Package installer health check "
                "has completed. No problems found, all systems "
                "go." % self.NAME)

        return (self.code, self.messages)

    def check_chef_data(self, data_type):
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
            return

        api = chef.autoconfigure()
        if data_type == 'CookBook':
            local = set([
                name for name in os.listdir('/var/chef/cookbooks')
                if name
            ])
            try:
                server = set(api['/cookbooks'].keys())
            except Exception:
                self._set_status(
                    0,
                    "[%s]Error: pychef fails to get cookbooks" % self.NAME)
                return
        elif data_type == 'Role':
            local = set([
                name[:-3] for name in os.listdir('/var/chef/roles')
                if name.endswith('.rb')
            ])
            try:
                server = set(api['/roles'].keys())
            except Exception:
                self._set_status(
                    0,
                    "[%s]Error: pychef fails to get roles" % self.NAME)
                return
        else:
            local = set([
                name for name in os.listdir('/var/chef/databags')
                if name
            ])
            try:
                server = set(api['/data'].keys())
            except Exception:
                self._set_status(
                    0,
                    "[%s]Error: pychef fails to get databags" % self.NAME)
                return

        diff = server - local

        if len(diff) > 0:
            self._set_status(
                0,
                "[%s]Error: %s diff: %s" % (self.NAME, diff))

    def check_chef_config_dir(self):
        """Validates chef configuration directories."""

        print "Checking Chef configurations......",
        message = health_check_utils.check_path(self.NAME, '/etc/chef-server/')
        if not message == "":
            self._set_status(0, message)
            return

        message = health_check_utils.check_path(self.NAME, '/opt/chef-server/')
        if not message == "":
            self._set_status(0, message)
            return
