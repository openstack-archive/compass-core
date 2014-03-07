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

"""Module to provide interface to read/update global/cluster/host config.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import logging

from abc import ABCMeta

from compass.utils import setting_wrapper as setting


class ConfigProvider(object):
    """Interface for config provider"""
    __metaclass__ = ABCMeta

    NAME = 'config_provider'

    def __repr__(self):
        return '%s[%s]' % (self.__class__.__name__, self.NAME)

    def get_global_config(self):
        """Virtual method to get global config.

        :returns: global configuration as dict.
        """
        return {}

    def get_cluster_config(self, clusterid):
        """Virtual method to get cluster config.

        :param clusterid: id of the cluster to get configuration.
        :type clusterid: int

        :returns: cluster configuration as dict.
        """
        return {}

    def update_adapters(self, adapters, roles_per_target_system):
        """Virtual method to update adapters.

        :param adapters: adapters to update
        :type adapters: list of dict
        :param roles_per_target_system: roles per target_system to update
        :type roles_per_target_system: dict of str to dict.
        """
        pass

    def update_switch_filters(self, switch_filters):
        """Virtual method to update switch filters.

        :param switch_filters: switch filters to update.
        :type switch_filters: list of dict
        """
        pass

    def get_host_config(self, hostid):
        """Virtual method to get host config.

        :param hostid: id of the host to get configuration.
        :type hostid: int

        :returns: host configuration as dict.
        """
        return {}

    def update_global_config(self, config):
        """Virtual method to update global config.

        :param config: global configuration.
        :type config: dict
        """
        pass

    def update_cluster_config(self, clusterid, config):
        """Virtual method to update cluster config.

        :param clusterid: the id of the cluster to update configuration.
        :type clusterid: int
        :param config: cluster configuration.
        :type config: dict
        """
        pass

    def update_host_config(self, hostid, config):
        """Virtual method to update host config.

        :param hostid: the id of the host to update configuration.
        :type hostid: int
        :param config: host configuration.
        :type config: dict
        """
        pass

    def clean_host_config(self, hostid):
        """Virtual method to clean host config.

        :param hostid; the id of the host to clean.
        :type hostid: int
        """
        pass

    def reinstall_host(self, hostid):
        """Virtual method to reintall host.

        :param hostid: the id of the host to reinstall.
        :type hostid: int.
        """
        pass

    def reinstall_cluster(self, clusterid):
        """Virtual method to reinstall cluster.

        :param clusterid: the id of the cluster to reinstall.
        :type clusterid: int
        """
        pass

    def clean_host_installing_progress(self, hostid):
        """Virtual method to clean host installing progress.

        :param hostid: the id of the host to clean the installing progress
        :type hostid: int
        """
        pass

    def clean_cluster_installing_progress(self, clusterid):
        """Virtual method to clean cluster installing progress.

        :param clusterid: the id of the cluster to clean installing progress
        :type clusterid: int
        """
        pass

    def clean_cluster_config(self, clusterid):
        """Virtual method to clean cluster config

        :param clsuterid: the id of the cluster to clean
        :type clusterid: int
        """
        pass

    def get_cluster_hosts(self, clusterid):
        """Virtual method to get hosts of given cluster.

        :param clusterid: the id of the clsuter
        :type clsuterid: int
        """
        return []

    def get_clusters(self):
        """Virtual method to get cluster list."""
        return []

    def get_switch_and_machines(self):
        """Virtual method to get switches and machines.

        :returns: switches as list, machines per switch as dict of str to list
        """
        return ([], {})

    def update_switch_and_machines(
        self, switches, switch_machines
    ):
        """Virtual method to update switches and machines.

        :param switches: switches to update
        :type switches: list of dict.
        :param switch_machines: machines of each switch to update
        :type switch_machines: dict of str to list of dict.
        """
        pass

    def sync(self):
        """Virtual method to sync data in provider."""
        pass


PROVIDERS = {}


def get_provider():
    """get default provider from compass setting."""
    return get_provider_by_name(setting.PROVIDER_NAME)


def get_provider_by_name(name):
    """get provider by provider name.

    :param name: provider name.
    :type name: str

    :returns: instance of subclass of :class:`ConfigProvider`.
    :raises: KeyError
    """
    if name not in PROVIDERS:
        logging.error('provider name %s is not found in providers %s',
                      name, PROVIDERS)
        raise KeyError('provider %s is not found in PROVIDERS' % name)

    provider = PROVIDERS[name]()
    logging.debug('got provider %s', provider)
    return provider


def register_provider(provider):
    """register provider.

    :param provider: class inherited from :class:`ConfigProvider`
    :raises: KeyError
    """
    if provider.NAME in PROVIDERS:
        logging.error('provider %s name %s is already registered in %s',
                      provider, provider.NAME, PROVIDERS)
        raise KeyError('provider %s is already registered in PROVIDERS' %
                       provider.NAME)
    logging.debug('register provider %s', provider.NAME)
    PROVIDERS[provider.NAME] = provider
