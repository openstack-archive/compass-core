"""Module to update status and installing progress of the given cluster.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import logging

from compass.db import database
from compass.db.model import Cluster
from compass.log_analyzor import progress_calculator
from compass.utils import setting_wrapper as setting


def update_progress(clusterid):
    """Update status and installing progress of the given cluster.

    :param clusterid: the id of the cluster to get the progress.
    :type clusterid: int

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
    os_version = ''
    target_system = ''
    hostids = []
    with database.session() as session:
        cluster = session.query(Cluster).filter_by(id=clusterid).first()
        if not cluster:
            logging.error('no cluster found for %s', clusterid)
            return

        if not cluster.adapter:
            logging.error('there is no adapter for cluster %s', clusterid)
            return

        os_version = cluster.adapter.os
        target_system = cluster.adapter.target_system
        if not cluster.state:
            logging.error('there is no state for cluster %s', clusterid)
            return

        if cluster.state.state != 'INSTALLING':
            logging.error('the state %s is not in installing for cluster %s',
                          cluster.state.state, clusterid)
            return

        hostids = [host.id for host in cluster.hosts]

    progress_calculator.update_progress(setting.OS_INSTALLER,
                                        os_version,
                                        setting.PACKAGE_INSTALLER,
                                        target_system,
                                        clusterid, hostids)
