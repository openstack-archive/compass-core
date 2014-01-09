"""Module to provider installer interface.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""


class Installer(object):
    """Interface for installer."""
    NAME = 'installer'

    def __init__(self):
        raise NotImplementedError(
            '%s is not implemented' % self.__class__.__name__)

    def __repr__(self):
        return '%s[%s]' % (self.__class__.__name__, self.NAME)

    def sync(self, **kwargs):
        """virtual method to sync installer."""
        pass

    def reinstall_host(self, hostid, config, **kwargs):
        """virtual method to reinstall specific host."""
        pass

    def get_global_config(self, **kwargs):
        """virtual method to get global config."""
        return {}

    def clean_cluster_config(self, clusterid, config, **kwargs):
        """virtual method to clean cluster config.

        :param clusterid: the id of the cluster to cleanup.
        :type clusterid: int
        :param config: cluster configuration to cleanup.
        :type config: dict
        """
        pass

    def get_cluster_config(self, clusterid, **kwargs):
        """virtual method to get cluster config.

        :param clusterid: the id of the cluster to get configuration.
        :type clusterid: int

        :returns: cluster configuration as dict.
        """
        return {}

    def clean_host_config(self, hostid, config, **kwargs):
        """virtual method to clean host config.

        :param hostid: the id of the host to cleanup.
        :type hostid: int
        :param config: host configuration to cleanup.
        :type config: dict
        """
        pass

    def get_host_config(self, hostid, **kwargs):
        """virtual method to get host config.

        :param hostid: the id of host to get configuration.
        :type hostid: int

        :returns: host configuration as dict.
        """
        return {}

    def clean_host_configs(self, host_configs, **kwargs):
        """Wrapper method to clean hosts' configs.

        :param host_configs: dict of host id to host configuration as dict
        """
        for hostid, host_config in host_configs.items():
            self.clean_host_config(hostid, host_config, **kwargs)

    def get_host_configs(self, hostids, **kwargs):
        """Wrapper method get hosts' configs.

        :param hostids: ids of the hosts' configuration.
        :type hostids: list of int

        :returns: dict of host id to host configuration as dict.
        """
        host_configs = {}
        for hostid in hostids:
            host_configs[hostid] = self.get_host_config(hostid, **kwargs)
        return host_configs

    def update_global_config(self, config, **kwargs):
        """virtual method to update global config.

        :param config: global configuration.
        :type config: dict
        """
        pass

    def update_cluster_config(self, clusterid, config, **kwargs):
        """virtual method to update cluster config.

        :param clusterid: the id of the cluster to update the configuration.
        :type clusterid: int
        :param config: cluster configuration to update.
        :type config: dict
        """
        pass

    def update_host_config(self, hostid, config, **kwargs):
        """virtual method to update host config.

        :param hostid: the id of host to update host configuration.
        :type hostid: int
        :param config: host configuration to update.
        :type config: dict
        """
        pass

    def update_host_configs(self, host_configs, **kwargs):
        """Wrapper method to updaet hosts' configs.

        :param host_configs: dict of host id to host configuration as dict
        """
        for hostid, config in host_configs.items():
            self.update_host_config(hostid, config, **kwargs)
