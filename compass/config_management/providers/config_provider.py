"""Module to provide interface to read/update global/cluster/host config.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import logging

from compass.utils import setting_wrapper as setting


class ConfigProvider(object):
    """Interface for config provider"""

    NAME = 'config_provider'

    def __init__(self):
        raise NotImplementedError('%s is not implemented' % self)

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

    def get_host_config(self, hostid):
        """Virtual method to get host config.

        :param hostid: id of the host to get configuration.
        :type hostid: int

        :returns: host configuration as dict.
        """
        return {}

    def get_host_configs(self, hostids):
        """Wrapper method to get hosts' configs.

        :param hostids: ids of the hosts to get configuration.
        :type hostids: list of int

        :returns: dict mapping each hostid to host configuration as dict.
        """
        configs = {}
        for hostid in hostids:
            configs[hostid] = self.get_host_config(hostid)
        return configs

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

    def update_host_configs(self, configs):
        """Wrapper method to update host configs.

        :param configs: dict mapping host id to host configuration as dict.
        :type configs: dict of (int, dict)
        """
        for hostname, config in configs.items():
            self.update_host_config(hostname, config)


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
