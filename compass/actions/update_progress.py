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
from compass.db.api import database
from compass.db import models
from compass.log_analyzor import progress_calculator
from compass.utils import setting_wrapper as setting


def _cluster_filter(cluster):
    """filter cluster."""
    if not cluster.state:
        logging.error('there is no state for cluster %s',
                      cluster.id)
        return False

    if cluster.state.state != 'INSTALLING':
        logging.error('the cluster %s state %s is not installing',
                      cluster.id, cluster.state.state)
        return False

    return True


def _host_filter(host):
    """filter host."""
    if not host.state:
        logging.error('there is no state for host %s',
                      host.id)
        return False

    if host.state.state != 'INSTALLING':
        logging.error('the host %s state %s is not installing',
                      host.id, host.state.state)
        return False

    return True


def update_progress(cluster_hosts):
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
    with util.lock('log_progressing', blocking=False) as lock:
        if not lock:
            logging.error(
                'failed to acquire lock to calculate installation progress')
            return

        logging.info('update installing progress of cluster_hosts: %s',
                     cluster_hosts)
        os_names = {}
        distributed_systems = {}
        with database.session() as session:
            clusters = session.query(models.Cluster).all()
            for cluster in clusters:
                clusterid = cluster.id

                adapter = cluster.adapter
                os_installer = adapter.adapter_os_installer
                if os_installer:
                    os_installer_name = os_installer.name
                else:
                    os_installer_name = None
                package_installer = adapter.adapter_package_installer
                if package_installer:
                    package_installer_name = package_installer.name
                else:
                    package_installer_name = None

                distributed_system_name = cluster.distributed_system_name
                os_name = cluster.os_name
                os_names[clusterid] = os_name
                distributed_systems[clusterid] = distributed_system_name

                clusterhosts = cluster.clusterhosts
                hostids = [clusterhost.host.id for clusterhost in clusterhosts]
                cluster_hosts.update({clusterid: hostids})

        logging.info(
            'update progress for '
            'os_installer_name %s,'
            'os_names %s,'
            'package_installer_name %s,'
            'distributed_systems %s,'
            'cluster_hosts %s',
            os_installer_name,
            os_names,
            package_installer_name,
            distributed_systems,
            cluster_hosts
        )
        progress_calculator.update_progress(
            os_installer_name,
            os_names,
            package_installer_name,
            distributed_systems,
            cluster_hosts)
