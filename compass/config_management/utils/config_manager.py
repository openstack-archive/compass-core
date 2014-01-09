"""
Module to get configs from provider and isntallers and update
them to provider and installers.

   .. moduleauthor:: Xiaodong wang ,xiaodongwang@huawei.com>
"""
import functools
import logging

from compass.config_management.installers import os_installer
from compass.config_management.installers import package_installer
from compass.config_management.providers import config_provider
from compass.config_management.utils import config_merger_callbacks
from compass.config_management.utils.config_merger import ConfigMapping
from compass.config_management.utils.config_merger import ConfigMerger
from compass.utils import util


CLUSTER_HOST_MERGER = ConfigMerger(
    mappings=[
        ConfigMapping(
            path_list=['/networking/interfaces/*'],
            from_upper_keys={'ip_start': 'ip_start', 'ip_end': 'ip_end'},
            to_key='ip',
            value=config_merger_callbacks.assign_ips
        ),
        ConfigMapping(
            path_list=['/role_assign_policy'],
            from_upper_keys={
                'policy_by_host_numbers': 'policy_by_host_numbers',
                'default': 'default'},
            to_key='/roles',
            value=config_merger_callbacks.assign_roles_by_host_numbers,
            override=config_merger_callbacks.override_if_empty
        ),
        ConfigMapping(
            path_list=['/dashboard_roles'],
            from_lower_keys={'lower_values': '/roles'},
            to_key='/has_dashboard_roles',
            value=config_merger_callbacks.has_intersection
        ),
        ConfigMapping(
            path_list=[
                '/networking/global',
                '/networking/interfaces/*/netmask',
                '/networking/interfaces/*/nic',
                '/networking/interfaces/*/promisc',
                '/security/*',
                '/partition',
            ]
        ),
        ConfigMapping(
            path_list=['/networking/interfaces/*'],
            from_upper_keys={'pattern': 'dns_pattern',
                             'clusterid': '/clusterid',
                             'search_path': '/networking/global/search_path'},
            from_lower_keys={'hostname': '/hostname'},
            to_key='dns_alias',
            value=functools.partial(config_merger_callbacks.assign_from_pattern,
                                    upper_keys=['search_path', 'clusterid'],
                                    lower_keys=['hostname'])
        ),
        ConfigMapping(
            path_list=['/networking/global'],
            from_upper_keys={'default': 'default_no_proxy'},
            from_lower_keys={'hostnames': '/hostname',
                             'ips': '/networking/interfaces/management/ip'},
            to_key='ignore_proxy',
            value=config_merger_callbacks.assign_noproxy
        )])


class ConfigManager(object):
    """
    Class is to get global/clsuter/host configs from provider,
    os installer, package installer, process them, and
    update them to provider, os installer, package installer.
    """

    def __init__(self):
        self.config_provider_ = config_provider.get_provider()
        logging.debug('got config provider: %s', self.config_provider_)
        self.package_installer_ = package_installer.get_installer()
        logging.debug('got package installer: %s', self.package_installer_)
        self.os_installer_ = os_installer.get_installer(
            self.package_installer_)
        logging.debug('got os installer: %s', self.os_installer_)

    def get_adapters(self):
        """Get adapter information from os installer and package installer.

        :returns: list of adapter information.

        .. note::
           For each adapter, the information is as
           {'name': '...', 'os': '...', 'target_system': '...'}
        """
        oses = self.os_installer_.get_oses()
        target_systems_per_os = self.package_installer_.get_target_systems(
            oses)
        adapters = []
        for os_version, target_systems in target_systems_per_os.items():
            for target_system in target_systems:
                adapters.append({
                    'name': '%s/%s' % (os_version, target_system),
                    'os': os_version,
                    'target_system': target_system})

        logging.debug('got adapters: %s', adapters)
        return adapters

    def get_roles(self, target_system):
        """Get all roles of the target system from package installer.

        :param target_system: the target distributed system to deploy.
        :type target_system: str

        :returns: list of role information.

        .. note::
           For each role, the information is as:
           {'name': '...', 'description': '...', 'target_system': '...'}
        """
        roles = self.package_installer_.get_roles(target_system)
        return [
            {
                'name': role,
                'description': description,
                'target_system': target_system
            } for role, description in roles.items()
        ]

    def get_global_config(self, os_version, target_system):
        """Get global config."""
        config = self.config_provider_.get_global_config()
        logging.debug('got global provider config from %s: %s',
                      self.config_provider_, config)

        os_config = self.os_installer_.get_global_config(
            os_version=os_version, target_system=target_system)
        logging.debug('got global os config from %s: %s',
                      self.os_installer_, os_config)
        package_config = self.package_installer_.get_global_config(
            os_version=os_version,
            target_system=target_system)
        logging.debug('got global package config from %s: %s',
                      self.package_installer_, package_config)

        util.merge_dict(config, os_config)
        util.merge_dict(config, package_config)
        return config

    def update_global_config(self, config, os_version, target_system):
        """update global config."""
        logging.debug('update global config: %s', config)
        self.config_provider_.update_global_config(config)
        self.os_installer_.update_global_config(
            config, os_version=os_version, target_system=target_system)
        self.package_installer_.update_global_config(
            config, os_version=os_version, target_system=target_system)

    def get_cluster_config(self, clusterid, os_version, target_system):
        """get cluster config."""
        config = self.config_provider_.get_cluster_config(clusterid)
        logging.debug('got cluster %s config from %s: %s',
                      clusterid, self.config_provider_, config)

        os_config = self.os_installer_.get_cluster_config(
            clusterid, os_version=os_version,
            target_system=target_system)
        logging.debug('got cluster %s config from %s: %s',
                      clusterid, self.os_installer_, os_config)

        package_config = self.package_installer_.get_cluster_config(
            clusterid, os_version=os_version,
            target_system=target_system)
        logging.debug('got cluster %s config from %s: %s',
                      clusterid, self.package_installer_, package_config)

        util.merge_dict(config, os_config)
        util.merge_dict(config, package_config)
        return config

    def clean_cluster_config(self, clusterid, os_version, target_system):
        config = self.config_provider_.get_cluster_config(clusterid)
        logging.debug('got cluster %s config from %s: %s',
                      clusterid, self.config_provider_, config)
        self.os_installer_.clean_cluster_config(
            clusterid, config, os_version=os_version,
            target_system=target_system)
        logging.debug('clean cluster %s config in %s',
                      clusterid, self.os_installer_)
        self.package_installer_.clean_cluster_config(
            clusterid, config, os_version=os_version,
            target_system=target_system)
        logging.debug('clean cluster %s config in %s',
                      clusterid, self.package_installer_)

    def update_cluster_config(self, clusterid, config,
                              os_version, target_system):
        """update cluster config."""
        logging.debug('update cluster %s config: %s', clusterid, config)
        self.config_provider_.update_cluster_config(clusterid, config)
        self.os_installer_.update_cluster_config(
            clusterid, config, os_version=os_version,
            target_system=target_system)
        self.package_installer_.update_cluster_config(
            clusterid, config, os_version=os_version,
            target_system=target_system)

    def get_host_config(self, hostid, os_version, target_system):
        """get host config."""
        config = self.config_provider_.get_host_config(hostid)
        logging.debug('got host %s config from %s: %s',
                      hostid, self.config_provider_, config)

        os_config = self.os_installer_.get_host_config(
            hostid, os_version=os_version,
            target_system=target_system)
        logging.debug('got host %s config from %s: %s',
                      hostid, self.os_installer_, os_config)

        package_config = self.package_installer_.get_host_config(
            hostid, os_version=os_version,
            target_system=target_system)
        logging.debug('got host %s config from %s: %s',
                      hostid, self.package_installer_, package_config)

        util.merge_dict(config, os_config)
        util.merge_dict(config, package_config)
        return config

    def get_host_configs(self, hostids, os_version, target_system):
        """get hosts' configs."""
        host_configs = {}
        for hostid in hostids:
            host_configs[hostid] = self.get_host_config(
                hostid, os_version, target_system)
        return host_configs

    def clean_host_config(self, hostid, os_version, target_system):
        """clean host config."""
        config = self.config_provider_.get_host_config(hostid)
        logging.debug('got host %s config from %s: %s',
                      hostid, self.config_provider_, config)
        self.os_installer_.clean_host_config(
            hostid, config, os_version=os_version,
            target_system=target_system)
        logging.debug('clean host %s config in %s',
                      hostid, self.os_installer_)
        self.package_installer_.clean_host_config(
            hostid, config, os_version=os_version,
            target_system=target_system)
        logging.debug('clean host %s config in %s',
                      hostid, self.package_installer_)

    def clean_host_configs(self, hostids, os_version, target_system):
        """clean hosts' configs."""
        for hostid in hostids:
            self.clean_host_config(hostid, os_version, target_system)

    def reinstall_host(self, hostid, os_version, target_system):
        """reinstall host."""
        config = self.config_provider_.get_host_config(hostid)
        logging.debug('got host %s config from %s: %s',
                      hostid, self.config_provider_, config)
        self.os_installer_.reinstall_host(
            hostid, config, os_version=os_version,
            target_system=target_system)
        logging.debug('reinstall host %s in %s',
                      hostid, self.os_installer_)
        self.package_installer_.reinstall_host(
            hostid, config, os_version=os_version,
            target_system=target_system)
        logging.debug('clean host %s in %s',
                      hostid, self.package_installer_)

    def reinstall_hosts(self, hostids, os_version, target_system):
        for hostid in hostids:
            self.reinstall_host(hostid, os_version, target_system)

    def update_host_config(self, hostid, config, os_version, target_system):
        """update host config."""
        logging.debug('update host %s config: %s', hostid, config)
        self.config_provider_.update_host_config(hostid, config)
        self.os_installer_.update_host_config(
            hostid, config, os_version=os_version,
            target_system=target_system)
        self.package_installer_.update_host_config(
            hostid, config, os_version=os_version,
            target_system=target_system)

    def update_host_configs(self, host_configs, os_version, target_system):
        """update host configs."""
        for hostid, host_config in host_configs.items():
            self.update_host_config(
                hostid, host_config, os_version, target_system)

    def update_cluster_and_host_configs(self,
                                        clusterid,
                                        hostids,
                                        update_hostids,
                                        os_version,
                                        target_system):
        """update cluster/host configs."""
        logging.debug('update cluster %s with all hosts %s and update: %s',
                      clusterid, hostids, update_hostids)

        global_config = self.get_global_config(os_version, target_system)
        self.update_global_config(global_config, os_version=os_version,
                                  target_system=target_system)

        cluster_config = self.get_cluster_config(
            clusterid, os_version=os_version, target_system=target_system)
        util.merge_dict(cluster_config, global_config, False)
        self.update_cluster_config(
            clusterid, cluster_config, os_version=os_version,
            target_system=target_system)

        host_configs = self.get_host_configs(
            hostids, os_version=os_version,
            target_system=target_system)
        CLUSTER_HOST_MERGER.merge(cluster_config, host_configs)
        update_host_configs = dict(
            [(hostid, host_config)
             for hostid, host_config in host_configs.items()
             if hostid in update_hostids])
        self.update_host_configs(
            update_host_configs, os_version=os_version,
            target_system=target_system)

    def sync(self):
        """sync os installer and package installer."""
        self.os_installer_.sync()
        self.package_installer_.sync()
