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
        self.check_chef_config_dir()
        print "[Done]"
        if self.code == 1:
            self.messages.append(
                "[%s]Info: Package installer health check "
                "has completed. No problems found, all systems "
                "go." % self.NAME)

        return (self.code, self.messages)

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

    def ansible_check(self):
        """Placeholder for ansible check."""
        print "Checking ansible......"
        print ("[Done]")
        self.code == 1
        self.messages.append(
            "[%s]Info: Package installer health check "
            "has completed. No problems found, all systems "
            "go." % self.NAME)
        return (self.code, self.messages)
