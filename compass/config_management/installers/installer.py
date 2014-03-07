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

"""Module to provider installer interface.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""


class Installer(object):
    """Interface for installer."""
    NAME = 'installer'

    def __repr__(self):
        return '%s[%s]' % (self.__class__.__name__, self.NAME)

    def sync(self, **kwargs):
        """virtual method to sync installer."""
        pass

    def get_global_config(self, **kwargs):
        """virtual method to get global config."""
        return {}

    def get_cluster_config(self, clusterid, **kwargs):
        """virtual method to get cluster config.

        :param clusterid: the id of the cluster to get configuration.
        :type clusterid: int

        :returns: cluster configuration as dict.
        """
        return {}

    def get_host_config(self, hostid, **kwargs):
        """virtual method to get host config.

        :param hostid: the id of host to get configuration.
        :type hostid: int

        :returns: host configuration as dict.
        """
        return {}

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

    def clean_host_installing_progress(
        self, hostid, config, **kwargs
    ):
        """virtual method to clean host installing progress.

        :param hostid: the id of host to clean the log.
        :type hostid: int
        :param config: host configuration.
        :type config: dict
        """
        pass

    def clean_cluster_installing_progress(
        self, clusterid, config, **kwargs
    ):
        """virtual method to clean host installing progress.

        :param clusterid: the id of cluster to clean the log.
        :type clusterid: int
        :param config: cluster configuration.
        :type config: dict
        """
        pass

    def reinstall_host(self, hostid, config, **kwargs):
        """virtual method to reinstall specific host.

        :param hostid: the id of the host to reinstall.
        :type hostid: int
        :param config: host configuration to reinstall
        :type config: dict
        """
        pass

    def reinstall_cluster(self, clusterid, config, **kwargs):
        """virtual method to reinstall specific cluster.

        :param clusterid: the id of the cluster to reinstall.
        :type clusterid: int
        :param config: cluster configuration to reinstall
        :type config: dict
        """
        pass

    def clean_host_config(self, hostid, config, **kwargs):
        """virtual method to clean host config.

        :param hostid: the id of the host to cleanup.
        :type hostid: int
        :param config: host configuration to cleanup.
        :type config: dict
        """
        pass

    def clean_cluster_config(self, clusterid, config, **kwargs):
        """virtual method to clean cluster config.

        :param clusterid: the id of the cluster to cleanup.
        :type clusterid: int
        :param config: cluster configuration to cleanup.
        :type config: dict
        """
        pass
