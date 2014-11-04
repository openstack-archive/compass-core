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

"""Module to deploy a given cluster
"""
import logging

from compass.actions import util
from compass.db.api import user as user_db
from compass.deployment.deploy_manager import DeployManager
from compass.deployment.utils import constants as const


def deploy(cluster_id, hosts_id_list, username=None):
    """Deploy clusters.

    :param cluster_hosts: clusters and hosts in each cluster to deploy.
    :type cluster_hosts: dict of int or str to list of int or str

    .. note::
        The function should be called out of database session.
    """
    with util.lock('serialized_action', timeout=1000) as lock:
        if not lock:
            raise Exception('failed to acquire lock to deploy')

        user = user_db.get_user_object(username)

        cluster_info = util.ActionHelper.get_cluster_info(cluster_id, user)
        adapter_id = cluster_info[const.ADAPTER_ID]

        adapter_info = util.ActionHelper.get_adapter_info(
            adapter_id, cluster_id, user)
        hosts_info = util.ActionHelper.get_hosts_info(
            cluster_id, hosts_id_list, user)

        deploy_manager = DeployManager(adapter_info, cluster_info, hosts_info)
        #deploy_manager.prepare_for_deploy()
        logging.debug('Created deploy manager with %s %s %s'
                      % (adapter_info, cluster_info, hosts_info))

        deployed_config = deploy_manager.deploy()
        util.ActionHelper.save_deployed_config(deployed_config, user)
        util.ActionHelper.update_state(cluster_id, hosts_id_list, user)


def redeploy(cluster_id, hosts_id_list, username=None):
    """Deploy clusters.

    :param cluster_hosts: clusters and hosts in each cluster to deploy.
    :type cluster_hosts: dict of int or str to list of int or str
    """
    with util.lock('serialized_action') as lock:
        if not lock:
            raise Exception('failed to acquire lock to deploy')

        user = user_db.get_user_object(username)
        cluster_info = util.ActionHelper.get_cluster_info(cluster_id, user)
        adapter_id = cluster_info[const.ADAPTER_ID]

        adapter_info = util.ActionHelper.get_adapter_info(
            adapter_id, cluster_id, user)
        hosts_info = util.ActionHelper.get_hosts_info(
            cluster_id, hosts_id_list, user)

        deploy_manager = DeployManager(adapter_info, cluster_info, hosts_info)
        # deploy_manager.prepare_for_deploy()
        deploy_manager.redeploy()
        util.ActionHelper.update_state(cluster_id, hosts_id_list, user)


ActionHelper = util.ActionHelper


class ServerPowerMgmt(object):
    """Power management for bare-metal machines by IPMI command."""
    @staticmethod
    def poweron(machine_id, user):
        """Power on the specified machine."""
        pass

    @staticmethod
    def poweroff(machine_id, user):
        pass

    @staticmethod
    def reset(machine_id, user):
        pass


class HostPowerMgmt(object):
    """Power management for hosts installed OS by OS installer. OS installer
       will poweron/poweroff/reset host.
    """
    @staticmethod
    def poweron(host_id, user):
        """Power on the specified host."""
        pass

    @staticmethod
    def poweroff(host_id, user):
        pass

    @staticmethod
    def reset(host_id, user):
        pass
