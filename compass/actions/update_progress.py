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

"""Module to update status and installing progress of the given cluster.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import logging

from compass.actions import util
from compass.db.api import adapter_holder as adapter_api
from compass.db.api import cluster as cluster_api
from compass.db.api import host as host_api
from compass.db.api import user as user_api
from compass.log_analyzor import progress_calculator
from compass.utils import setting_wrapper as setting


def update_progress():
    """Update status and installing progress of the given cluster.

    :param cluster_hosts: clusters and hosts in each cluster to update.
    :type cluster_hosts: dict of int or str to list of int or str

    .. note::
       The function should be called out of the database session scope.
       In the function, it will update the database cluster_state and
       host_state table for the deploying cluster and hosts.

       The function will also query log_progressing_history table to get
       the lastest installing progress and the position of log it has
       processed in the last run. The function uses these information to
       avoid recalculate the progress from the beginning of the log file.
       After the progress got updated, these information will be stored back
       to the log_progressing_history for next time run.
    """
    with util.lock('log_progressing', timeout=60, blocking=False) as lock:
        if not lock:
            logging.error(
                'failed to acquire lock to calculate installation progress'
            )
            return

        logging.info('update installing progress')

        user = user_api.get_user_object(setting.COMPASS_ADMIN_EMAIL)
        hosts = host_api.list_hosts(user=user)
        host_mapping = {}
        for host in hosts:
            if 'id' not in host:
                logging.error('id is not in host %s', host)
                continue
            host_id = host['id']
            if 'os_name' not in host:
                logging.error('os_name is not in host %s', host)
                continue
            if 'os_installer' not in host:
                logging.error('os_installer is not in host %s', host)
                continue
            host_dirname = setting.HOST_INSTALLATION_LOGDIR_NAME
            if host_dirname not in host:
                logging.error(
                    '%s is not in host %s', host_dirname, host
                )
                continue
            host_state = host_api.get_host_state(host_id, user=user)
            if 'state' not in host_state:
                logging.error('state is not in host state %s', host_state)
                continue
            if host_state['state'] == 'INSTALLING':
                host_log_histories = host_api.get_host_log_histories(
                    host_id, user=user
                )
                host_log_history_mapping = {}
                for host_log_history in host_log_histories:
                    if 'filename' not in host_log_history:
                        logging.error(
                            'filename is not in host log history %s',
                            host_log_history
                        )
                        continue
                    host_log_history_mapping[
                        host_log_history['filename']
                    ] = host_log_history
                host_mapping[host_id] = (
                    host, host_state, host_log_history_mapping
                )
            else:
                logging.info(
                    'ignore host state %s since it is not in installing',
                    host_state
                )
        adapters = adapter_api.list_adapters(user=user)
        adapter_mapping = {}
        for adapter in adapters:
            if 'id' not in adapter:
                logging.error(
                    'id not in adapter %s', adapter
                )
                continue
            if 'package_installer' not in adapter:
                logging.info(
                    'package_installer not in adapter %s', adapter
                )
                continue
            adapter_id = adapter['id']
            adapter_mapping[adapter_id] = adapter
        clusters = cluster_api.list_clusters(user=user)
        cluster_mapping = {}
        for cluster in clusters:
            if 'id' not in cluster:
                logging.error('id not in cluster %s', cluster)
                continue
            cluster_id = cluster['id']
            if 'adapter_id' not in cluster:
                logging.error(
                    'adapter_id not in cluster %s',
                    cluster
                )
                continue
            cluster_state = cluster_api.get_cluster_state(
                cluster_id,
                user=user
            )
            if 'state' not in cluster_state:
                logging.error('state not in cluster state %s', cluster_state)
                continue
            cluster_mapping[cluster_id] = (cluster, cluster_state)
        clusterhosts = cluster_api.list_clusterhosts(user=user)
        clusterhost_mapping = {}
        for clusterhost in clusterhosts:
            if 'clusterhost_id' not in clusterhost:
                logging.error(
                    'clusterhost_id not in clusterhost %s',
                    clusterhost
                )
                continue
            clusterhost_id = clusterhost['clusterhost_id']
            if 'cluster_id' not in clusterhost:
                logging.error(
                    'cluster_id not in clusterhost %s',
                    clusterhost
                )
                continue
            cluster_id = clusterhost['cluster_id']
            if cluster_id not in cluster_mapping:
                logging.info(
                    'ignore clusterhost %s '
                    'since the cluster_id '
                    'is not in cluster_mapping %s',
                    clusterhost, cluster_mapping
                )
                continue
            cluster, _ = cluster_mapping[cluster_id]
            if 'flavor_name' not in cluster:
                logging.error(
                    'flavor_name is not in clusterhost %s related cluster',
                    clusterhost
                )
                continue
            clusterhost_dirname = setting.CLUSTERHOST_INATALLATION_LOGDIR_NAME
            if clusterhost_dirname not in clusterhost:
                logging.error(
                    '%s is not in clusterhost %s',
                    clusterhost_dirname, clusterhost
                )
                continue
            adapter_id = cluster['adapter_id']
            if adapter_id not in adapter_mapping:
                logging.info(
                    'ignore clusterhost %s '
                    'since the adapter_id %s '
                    'is not in adaper_mapping %s',
                    clusterhost, adapter_id, adapter_mapping
                )
                continue
            adapter = adapter_mapping[adapter_id]
            if 'package_installer' not in adapter:
                logging.info(
                    'ignore clusterhost %s '
                    'since the package_installer is not define '
                    'in adapter %s',
                    clusterhost, adapter
                )
                continue
            package_installer = adapter['package_installer']
            clusterhost['package_installer'] = package_installer
            clusterhost['adapter_name'] = adapter['name']
            clusterhost_state = cluster_api.get_clusterhost_self_state(
                clusterhost_id, user=user
            )
            if 'state' not in clusterhost_state:
                logging.error(
                    'state not in clusterhost_state %s',
                    clusterhost_state
                )
                continue
            if clusterhost_state['state'] == 'INSTALLING':
                clusterhost_log_histories = (
                    cluster_api.get_clusterhost_log_histories(
                        clusterhost_id, user=user
                    )
                )
                clusterhost_log_history_mapping = {}
                for clusterhost_log_history in clusterhost_log_histories:
                    if 'filename' not in clusterhost_log_history:
                        logging.error(
                            'filename not in clusterhost_log_history %s',
                            clusterhost_log_history
                        )
                        continue
                    clusterhost_log_history_mapping[
                        clusterhost_log_history['filename']
                    ] = clusterhost_log_history
                clusterhost_mapping[clusterhost_id] = (
                    clusterhost, clusterhost_state,
                    clusterhost_log_history_mapping
                )
            else:
                logging.info(
                    'ignore clusterhost state %s '
                    'since it is not in installing',
                    clusterhost_state
                )

        progress_calculator.update_host_progress(
            host_mapping)
        for host_id, (host, host_state, host_log_history_mapping) in (
            host_mapping.items()
        ):
            host_api.update_host_state(
                host_id, user=user,
                percentage=host_state.get('percentage', 0),
                message=host_state.get('message', ''),
                severity=host_state.get('severity', 'INFO')
            )
            for filename, host_log_history in (
                host_log_history_mapping.items()
            ):
                host_api.add_host_log_history(
                    host_id, filename=filename, user=user,
                    position=host_log_history.get('position', 0),
                    percentage=host_log_history.get('percentage', 0),
                    partial_line=host_log_history.get('partial_line', ''),
                    message=host_log_history.get('message', ''),
                    severity=host_log_history.get('severity', 'INFO'),
                    line_matcher_name=host_log_history.get(
                        'line_matcher_name', 'start'
                    )
                )
        progress_calculator.update_clusterhost_progress(
            clusterhost_mapping)
        for (
            clusterhost_id,
            (clusterhost, clusterhost_state, clusterhost_log_history_mapping)
        ) in (
            clusterhost_mapping.items()
        ):
            cluster_api.update_clusterhost_state(
                clusterhost_id, user=user,
                percentage=clusterhost_state.get('percentage', 0),
                message=clusterhost_state.get('message', ''),
                severity=clusterhost_state.get('severity', 'INFO')
            )
            for filename, clusterhost_log_history in (
                clusterhost_log_history_mapping.items()
            ):
                cluster_api.add_clusterhost_log_history(
                    clusterhost_id, user=user, filename=filename,
                    position=clusterhost_log_history.get('position', 0),
                    percentage=clusterhost_log_history.get('percentage', 0),
                    partial_line=clusterhost_log_history.get(
                        'partial_line', ''),
                    message=clusterhost_log_history.get('message', ''),
                    severity=clusterhost_log_history.get('severity', 'INFO'),
                    line_matcher_name=(
                        clusterhost_log_history.get(
                            'line_matcher_name', 'start'
                        )
                    )
                )
        progress_calculator.update_cluster_progress(
            cluster_mapping)
        for cluster_id, (cluster, cluster_state) in cluster_mapping.items():
            cluster_api.update_cluster_state(
                cluster_id, user=user
            )
