"""package instaler chef plugin.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@gmail.com>
"""
import fnmatch
import logging

from compass.utils import util
from compass.config_management.installers import package_installer
from compass.config_management.utils.config_translator import ConfigTranslator
from compass.config_management.utils.config_translator import KeyTranslator
from compass.config_management.utils import config_translator_callbacks
from compass.utils import setting_wrapper as setting


TO_CLUSTER_TRANSLATORS = {
    'openstack': ConfigTranslator(
        mapping={
            '/security/console_credentials': [KeyTranslator(
                translated_keys=['credential/identity/users/admin'],
            )],
            '/security/service_credentials': [KeyTranslator(
                translated_keys=[
                    '/credential/identity/users/compute',
                    '/credential/identity/users/image',
                    '/credential/identity/users/metering',
                    '/credential/identity/users/network',
                    '/credential/identity/users/object-store',
                    '/credential/identity/users/volume',
                    '/credential/mysql/compute',
                    '/credential/mysql/dashboard',
                    '/credential/mysql/identity',
                    '/credential/mysql/image',
                    '/credential/mysql/metering',
                    '/credential/mysql/network',
                    '/credential/mysql/super',
                    '/credential/mysql/volume',
                ]
            )],
            '/networking/interfaces/management/nic': [KeyTranslator(
                translated_keys=['/networking/control/interface'],
            )],
            '/networking/global/ntp_server': [KeyTranslator(
                translated_keys=['/ntp/ntpserver']
            )],
            '/networking/interfaces/storage/nic': [KeyTranslator(
                translated_keys=['/networking/storage/interface']
            )],
            '/networking/interfaces/public/nic': [KeyTranslator(
                translated_keys=['/networking/public/interface']
            )],
            '/networking/interfaces/tenant/nic': [KeyTranslator(
                translated_keys=['/networking/tenant/interface']
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
            '/dashboard_roles': [KeyTranslator(
                translated_keys=['/dashboard_roles']
            )],
        }
    ),
}


TO_HOST_TRANSLATORS = {
    'openstack': ConfigTranslator(
        mapping={
            '/networking/interfaces/management/ip': [KeyTranslator(
                translated_keys=[
                    '/db/mysql/bind_address',
                    '/mq/rabbitmq/bind_address',
                    '/endpoints/compute/metadata/host',
                    '/endpoints/compute/novnc/host',
                    '/endpoints/compute/service/host',
                    '/endpoints/compute/xvpvnc/host',
                    '/endpoints/ec2/admin/host',
                    '/endpoints/ec2/service/host',
                    '/endpoints/identity/admin/host',
                    '/endpoints/identity/service/host',
                    '/endpoints/image/registry/host',
                    '/endpoints/image/service/host',
                    '/endpoints/metering/service/host',
                    '/endpoints/network/service/host',
                    '/endpoints/volume/service/host',
                ],
                translated_value=config_translator_callbacks.get_value_if,
                from_values={'condition': '/has_dashboard_roles'}
            )],
        }
    ),
}


class Installer(package_installer.Installer):
    """chef package installer."""
    NAME = 'chef'

    def __init__(self):
        import chef
        self.installer_url_ = setting.CHEF_INSTALLER_URL
        self.global_databag_name_ = setting.CHEF_GLOBAL_DATABAG_NAME
        self.api_ = chef.autoconfigure()
        logging.debug('%s instance created', self)

    def __repr__(self):
        return '%s[name=%s,installer_url=%s,global_databag_name=%s]' % (
            self.__class__.__name__, self.installer_url_,
            self.NAME, self.global_databag_name_)

    @classmethod
    def _cluster_databag_name(cls, clusterid, target_system):
        """get cluster databag name"""
        return '%s_%s' % (target_system, str(clusterid))

    @classmethod
    def _get_client_name(cls, hostname, clusterid, target_system):
        """get client name"""
        return cls._get_node_name(hostname, clusterid, target_system)

    @classmethod
    def _get_node_name(cls, hostname, clusterid, target_system):
        """get node name"""
        return '%s_%s_%s' % (hostname, target_system, clusterid)

    def os_installer_config(self, config, target_system, **kwargs):
        """get os installer config."""
        clusterid = config['clusterid']
        roles = config['roles']
        return {
            '%s_url' % self.NAME: self.installer_url_,
            'run_list': ','.join(
                ['"role[%s]"' % role for role in roles if role]),
            'cluster_databag': self._cluster_databag_name(
                clusterid, target_system),
            'chef_client_name': self._get_client_name(
                config['hostname'], config['clusterid'],
                target_system),
            'chef_node_name': self._get_node_name(
                config['hostname'], config['clusterid'],
                target_system)
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
        except Exception as error:
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
        """clean client"""
        from chef import Client
        try:
            client = Client(
                self._get_client_name(
                    config['hostname'], config['clusterid'], target_system),
                api=self.api_)
            client.delete()
            logging.debug('client is removed for host %s '
                          'config %s target_system %s',
                          hostid, config, target_system)
        except Exception as error:
            logging.debug('no client to delete for host %s '
                          'config %s target_system %s',
                          hostid, config, target_system)

    def _clean_node(self, hostid, config, target_system, **kwargs):
        """clean node"""
        from chef import Node
        try:
            node = Node(
                self._get_node_name(
                    config['hostname'], config['clusterid'], target_system),
                api=self.api_
            ) 
            node.delete()
            logging.debug('node is removed for host %s '
                          'config %s target_system %s',
                          hostid, config, target_system)
        except Exception as error:
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

    def update_host_config(self, hostid, config, target_system, **kwargs):
        """update host cnfig."""
        self.clean_host_config(hostid, config,
                               target_system=target_system, **kwargs)
        clusterid = config['clusterid']
        bag = self._get_databag(target_system)
        global_bag_item = dict(self._get_global_databag_item(bag))
        bag_item = self._get_cluster_databag_item(bag, clusterid, target_system)
        bag_item_dict = dict(bag_item)
        util.merge_dict(bag_item_dict, global_bag_item, False)
        translated_config = TO_HOST_TRANSLATORS[target_system].translate(
            config)
        util.merge_dict(bag_item_dict, translated_config)

        for key, value in bag_item_dict.items():
            bag_item[key] = value

        bag_item.save()


package_installer.register(Installer)
