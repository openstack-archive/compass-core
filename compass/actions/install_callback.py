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

"""Module to receive installation callback.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import logging

from compass.actions import util
from compass.db.api import cluster as cluster_api
from compass.db.api import host as host_api
from compass.db.api import user as user_db
from compass.deployment.deploy_manager import DeployManager
from compass.deployment.utils import constants as const


def os_installed(
    host_id, clusterhosts_ready, clusters_os_ready,
    username=None
):
    """Callback when os is installed.

    :param host_id: host that os is installed.
    :type host_id: integer
    :param clusterhosts_ready: the clusterhosts that should trigger ready.
    :param clusters_os_ready: the cluster that should trigger os ready.

    .. note::
        The function should be called out of database session.
    """
    with util.lock('serialized_action') as lock:
        if not lock:
            raise Exception(
                'failed to acquire lock to '
                'do the post action after os installation'
            )
        logging.info(
            'os installed on host %s '
            'with cluster host ready %s cluster os ready %s',
            host_id, clusterhosts_ready, clusters_os_ready
        )
        if username:
            user = user_db.get_user_object(username)
        else:
            user = None
        os_installed_triggered = False
        for cluster_id, clusterhost_ready in clusterhosts_ready.items():
            if not clusterhost_ready and os_installed_triggered:
                continue

            cluster_info = util.ActionHelper.get_cluster_info(
                cluster_id, user)
            adapter_id = cluster_info[const.ADAPTER_ID]

            adapter_info = util.ActionHelper.get_adapter_info(
                adapter_id, cluster_id, user)
            hosts_info = util.ActionHelper.get_hosts_info(
                cluster_id, [host_id], user)

            deploy_manager = DeployManager(
                adapter_info, cluster_info, hosts_info)

            if not os_installed_triggered:
                deploy_manager.os_installed()
                util.ActionHelper.host_ready(host_id, True, user)
                os_installed_triggered = True

            if clusterhost_ready:
                # deploy_manager.cluster_os_installed()
                util.ActionHelper.cluster_host_ready(
                    cluster_id, host_id, False, user
                )

            if util.ActionHelper.is_cluster_os_ready(cluster_id, user):
                logging.info("deploy_manager begin cluster_os_installed")
                deploy_manager.cluster_os_installed()


def package_installed(
    cluster_id, host_id, cluster_ready,
    host_ready, username=None
):
    """Callback when package is installed.

    :param cluster_id: cluster id.
    :param host_id: host id.
    :param cluster_ready: if the cluster should trigger ready.
    :param host_ready: if the host should trigger ready.

    .. note::
        The function should be called out of database session.
    """
    with util.lock('serialized_action') as lock:
        if not lock:
            raise Exception(
                'failed to acquire lock to '
                'do the post action after package installation'
            )
        logging.info(
            'package installed on cluster %s host %s '
            'with cluster ready %s host ready %s',
            cluster_id, host_id, cluster_ready, host_ready
        )

        if username:
            user = user_db.get_user_object(username)
        else:
            user = None
        cluster_info = util.ActionHelper.get_cluster_info(cluster_id, user)
        adapter_id = cluster_info[const.ADAPTER_ID]

        adapter_info = util.ActionHelper.get_adapter_info(
            adapter_id, cluster_id, user)
        hosts_info = util.ActionHelper.get_hosts_info(
            cluster_id, [host_id], user)

        deploy_manager = DeployManager(adapter_info, cluster_info, hosts_info)

        deploy_manager.package_installed()
        util.ActionHelper.cluster_host_ready(cluster_id, host_id, True, user)
        if cluster_ready:
            util.ActionHelper.cluster_ready(cluster_id, False, user)
        if host_ready:
            util.ActionHelper.host_ready(host_id, False, user)


def cluster_installed(
    cluster_id, clusterhosts_ready,
    username=None
):
    """Callback when cluster is installed.

    :param cluster_id: cluster id
    :param clusterhosts_ready: clusterhosts that should trigger ready.

    .. note::
        The function should be called out of database session.
    """
    with util.lock('serialized_action') as lock:
        if not lock:
            raise Exception(
                'failed to acquire lock to '
                'do the post action after cluster installation'
            )
        logging.info(
            'package installed on cluster %s with clusterhosts ready %s',
            cluster_id, clusterhosts_ready
        )
        if username:
            user = user_db.get_user_object(username)
        else:
            user = None
        cluster_info = util.ActionHelper.get_cluster_info(cluster_id, user)
        adapter_id = cluster_info[const.ADAPTER_ID]

        adapter_info = util.ActionHelper.get_adapter_info(
            adapter_id, cluster_id, user)
        hosts_info = util.ActionHelper.get_hosts_info(
            cluster_id, clusterhosts_ready.keys(), user)

        deploy_manager = DeployManager(adapter_info, cluster_info, hosts_info)

        deploy_manager.cluster_installed()
        util.ActionHelper.cluster_ready(cluster_id, True, user)
        for host_id, clusterhost_ready in clusterhosts_ready.items():
            if clusterhost_ready:
                util.ActionHelper.cluster_host_ready(
                    cluster_id, host_id, False, user
                )
