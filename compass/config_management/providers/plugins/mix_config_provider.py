"""Mix provider which read config from different other providers.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
from compass.config_management.providers import config_provider
from compass.utils import setting_wrapper as setting


class MixProvider(config_provider.ConfigProvider):
    """mix provider which read config from different other providers."""
    NAME = 'mix'

    def __init__(self):
        self.global_provider_ = config_provider.get_provider_by_name(
            setting.GLOBAL_CONFIG_PROVIDER)
        self.cluster_provider_ = config_provider.get_provider_by_name(
            setting.CLUSTER_CONFIG_PROVIDER)
        self.host_provider_ = config_provider.get_provider_by_name(
            setting.HOST_CONFIG_PROVIDER)

    def get_global_config(self):
        """get global config."""
        return self.global_provider_.get_global_config()

    def get_cluster_config(self, clusterid):
        """get cluster config."""
        return self.cluster_provider_.get_cluster_config(clusterid)

    def get_host_config(self, hostid):
        """get host config."""
        return self.host_provider_.get_host_config(hostid)

    def update_global_config(self, config):
        """update global config."""
        self.global_provider_.update_global_config(config)

    def update_cluster_config(self, clusterid, config):
        """update cluster config."""
        self.cluster_provider_.update_cluster_config(
            clusterid, config)

    def update_host_config(self, hostid, config):
        """update host config."""
        self.host_provider_.update_host_config(hostid, config)


config_provider.register_provider(MixProvider)
