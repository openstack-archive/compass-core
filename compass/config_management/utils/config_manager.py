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
"""Module to get configs from provider and isntallers and update
   them to provider and installers.

   .. moduleauthor:: Xiaodong wang ,xiaodongwang@huawei.com>
"""
import functools
import logging

from compass.config_management import installers
from compass.config_management import providers
from compass.config_management.utils.config_merger import ConfigMapping
from compass.config_management.utils.config_merger import ConfigMerger
from compass.config_management.utils import config_merger_callbacks
from compass.config_management.utils.config_reference import ConfigReference
from compass.utils import setting_wrapper as setting
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
            path_list=['/role_mapping'],
        ),
        ConfigMapping(
            path_list=[
                '/networking/global/nameservers',
                '/networking/global/gateway',
                '/networking/global/proxy',
                '/networking/global/ntp_server',
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
            value=functools.partial(
                config_merger_callbacks.assign_from_pattern,
                upper_keys=['search_path', 'clusterid'],
                lower_keys=['hostname'])
        ),
        ConfigMapping(
            path_list=['/networking/global'],
            from_upper_keys={'default': 'default_no_proxy',
                             'clusterid': '/clusterid',
                             'noproxy_pattern': 'noproxy_pattern'},
            from_lower_keys={'hostnames': '/hostname',
                             'ips': '/networking/interfaces/management/ip'},
            to_key='ignore_proxy',
            value=config_merger_callbacks.assign_noproxy
        ),
        ConfigMapping(
            path_list=['/networking/global'],
            from_upper_keys={'pattern': 'search_path_pattern',
                             'search_path': 'search_path',
                             'clusterid': '/clusterid'},
            to_key='search_path',
            value=functools.partial(
                config_merger_callbacks.assign_from_pattern,
                upper_keys=['search_path', 'clusterid'])
        )])


class ConfigManager(object):
    """Class to get global/clsuter/host configs.

       .. note::
          The class is used to get global/clsuter/host configs
          from provider, os installer, package installer, process them,
          and update them to provider, os installer, package installer.
    """

    def __init__(self):
        self.config_provider_ = providers.get_provider()
        logging.debug('got config provider: %s', self.config_provider_)
        self.package_installer_ = installers.get_package_installer()
        logging.debug('got package installer: %s', self.package_installer_)
        self.os_installer_ = installers.get_os_installer(
            package_installer=self.package_installer_)
        logging.debug('got os installer: %s', self.os_installer_)

    def get_adapters(self):
        """Get adapter information from os installer and package installer.

        :returns: list of adapter information.

        .. note::
           For each adapter, the information is as
           {'name': '...', 'os': '...', 'target_system': '...'}
        """
        oses = self.os_installer_.get_oses()
        logging.debug('got oses %s from %s', oses, self.os_installer_)
        target_systems_per_os = self.package_installer_.get_target_systems(
            oses)
        logging.debug('got target_systems per os from %s: %s',
                      self.package_installer_, target_systems_per_os)
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
        logging.debug('got target system %s roles %s from %s',
                      target_system, roles, self.package_installer_)
        return [
            {
                'name': role,
                'description': description,
                'target_system': target_system
            } for role, description in roles.items()
        ]

    def update_adapters_from_installers(self):
        """update adapters from installers."""
        adapters = self.get_adapters()
        target_systems = set()
        roles_per_target_system = {}
        for adapter in adapters:
            target_systems.add(adapter['target_system'])

        for target_system in target_systems:
            roles_per_target_system[target_system] = self.get_roles(
                target_system)

        logging.debug('update adapters %s and '
                      'roles per target system %s to %s',
                      adapters, roles_per_target_system,
                      self.config_provider_)
        self.config_provider_.update_adapters(
            adapters, roles_per_target_system)

    def update_switch_filters(self):
        """Update switch filter from setting.SWITCHES."""
        if not hasattr(setting, 'SWITCHES'):
            logging.info('no switch configs to set')
            return

        switch_filters = util.get_switch_filters(setting.SWITCHES)
        logging.debug('update switch filters %s to %s',
                      switch_filters, self.config_provider_)
        self.config_provider_.update_switch_filters(switch_filters)

    def get_switch_and_machines(self):
        """Get switches and machines."""
        switches, machines_per_switch = (
            self.config_provider_.get_switch_and_machines())
        logging.debug('got switches %s from %s',
                      switches, self.config_provider_)
        logging.debug('got machines per switch %s from %s',
                      machines_per_switch, self.config_provider_)
        return (switches, machines_per_switch)

    def update_switch_and_machines(
        self, switches, switch_machines
    ):
        """Update switches and machines."""
        logging.debug('update switches %s to %s',
                      switches, self.config_provider_)
        logging.debug('update switch machines %s to %s',
                      switch_machines, self.config_provider_)
        self.config_provider_.update_switch_and_machines(
            switches, switch_machines)

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
        logging.debug('update global config to %s',
                      self.config_provider_)
        self.config_provider_.update_global_config(config)
        logging.debug('update global config to %s',
                      self.os_installer_)
        self.os_installer_.update_global_config(
            config, os_version=os_version, target_system=target_system)
        logging.debug('update global config to %s',
                      self.package_installer_)
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

    def update_cluster_config(self, clusterid, config,
                              os_version, target_system):
        """update cluster config."""
        logging.debug('update cluster %s config: %s', clusterid, config)
        logging.debug('update cluster %s config to %s',
                      clusterid, self.config_provider_)
        self.config_provider_.update_cluster_config(clusterid, config)
        logging.debug('update cluster %s config to %s',
                      clusterid, self.os_installer_)
        self.os_installer_.update_cluster_config(
            clusterid, config, os_version=os_version,
            target_system=target_system)
        logging.debug('update cluster %s config to %s',
                      clusterid, self.package_installer_)
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
        logging.debug('clean host %s config in %s',
                      hostid, self.config_provider_)
        self.config_provider_.clean_host_config(hostid)
        logging.debug('clean host %s config in %s',
                      hostid, self.os_installer_)
        self.os_installer_.clean_host_config(
            hostid, config, os_version=os_version,
            target_system=target_system)
        logging.debug('clean host %s config in %s',
                      hostid, self.package_installer_)
        self.package_installer_.clean_host_config(
            hostid, config, os_version=os_version,
            target_system=target_system)

    def clean_host_configs(self, hostids, os_version, target_system):
        """clean hosts' configs."""
        for hostid in hostids:
            self.clean_host_config(hostid, os_version, target_system)

    def reinstall_host(self, hostid, os_version, target_system):
        """reinstall host."""
        config = self.config_provider_.get_host_config(hostid)
        logging.debug('got host %s config from %s: %s',
                      hostid, self.config_provider_, config)
        logging.debug('reinstall host %s in %s',
                      hostid, self.config_provider_)
        self.config_provider_.reinstall_host(hostid)
        logging.debug('reinstall host %s in %s',
                      hostid, self.os_installer_)
        self.os_installer_.reinstall_host(
            hostid, config, os_version=os_version,
            target_system=target_system)
        logging.debug('reinstall host %s in %s',
                      hostid, self.package_installer_)
        self.package_installer_.reinstall_host(
            hostid, config, os_version=os_version,
            target_system=target_system)

    def reinstall_cluster(self, clusterid, os_version, target_system):
        """reinstall cluster."""
        config = self.config_provider_.get_cluster_config(clusterid)
        logging.debug('got cluster %s config from %s: %s',
                      clusterid, self.config_provider_, config)
        logging.debug('reinstall cluster %s in %s',
                      clusterid, self.config_provider_)
        self.config_provider_.reinstall_cluster(clusterid)
        logging.debug('reinstall cluster %s in %s',
                      clusterid, self.os_installer_)
        self.os_installer_.reinstall_cluster(
            clusterid, config, os_version=os_version,
            target_system=target_system)
        logging.debug('reinstall cluster %s in %s',
                      clusterid, self.package_installer_)
        self.package_installer_.reinstall_cluster(
            clusterid, config, os_version=os_version,
            target_system=target_system)

    def reinstall_hosts(self, hostids, os_version, target_system):
        """reinstall hosts."""
        for hostid in hostids:
            self.reinstall_host(hostid, os_version, target_system)

    def clean_host_installing_progress(self, hostid,
                                       os_version, target_system):
        """clean host installing progress."""
        config = self.config_provider_.get_host_config(hostid)
        logging.debug('got host %s config from %s: %s',
                      hostid, self.config_provider_, config)
        logging.debug('clean host %s installing progress in %s',
                      hostid, self.config_provider_)
        self.config_provider_.clean_host_installing_progress(hostid)
        logging.debug('clean host %s installing progress in %s',
                      hostid, self.os_installer_)
        self.os_installer_.clean_host_installing_progress(
            hostid, config, os_version=os_version,
            target_system=target_system)
        logging.debug('clean host %s installing progress in %s',
                      hostid, self.package_installer_)
        self.package_installer_.clean_host_installing_progress(
            hostid, config, os_version=os_version,
            target_system=target_system)

    def clean_hosts_installing_progress(self, hostids,
                                        os_version, target_system):
        """clean hosts installing progress."""
        for hostid in hostids:
            self.clean_host_installing_progress(
                hostid, os_version, target_system)

    def clean_cluster_installing_progress(self, clusterid,
                                          os_version, target_system):
        """clean cluster installing progress."""
        config = self.config_provider_.get_cluster_config(clusterid)
        logging.debug('got host %s config from %s: %s',
                      clusterid, self.config_provider_, config)
        logging.debug('clean cluster %s installing progress in %s',
                      clusterid, self.config_provider_)
        self.config_provider_.clean_cluster_installing_progress(clusterid)
        logging.debug('clean cluster %s installing progress in %s',
                      clusterid, self.os_installer_)
        self.os_installer_.clean_cluster_installing_progress(
            clusterid, config, os_version=os_version,
            target_system=target_system)
        logging.debug('clean cluster %s installing progress in %s',
                      clusterid, self.package_installer_)
        self.package_installer_.clean_cluster_installing_progress(
            clusterid, config, os_version=os_version,
            target_system=target_system)

    def clean_cluster_config(self, clusterid,
                             os_version, target_system):
        """clean cluster config."""
        config = self.config_provider_.get_cluster_config(clusterid)
        logging.debug('got cluster %s config from %s: %s',
                      clusterid, self.config_provider_, config)

        logging.debug('clean cluster %s config in %s',
                      clusterid, self.config_provider_)
        self.config_provider_.clean_cluster_config(clusterid)
        logging.debug('clean cluster %s config in %s',
                      clusterid, self.os_installer_)
        self.os_installer_.clean_cluster_config(
            clusterid, config, os_version=os_version,
            target_system=target_system)
        logging.debug('clean cluster %s config in %s',
                      clusterid, self.package_installer_)
        self.package_installer_.clean_cluster_config(
            clusterid, config, os_version=os_version,
            target_system=target_system)

    def update_host_config(self, hostid, config,
                           os_version, target_system):
        """update host config."""
        logging.debug('update host %s config: %s', hostid, config)
        logging.debug('update host %s config to %s',
                      hostid, self.config_provider_)
        self.config_provider_.update_host_config(hostid, config)
        logging.debug('update host %s config to %s',
                      hostid, self.os_installer_)
        self.os_installer_.update_host_config(
            hostid, config, os_version=os_version,
            target_system=target_system)
        logging.debug('update host %s config to %s',
                      hostid, self.package_installer_)
        self.package_installer_.update_host_config(
            hostid, config, os_version=os_version,
            target_system=target_system)

    def update_host_configs(self, host_configs, os_version, target_system):
        """update host configs."""
        for hostid, host_config in host_configs.items():
            self.update_host_config(
                hostid, host_config, os_version, target_system)

    def get_cluster_hosts(self, clusterid):
        """get cluster hosts."""
        hostids = self.config_provider_.get_cluster_hosts(clusterid)
        logging.debug('got hosts of cluster %s from %s: %s',
                      clusterid, self.config_provider_, hostids)
        return hostids

    def get_clusters(self):
        """get clusters."""
        clusters = self.config_provider_.get_clusters()
        logging.debug('got clusters from %s: %s',
                      self.config_provider_, clusters)
        return clusters

    def filter_cluster_and_hosts(self, cluster_hosts,
                                 os_versions, target_systems,
                                 cluster_properties_match,
                                 cluster_properties_name,
                                 host_properties_match,
                                 host_properties_name):
        """get filtered cluster and hosts configs."""
        logging.debug('filter cluster_hosts: %s', cluster_hosts)
        clusters_properties = []
        cluster_hosts_properties = {}
        for clusterid, hostids in cluster_hosts.items():
            cluster_config = self.get_cluster_config(
                clusterid, os_version=os_versions[clusterid],
                target_system=target_systems[clusterid])
            cluster_ref = ConfigReference(cluster_config)
            if cluster_ref.match(cluster_properties_match):
                clusters_properties.append(
                    cluster_ref.filter(cluster_properties_name))

            host_configs = self.get_host_configs(
                hostids, os_version=os_versions[clusterid],
                target_system=target_systems[clusterid])
            cluster_hosts_properties[clusterid] = []
            for _, host_config in host_configs.items():
                host_ref = ConfigReference(host_config)
                if host_ref.match(host_properties_match):
                    cluster_hosts_properties[clusterid].append(
                        host_ref.filter(host_properties_name))

        logging.debug('got clsuter properties: %s',
                      clusters_properties)
        logging.debug('got cluster hosts properties: %s',
                      cluster_hosts_properties)
        return (clusters_properties, cluster_hosts_properties)

    def reinstall_cluster_and_hosts(self,
                                    cluster_hosts,
                                    os_versions,
                                    target_systems):
        """reinstall clusters and hosts of each cluster."""
        logging.debug('reinstall cluster_hosts: %s', cluster_hosts)
        for clusterid, hostids in cluster_hosts.items():
            self.reinstall_hosts(
                hostids,
                os_version=os_versions[clusterid],
                target_system=target_systems[clusterid])
            self.reinstall_cluster(clusterid,
                                   os_version=os_versions[clusterid],
                                   target_system=target_systems[clusterid])

    def clean_cluster_and_hosts(self, cluster_hosts,
                                os_versions, target_systems):
        """clean clusters and hosts of each cluster."""
        logging.debug('clean cluster_hosts: %s', cluster_hosts)
        for clusterid, hostids in cluster_hosts.items():
            self.clean_host_configs(hostids,
                                    os_version=os_versions[clusterid],
                                    target_system=target_systems[clusterid])
            all_hostids = self.get_cluster_hosts(clusterid)
            if set(all_hostids) == set(hostids):
                self.clean_cluster_config(
                    clusterid,
                    os_version=os_versions[clusterid],
                    target_system=target_systems[clusterid])
            else:
                self.clean_cluster_installing_progress(
                    clusterid, os_version=os_versions[clusterid],
                    target_system=target_systems[clusterid])

    def clean_cluster_and_hosts_installing_progress(
        self, cluster_hosts, os_versions, target_systems
    ):
        """Clean clusters and hosts of each cluster intalling progress."""
        logging.debug('clean cluster_hosts installing progress: %s',
                      cluster_hosts)
        for clusterid, hostids in cluster_hosts.items():
            self.clean_hosts_installing_progress(
                hostids, os_version=os_versions[clusterid],
                target_system=target_systems[clusterid])
            self.clean_cluster_installing_progress(
                clusterid, os_version=os_versions[clusterid],
                target_system=target_systems[clusterid])

    def install_cluster_and_hosts(self,
                                  cluster_hosts,
                                  os_versions,
                                  target_systems):
        """update clusters and hosts of each cluster configs."""
        logging.debug('update cluster_hosts: %s', cluster_hosts)

        for clusterid, hostids in cluster_hosts.items():
            global_config = self.get_global_config(
                os_version=os_versions[clusterid],
                target_system=target_systems[clusterid])
            self.update_global_config(global_config,
                                      os_version=os_versions[clusterid],
                                      target_system=target_systems[clusterid])
            cluster_config = self.get_cluster_config(
                clusterid, os_version=os_versions[clusterid],
                target_system=target_systems[clusterid])
            util.merge_dict(cluster_config, global_config, False)
            self.update_cluster_config(
                clusterid, cluster_config,
                os_version=os_versions[clusterid],
                target_system=target_systems[clusterid])

            all_hostids = self.get_cluster_hosts(clusterid)
            host_configs = self.get_host_configs(
                all_hostids, os_version=os_versions[clusterid],
                target_system=target_systems[clusterid])
            CLUSTER_HOST_MERGER.merge(cluster_config, host_configs)
            update_host_configs = dict(
                [(hostid, host_config)
                 for hostid, host_config in host_configs.items()
                 if hostid in hostids])
            self.update_host_configs(
                update_host_configs,
                os_version=os_versions[clusterid],
                target_system=target_systems[clusterid])
            self.reinstall_hosts(
                update_host_configs.keys(),
                os_version=os_versions[clusterid],
                target_system=target_systems[clusterid])
            self.reinstall_cluster(clusterid,
                                   os_version=os_versions[clusterid],
                                   target_system=target_systems[clusterid])

    def sync(self):
        """sync os installer and package installer."""
        logging.info('config manager sync')
        logging.debug('sync %s', self.config_provider_)
        self.config_provider_.sync()
        logging.debug('sync %s', self.os_installer_)
        self.os_installer_.sync()
        logging.debug('sync %s', self.package_installer_)
        self.package_installer_.sync()
