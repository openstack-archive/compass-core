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

"""Module to reinstall a given cluster

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import logging

from compass.actions import util
from compass.config_management.utils.config_manager import ConfigManager
from compass.db.api import database


def reinstall(cluster_hosts):
    """Reinstall clusters.

    :param cluster_hosts: clusters and hosts in each cluster to reinstall.
    :type cluster_hosts: dict of int or str to list of int or str

    .. note::
        The function should be called out of database session.
    """
    with util.lock('serialized_action') as lock:
        if not lock:
            raise Exception(
                'failed to acquire lock to reinstall')

        logging.debug('reinstall cluster_hosts: %s', cluster_hosts)
        with database.session():
            cluster_hosts, os_versions, target_systems = (
                util.update_cluster_hosts(cluster_hosts))
            manager = ConfigManager()
            manager.reinstall_cluster_and_hosts(
                cluster_hosts, os_versions, target_systems)
            manager.sync()
