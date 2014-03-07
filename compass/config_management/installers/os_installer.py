# Copyright 2014 Openstack Foundation
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

"""Module for interface of os installer.

   .. moduleauthor::: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import logging

from compass.config_management.installers import installer
from compass.utils import setting_wrapper as setting


class Installer(installer.Installer):
    """Interface for os installer."""
    NAME = 'os_installer'

    def get_oses(self):
        """virtual method to get supported oses.

        :returns: list of str, each is the supported os version.
        """
        return []


INSTALLERS = {}


def get_installer_by_name(name, **kwargs):
    """Get os installer by name.

    :param name: os installer name.
    :type name: str

    :returns: :instance of subclass of :class:`Installer`
    :raises: KeyError
    """
    if name not in INSTALLERS:
        logging.error('os installer name %s is not in os installers %s',
                      name, INSTALLERS)
        raise KeyError('os installer name %s is not in os INSTALLERS')

    os_installer = INSTALLERS[name](**kwargs)
    logging.debug('got os installer %s', os_installer)
    return os_installer


def register(os_installer):
    """Register os installer.

    :param os_installer: subclass of :class:`Installer`
    :raises: KeyError
    """
    if os_installer.NAME in INSTALLERS:
        logging.error(
            'os installer %s is already registered in INSTALLERS %s',
            os_installer, INSTALLERS)
        raise KeyError(
            'os installer %s is already registered' % os_installer)

    logging.info('register os installer %s', os_installer)
    INSTALLERS[os_installer.NAME] = os_installer


def get_installer(**kwargs):
    """Get default os installer from compass setting."""
    return get_installer_by_name(setting.OS_INSTALLER, **kwargs)
