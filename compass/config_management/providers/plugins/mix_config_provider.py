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

    def update_adapters(self, adapters, roles_per_target_system):
        """update adapters."""
        self.host_provider_.update_adapters(
            adapters, roles_per_target_system)

    def update_switch_filters(self, switch_filters):
        """update switch filters."""
        self.host_provider_.update_switch_filters(switch_filters)

    def clean_host_config(self, hostid):
        """clean host config."""
        self.host_provider_.clean_host_config(hostid)

    def reinstall_host(self, hostid):
        """reinstall host config."""
        self.host_provider_.reinstall_host(hostid)

    def reinstall_cluster(self, clusterid):
        """reinstall cluster."""
        self.host_provider_.reinstall_cluster(clusterid)

    def clean_host_installing_progress(self, hostid):
        """clean host installing progress."""
        self.host_provider_.clean_host_installing_progress(hostid)

    def clean_cluster_installing_progress(self, clusterid):
        """clean cluster installing progress."""
        self.host_provider_.clean_cluster_installing_progress(clusterid)

    def clean_cluster_config(self, clusterid):
        """clean cluster config."""
        self.host_provider_.clean_cluster_config(clusterid)

    def get_cluster_hosts(self, clusterid):
        """get cluster hosts."""
        return self.host_provider_.get_cluster_hosts(clusterid)

    def get_clusters(self):
        """get clusters."""
        return self.host_provider_.get_clusters()

    def get_switch_and_machines(self):
        """get switch and machines."""
        return self.host_provider_.get_switch_and_machines()

    def update_switch_and_machines(self, switches, switch_machines):
        """update siwtch and machines."""
        self.host_provider_.update_switch_and_machines(
            switches, switch_machines)


config_provider.register_provider(MixProvider)
