"""Module to provider interface for package installer.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import logging

from compass.config_management.installers import installer
from compass.utils import setting_wrapper as setting


class Installer(installer.Installer):
    """Interface for package installer."""
    NAME = 'package_installer'

    def get_target_systems(self, oses):
        """virtual method to get available target_systems for each os.

        :param oses: supported os versions.
        :type oses: list of st

        :returns: dict of os_version to target systems as list of str.
        """
        return {}

    def get_roles(self, target_system):
        """virtual method to get all roles of given target system.

        :param target_system: target distributed system such as openstack.
        :type target_system: str

        :returns: dict of role to role description as str.
        """
        return {}

    def os_installer_config(self, config, **kwargs):
        """virtual method to get os installer related config.

        :param config: os installer host configuration
        :type config: dict

        :returns: package related configuration for os installer.
        """
        return {}


INSTALLERS = {}


def get_installer_by_name(name, **kwargs):
    """Get package installer by name.

    :param name: package installer name.
    :type name: str

    :returns: instance of subclass of :class:`Installer`
    :raises: KeyError
    """
    if name not in INSTALLERS:
        logging.error('installer name %s is not in package installers %s',
                      name, INSTALLERS)
        raise KeyError('installer name %s is not in package INSTALLERS' % name)

    package_installer = INSTALLERS[name](**kwargs)
    logging.debug('got package installer %s', package_installer)
    return package_installer


def register(package_installer):
    """Register package installer.

    :param package_installer: subclass of :class:`Installer`
    :raises: KeyError
    """
    if package_installer.NAME in INSTALLERS:
        logging.error(
            'package installer %s is already in INSTALLERS %s',
            installer, INSTALLERS)
        raise KeyError(
            'package installer %s already registered' % package_installer)

    logging.info('register package installer: %s', package_installer)
    INSTALLERS[package_installer.NAME] = package_installer


def get_installer(**kwargs):
    """get default package installer from comapss setting."""
    return get_installer_by_name(setting.PACKAGE_INSTALLER, **kwargs)
