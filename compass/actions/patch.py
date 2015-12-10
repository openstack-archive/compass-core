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

"""Module to patch an existing cluster
"""
import logging
import simplejson as json

from compass.actions import util
from compass.db.api import cluster as cluster_db
from compass.db.api import user as user_db
from compass.deployment.deploy_manager import Patcher
from compass.deployment.utils import constants as const


def patch(cluster_id, username=None):
    """Patch cluster.

    :param cluster_id: id of the cluster
    :type cluster_id: int

    .. note::
        The function should be called out of database session.
    """
    with util.lock('serialized_action', timeout=1000) as lock:
        if not lock:
            raise Exception('failed to acquire lock to deploy')

        user = user_db.get_user_object(username)
        cluster_hosts = cluster_db.list_cluster_hosts(cluster_id, user)
        hosts_id_list = [host['id'] for host in cluster_hosts]
        cluster_info = util.ActionHelper.get_cluster_info(cluster_id, user)
        adapter_id = cluster_info[const.ADAPTER_ID]

        adapter_info = util.ActionHelper.get_adapter_info(
            adapter_id, cluster_id, user)
        hosts_info = util.ActionHelper.get_hosts_info(
            cluster_id, hosts_id_list, user)
        patch_successful = True
        try:
            patcher = Patcher(
                adapter_info, cluster_info, hosts_info, cluster_hosts)
            patched_config = patcher.patch()
        except Exception as error:
            logging.exception(error)
            patch_successful = False

        if patch_successful:
            clean_payload = '{"patched_roles": []}'
            clean_payload = json.loads(clean_payload)
            for cluster_host in cluster_hosts:
                cluster_db.update_cluster_host(
                    cluster_id, cluster_host['id'], user, **clean_payload)
                logging.info(
                    "cleaning up patched roles for host id: %s",
                    cluster_host['id']
                )
            logging.info("Patch successful: %s", patched_config)
