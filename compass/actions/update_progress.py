# Copyright 2014 Openstack Foundation
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
from compass.db import database
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
    with util.lock('log_progressing', blocking=False):
        logging.debug('update installing progress of cluster_hosts: %s',
                      cluster_hosts)
        os_versions = {}
        target_systems = {}
        with database.session():
            cluster_hosts, os_versions, target_systems = (
                util.update_cluster_hosts(
                    cluster_hosts, _cluster_filter, _host_filter))

        progress_calculator.update_progress(
            setting.OS_INSTALLER,
            os_versions,
            setting.PACKAGE_INSTALLER,
            target_systems,
            cluster_hosts)
