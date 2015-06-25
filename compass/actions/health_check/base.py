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

"""Base class for Compass Health Check."""
from compass.actions.health_check import utils as health_check_utils
from compass.db.api import adapter as adapter_api
from compass.utils import setting_wrapper as setting


class BaseCheck(object):
    """health check base class."""

    def __init__(self):
        self.config = setting
        self.code = 1
        self.messages = []
        self.dist, self.version, self.release = health_check_utils.get_dist()
        adapter_api.load_adapters_internal()
        self.os_installer = self._get_os_installer()
        self.package_installer = self._get_package_installer()

    def _get_os_installer(self):
        installer = adapter_api.OS_INSTALLERS.values()[0]
        os_installer = {}
        os_installer['name'] = health_check_utils.strip_name(
            installer['name'])
        os_installer.update(installer['settings'])
        return os_installer

    def _get_package_installer(self):
        package_installer = {}
        installer = adapter_api.PACKAGE_INSTALLERS.values()[0]
        package_installer = {}
        package_installer['name'] = health_check_utils.strip_name(
            installer['name'])
        package_installer.update(installer['settings'])
        return package_installer

    def _set_status(self, code, message):
        """set status."""
        self.code = code
        self.messages.append(message)

    def get_status(self):
        """get status."""
        return (self.code, self.messages)
