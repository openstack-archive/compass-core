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

"""package instaler chef plugin.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@gmail.com>
"""
import fnmatch
import functools
import logging

from compass.config_management.installers import package_installer
from compass.config_management.utils.config_translator import ConfigTranslator
from compass.config_management.utils.config_translator import KeyTranslator
from compass.config_management.utils import config_translator_callbacks
from compass.utils import setting_wrapper as setting
from compass.utils import util


TO_CLUSTER_TRANSLATORS = {
    'openstack': ConfigTranslator(
        mapping={
            '/config_mapping': [KeyTranslator(
                translated_keys=(
                    config_translator_callbacks.get_keys_from_config_mapping),
                translated_value=(
                    config_translator_callbacks.get_value_from_config_mapping)
            )]
        }
    ),
}


FROM_CLUSTER_TRANSLATORS = {
    'openstack': ConfigTranslator(
        mapping={
            '/role_assign_policy': [KeyTranslator(
                translated_keys=['/role_assign_policy']
            )],
            '/config_mapping': [KeyTranslator(
                translated_keys=['/config_mapping']
            )],
            '/role_mapping': [KeyTranslator(
                translated_keys=['/role_mapping']
            )],
            '/read_config_mapping': [KeyTranslator(
                translated_keys=(
                    config_translator_callbacks.get_keys_from_config_mapping),
                translated_value=(
                    config_translator_callbacks.get_value_from_config_mapping)
            )],
        }
    ),
}


TO_HOST_TRANSLATORS = {
    'openstack': ConfigTranslator(
        mapping={
            '/roles': [KeyTranslator(
                translated_keys=(
                    config_translator_callbacks.get_keys_from_role_mapping),
                from_keys={'mapping': '/role_mapping'},
                translated_value=(
                    config_translator_callbacks.get_value_from_role_mapping),
                from_values={'mapping': '/role_mapping'}
            ), KeyTranslator(
                translated_keys=[functools.partial(
                    config_translator_callbacks.get_key_from_pattern,
                    to_pattern='/node_mapping/%(node_name)s/roles'
                )],
                from_keys={'node_name': '/node_name'}
            )],
            '/networking/interfaces/management/ip': [KeyTranslator(
                translated_keys=[functools.partial(
                    config_translator_callbacks.get_key_from_pattern,
                    to_pattern='/node_mapping/%(node_name)s/management_ip'
                )],
                from_keys={'node_name': '/node_name'}
            )],
            '/haproxy_roles': [KeyTranslator(
                translated_keys=['/ha/status'],
                translated_value='enable',
                override=config_translator_callbacks.override_if_any,
                override_conditions={'haproxy_roles': '/haproxy_roles'}
            )],
            '/haproxy/router_id': [KeyTranslator(
                translated_keys=[functools.partial(
                    config_translator_callbacks.get_key_from_pattern,
                    to_pattern='/ha/keepalived/router_ids/%(node_name)s'
                )],
                from_keys={'node_name': '/node_name'}
            )],
            '/haproxy/priority': [KeyTranslator(
                translated_keys=[functools.partial(
                    config_translator_callbacks.get_key_from_pattern,
                    to_pattern=(
                        '/ha/keepalived/instance_name/'
                        'priorities/%(node_name)s'
                    )
                )],
                from_keys={'node_name': '/node_name'}
            )],
            '/haproxy/state': [KeyTranslator(
                translated_keys=[functools.partial(
                    config_translator_callbacks.get_key_from_pattern,
                    to_pattern=(
                        '/ha/keepalived/instance_name/'
                        'states/%(node_name)s'
                    )
                )],
                from_keys={'node_name': '/node_name'}
            )],
        }
    ),
}


class Installer(package_installer.Installer):
    """chef package installer."""
    NAME = 'chef'

    def __init__(self, **kwargs):
        super(Installer, self).__init__(**kwargs)
        import chef
        self.installer_url_ = setting.CHEF_INSTALLER_URL
        self.global_databag_name_ = setting.CHEF_GLOBAL_DATABAG_NAME
        self.api_ = chef.autoconfigure()
        logging.debug('%s instance created', self)

    def __repr__(self):
        return '%s[name=%s,installer_url=%s,global_databag_name=%s]' % (
            self.__class__.__name__, self.NAME, self.installer_url_,
            self.global_databag_name_)

    @classmethod
    def _cluster_databag_name(cls, clusterid, target_system):
        """get cluster databag name."""
        return '%s_%s' % (target_system, clusterid)

    @classmethod
    def _get_client_name(cls, fullname, target_system):
        """get client name."""
        return cls._get_node_name(fullname, target_system)

    def _update_host_attributes(self, config, target_system):
        """chef manage node attributes"""
        from chef import Node
        roles = config['roles']
        node_name = "%s.%s" % (target_system, config['fullname'])
        node = Node(node_name, api=self.api_)
        node['cluster'] = target_system + '_' + str(config['clusterid'])
        for role in roles:
            node.run_list.append('role[%s]' % role)
        node.save()

    @classmethod
    def _get_node_name(cls, fullname, target_system):
        """get node name."""
        return '%s.%s' % (target_system, fullname)

    def os_installer_config(self, config, target_system, **kwargs):
        """get os installer config."""
        return {
            '%s_url' % self.NAME: self.installer_url_,
            'run_list': ','.join(
                ['"role[%s]"' % role for role in config['roles'] if role]),
            'cluster_databag': self._cluster_databag_name(
                config['clusterid'], target_system),
            'chef_client_name': self._get_client_name(
                config['fullname'], target_system),
            'chef_node_name': self._get_node_name(
                config['fullname'], target_system)
        }

    def get_target_systems(self, oses):
        """get target systems."""
        from chef import DataBag
        databags = DataBag.list(api=self.api_)
        target_systems = {}
        for os_version in oses:
            target_systems[os_version] = []

        for databag in databags:
            target_system = databag
            global_databag_item = self._get_global_databag_item(
                self._get_databag(target_system))
            support_oses = global_databag_item['support_oses']
            for os_version in oses:
                for support_os in support_oses:
                    if fnmatch.fnmatch(os_version, support_os):
                        target_systems[os_version].append(target_system)
                        break

        return target_systems

    def get_roles(self, target_system):
        """get supported roles."""
        global_databag_item = self._get_global_databag_item(
            self._get_databag(target_system))
        return global_databag_item['all_roles']

    def _get_databag(self, target_system):
        """get databag."""
        import chef
        return chef.DataBag(target_system, api=self.api_)

    def _get_databag_item(self, bag, bag_item_name):
        """get databag item."""
        from chef import DataBagItem
        return DataBagItem(bag, bag_item_name, api=self.api_)

    def _get_global_databag_item(self, bag):
        """get global databag item."""
        return self._get_databag_item(
            bag, self.global_databag_name_)

    def _get_cluster_databag_item(self, bag, clusterid, target_system):
        """get cluster databag item."""
        return self._get_databag_item(
            bag, self._cluster_databag_name(clusterid, target_system))

    def get_cluster_config(self, clusterid, target_system, **kwargs):
        """get cluster config."""
        bag = self._get_databag(target_system)
        global_bag_item = dict(self._get_global_databag_item(bag))
        bag_item = dict(self._get_cluster_databag_item(
            bag, clusterid, target_system))
        util.merge_dict(bag_item, global_bag_item, False)

        return FROM_CLUSTER_TRANSLATORS[target_system].translate(bag_item)

    def clean_cluster_config(self, clusterid, config,
                             target_system, **kwargs):
        """clean cluster config."""
        try:
            bag = self._get_databag(target_system)
            bag_item = self._get_cluster_databag_item(
                bag, clusterid, target_system)
            bag_item.delete()
            logging.debug('databag item is removed for cluster %s '
                          'config %s target_system %s',
                          clusterid, config, target_system)
        except Exception:
            logging.debug('no databag item to delete for cluster %s '
                          'config %s target_system %s',
                          clusterid, config, target_system)

    def update_cluster_config(self, clusterid, config,
                              target_system, **kwargs):
        """update cluster config."""
        self.clean_cluster_config(clusterid, config,
                                  target_system, **kwargs)
        bag = self._get_databag(target_system)
        global_bag_item = dict(self._get_global_databag_item(bag))
        bag_item = self._get_cluster_databag_item(
            bag, clusterid, target_system)
        bag_item_dict = dict(bag_item)
        util.merge_dict(bag_item_dict, global_bag_item, False)
        translated_config = TO_CLUSTER_TRANSLATORS[target_system].translate(
            config)
        util.merge_dict(bag_item_dict, translated_config)

        for key, value in bag_item_dict.items():
            bag_item[key] = value

        bag_item.save()

    def _clean_client(self, hostid, config, target_system, **kwargs):
        """clean client."""
        from chef import Client
        try:
            client = Client(
                self._get_client_name(
                    config['fullname'], target_system),
                api=self.api_)
            client.delete()
            logging.debug('client is removed for host %s '
                          'config %s target_system %s',
                          hostid, config, target_system)
        except Exception:
            logging.debug('no client to delete for host %s '
                          'config %s target_system %s',
                          hostid, config, target_system)

    def _clean_node(self, hostid, config, target_system, **kwargs):
        """clean node."""
        from chef import Node
        try:
            node = Node(
                self._get_node_name(
                    config['fullname'], target_system),
                api=self.api_
            )
            node.delete()
            logging.debug('node is removed for host %s '
                          'config %s target_system %s',
                          hostid, config, target_system)
        except Exception:
            logging.debug('no node to delete for host %s '
                          'config %s target_system %s',
                          hostid, config, target_system)

    def clean_host_config(self, hostid, config, target_system, **kwargs):
        """clean host config."""
        self._clean_client(hostid, config, target_system, **kwargs)
        self._clean_node(hostid, config, target_system, **kwargs)

    def reinstall_host(self, hostid, config, target_system, **kwargs):
        """reinstall host."""
        self._clean_client(hostid, config, target_system, **kwargs)
        self._clean_node(hostid, config, target_system, **kwargs)
        self._update_host_attributes(config, target_system)

    def update_host_config(self, hostid, config, target_system, **kwargs):
        """update host cnfig."""
        self.clean_host_config(hostid, config,
                               target_system=target_system, **kwargs)
        clusterid = config['clusterid']
        bag = self._get_databag(target_system)
        global_bag_item = dict(self._get_global_databag_item(bag))
        bag_item = self._get_cluster_databag_item(
            bag, clusterid, target_system)
        bag_item_dict = dict(bag_item)
        util.merge_dict(bag_item_dict, global_bag_item, False)
        util.merge_dict(config, {
            'client_name': self._get_client_name(
                config['fullname'], target_system),
            'node_name': self._get_node_name(
                config['fullname'], target_system)
        })
        translated_config = TO_HOST_TRANSLATORS[target_system].translate(
            config)
        util.merge_dict(bag_item_dict, translated_config)

        for key, value in bag_item_dict.items():
            bag_item[key] = value

        bag_item.save()

        self._update_host_attributes(config, target_system)

package_installer.register(Installer)
