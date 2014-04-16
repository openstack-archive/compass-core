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
import traceback

from compass.config_management.installers import package_installer
from compass.config_management.utils.config_translator import ConfigTranslator
from compass.config_management.utils.config_translator import KeyTranslator
from compass.config_management.utils import config_translator_callbacks
from compass.utils import setting_wrapper as setting
from compass.utils import util


FROM_GLOBAL_TRANSLATORS = {
    'openstack': ConfigTranslator(
        mapping={
            '/read_config_mapping': [KeyTranslator(
                translated_keys=(
                    config_translator_callbacks.get_keys_from_config_mapping),
                translated_value=(
                    config_translator_callbacks.get_value_from_config_mapping)
            )],
        }
    ),
}

TO_GLOBAL_TRANSLATORS = {
    'openstack': ConfigTranslator(
        mapping={
            '/test_roles/*': [KeyTranslator(
                translated_keys=[
                    functools.partial(
                        config_translator_callbacks.get_key_from_pattern,
                        from_pattern=r'^/test_roles/(?P<role>.*)$',
                        to_pattern=(
                            '/role_assign_policy/default'
                            '/dependencies/%(role)s'
                        )
                    )
                ],
                from_values={'testmode': '/testmode'},
                translated_value=functools.partial(
                    config_translator_callbacks.add_value,
                    check_value_callback=(
                        lambda value, value_list: (
                            set(value) & set(value_list))
                    ),
                    add_value_callback=(
                        lambda value, value_list: value_list.extend(value)
                    )
                ),
                override=True
            )],
        }
    ),
}

TO_CLUSTER_TRANSLATORS = {
    'openstack': ConfigTranslator(
        mapping={
            '/config_mapping': [KeyTranslator(
                translated_keys=(
                    config_translator_callbacks.get_keys_from_config_mapping),
                translated_value=(
                    config_translator_callbacks.get_value_from_config_mapping)
            )],
            '/testmode': [KeyTranslator(
                translated_keys=['/debugging/debug', '/debugging/verbose'],
                translated_value=functools.partial(
                    config_translator_callbacks.set_value,
                    return_value_callback=lambda value: str(value)
                ),
                override=True
            )],
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
        import chef
        super(Installer, self).__init__(**kwargs)
        self.installer_url_ = setting.CHEF_INSTALLER_URL
        self.global_databag_name_ = setting.CHEF_GLOBAL_DATABAG_NAME
        self.api_ = chef.autoconfigure()
        self.tmp_databags_ = {}
        self.tmp_databag_items_ = {}
        logging.debug('%s instance created', self)

    def __repr__(self):
        return '%s[name=%s,installer_url=%s,global_databag_name=%s]' % (
            self.__class__.__name__, self.NAME, self.installer_url_,
            self.global_databag_name_)

    @classmethod
    def _cluster_databag_name(cls, clusterid):
        """get cluster databag name."""
        return '%s' % clusterid

    @classmethod
    def _get_client_name(cls, fullname):
        """get client name."""
        return cls._get_node_name(fullname)

    def _clean_host_attributes(self, config, target_system):
        """clean node attributes about target system."""
        import chef
        node_name = self._get_node_name(config['fullname'])
        client_name = self._get_client_name(config['fullname'])
        node = chef.Node(node_name, api=self.api_)
        roles_per_target_system = node.get('roles_per_target_system', {})
        if target_system in roles_per_target_system:
            del roles_per_target_system[target_system]

        node['roles_per_target_system'] = roles_per_target_system
        if not roles_per_target_system:
            try:
                node.delete()
                client = chef.Client(client_name, api=self.api_)
                client.delete()
                logging.debug(
                    'delete %s for host %s ', target_system, node_name)
            except Exception:
                logging.debug(
                    'failed to delete %s for host %s: %s',
                    target_system, node_name,
                    ''.join(traceback.format_stack()))

        else:
            node.run_list = []
            for _, roles in node['roles'].items():
                for role in roles:
                    node.run_list.append('role[%s]' % role)

            node.save()
            logging.debug('node %s is updated for %s',
                          node_name, target_system)

    def _update_host_attributes(self, config, target_system):
        """chef manage node attributes about target system."""
        import chef
        node_name = self._get_node_name(config['fullname'])
        node = chef.Node(node_name, api=self.api_)
        node['cluster'] = self._cluster_databag_name(config['clusterid'])
        roles_per_target_system = node.get('roles_per_target_system', {})
        roles_per_target_system[target_system] = config['roles']
        node['roles_per_target_system'] = roles_per_target_system

        node.run_list = []
        for _, roles in roles_per_target_system.items():
            for role in roles:
                node.run_list.append('role[%s]' % role)

        node.save()
        logging.debug('update %s for host %s',
                      target_system, node_name)

    @classmethod
    def _get_node_name(cls, fullname):
        """get node name."""
        return fullname

    def os_installer_config(self, config, target_system, **kwargs):
        """get os installer config."""
        return {
            '%s_url' % self.NAME: self.installer_url_,
            'chef_client_name': self._get_client_name(config['fullname']),
            'chef_node_name': self._get_node_name(config['fullname'])
        }

    def get_target_systems(self, oses):
        """get target systems."""
        import chef
        databags = chef.DataBag.list(api=self.api_)
        target_systems = {}
        for os_version in oses:
            target_systems[os_version] = []

        for databag in databags:
            target_system = databag
            global_databag_item = self._get_global_databag_item(target_system)
            support_oses = global_databag_item['support_oses']
            for os_version in oses:
                for support_os in support_oses:
                    if fnmatch.fnmatch(os_version, support_os):
                        target_systems[os_version].append(target_system)
                        break

        return target_systems

    def get_roles(self, target_system):
        """get supported roles."""
        global_databag_item = self._get_global_databag_item(target_system)
        return global_databag_item['all_roles']

    def _get_databag(self, target_system):
        """get databag."""
        import chef
        if target_system not in self.tmp_databags_:
            self.tmp_databags_[target_system] = chef.DataBag(
                target_system, api=self.api_)

        return self.tmp_databags_[target_system]

    def _get_databag_item(self, target_system, bag_item_name):
        """get databag item."""
        import chef
        databag_items = self.tmp_databag_items_.setdefault(
            target_system, {})
        if bag_item_name not in databag_items:
            databag = self._get_databag(target_system)
            databag_items[bag_item_name] = chef.DataBagItem(
                databag, bag_item_name, api=self.api_)

        return dict(databag_items[bag_item_name])

    def _update_databag_item(
        self, target_system, bag_item_name, config, save=True
    ):
        """update databag item."""
        import chef
        databag_items = self.tmp_databag_items_.setdefault(
            target_system, {})
        if bag_item_name not in databag_items:
            databag = self._get_databag(target_system)
            databag_items[bag_item_name] = chef.DataBagItem(
                databag, bag_item_name, api=self.api_)

        bag_item = databag_items[bag_item_name]
        for key, value in config.items():
            bag_item[key] = value

        if save:
            bag_item.save()
            logging.debug('save databag item %s to target system %s',
                          bag_item_name, target_system)
        else:
            logging.debug(
                'ignore saving databag item %s to target system %s',
                bag_item_name, target_system)

    def _clean_databag_item(self, target_system, bag_item_name):
        """clean databag item."""
        import chef
        databag_items = self.tmp_databag_items_.setdefault(
            target_system, {})
        if bag_item_name not in databag_items:
            databag = self._get_databag(target_system)
            databag_items[bag_item_name] = chef.DataBagItem(
                databag, bag_item_name, api=self.api_)

        bag_item = databag_items[bag_item_name]
        try:
            bag_item.delete()
            logging.debug(
                'databag item %s is removed from target_system %s',
                bag_item_name, target_system)
        except Exception:
            logging.debug(
                'no databag item %s to delete from target_system %s: %s',
                bag_item_name, target_system,
                ''.join(traceback.format_stack()))

        del databag_items[bag_item_name]

    def _get_global_databag_item(self, target_system):
        """get global databag item."""
        return self._get_databag_item(
            target_system, self.global_databag_name_)

    def _clean_global_databag_item(self, target_system):
        """clean global databag item."""
        self._clean_databag_item(
            target_system, self.global_databag_name_)

    def _update_global_databag_item(self, target_system, config):
        """update global databag item."""
        self._update_databag_item(
            target_system, self.global_databag_name_, config, save=False)

    def _get_cluster_databag_item(self, target_system, clusterid):
        """get cluster databag item."""
        return self._get_databag_item(
            target_system, self._cluster_databag_name(clusterid))

    def _clean_cluster_databag_item(self, target_system, clusterid):
        """clean cluster databag item."""
        self._clean_databag_item(
            target_system, self._cluster_databag_name(clusterid))

    def _update_cluster_databag_item(self, target_system, clusterid, config):
        """update cluster databag item."""
        self._update_databag_item(
            target_system, self._cluster_databag_name(clusterid),
            config, save=True)

    def get_global_config(self, target_system, **kwargs):
        """get global config."""
        bag_item = self._get_global_databag_item(target_system)
        return FROM_GLOBAL_TRANSLATORS[target_system].translate(bag_item)

    def get_cluster_config(self, clusterid, target_system, **kwargs):
        """get cluster config."""
        global_bag_item = self._get_global_databag_item(
            target_system)
        cluster_bag_item = self._get_cluster_databag_item(
            target_system, clusterid)
        util.merge_dict(cluster_bag_item, global_bag_item, False)

        return FROM_CLUSTER_TRANSLATORS[target_system].translate(
            cluster_bag_item)

    def clean_cluster_config(self, clusterid, config,
                             target_system, **kwargs):
        """clean cluster config."""
        self._clean_cluster_databag_item(target_system, clusterid)

    def update_global_config(self, config, target_system, **kwargs):
        """update global config."""
        global_bag_item = self._get_global_databag_item(target_system)
        translated_config = TO_GLOBAL_TRANSLATORS[target_system].translate(
            config)

        util.merge_dict(global_bag_item, translated_config, True)
        self._update_global_databag_item(target_system, global_bag_item)

    def update_cluster_config(self, clusterid, config,
                              target_system, **kwargs):
        """update cluster config."""
        self.clean_cluster_config(clusterid, config,
                                  target_system, **kwargs)
        global_bag_item = self._get_global_databag_item(target_system)
        cluster_bag_item = self._get_cluster_databag_item(
            target_system, clusterid)
        util.merge_dict(cluster_bag_item, global_bag_item, False)
        translated_config = TO_CLUSTER_TRANSLATORS[target_system].translate(
            config)
        util.merge_dict(cluster_bag_item, translated_config, True)
        self._update_cluster_databag_item(
            target_system, clusterid, cluster_bag_item)

    def clean_host_config(self, hostid, config, target_system, **kwargs):
        """clean host config."""
        self._clean_host_attributes(config, target_system)

    def reinstall_host(self, hostid, config, target_system, **kwargs):
        """reinstall host."""
        self._clean_host_attributes(config, target_system)
        self._update_host_attributes(config, target_system)

    def update_host_config(self, hostid, config, target_system, **kwargs):
        """update host config."""
        clusterid = config['clusterid']
        global_bag_item = self._get_global_databag_item(target_system)
        cluster_bag_item = self._get_cluster_databag_item(
            target_system, clusterid)
        util.merge_dict(cluster_bag_item, global_bag_item, False)
        util.merge_dict(config, {
            'client_name': self._get_client_name(config['fullname']),
            'node_name': self._get_node_name(config['fullname'])
        })
        translated_config = TO_HOST_TRANSLATORS[target_system].translate(
            config)
        util.merge_dict(cluster_bag_item, translated_config, True)
        self._update_cluster_databag_item(
            target_system, clusterid, cluster_bag_item)
        self._update_host_attributes(config, target_system)


package_installer.register(Installer)
