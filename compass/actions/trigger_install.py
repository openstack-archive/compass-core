"""Module to deploy a given cluster

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import logging
import os
import os.path
import shutil

from compass.db import database
from compass.db.model import Cluster, ClusterState, HostState
from compass.db.model import LogProgressingHistory
from compass.config_management.utils.config_manager import ConfigManager
from compass.utils import setting_wrapper as setting


def trigger_install(clusterid, hostids=[]):
    """Deploy a given cluster.

    :param clusterid: the id of the cluster to deploy.
    :type clusterid: int
    :param hostids: the ids of the hosts to deploy.
    :type hostids: list of int

    .. note::
        The function should be called in database session.
    """
    logging.debug('trigger install cluster %s hosts %s',
                  clusterid, hostids)
    session = database.current_session()
    cluster = session.query(Cluster).filter_by(id=clusterid).first()
    if not cluster:
        logging.error('no cluster found for %s', clusterid)
        return

    adapter = cluster.adapter
    if not adapter:
        logging.error('no proper adapter found for cluster %s', cluster.id)
        return

    if cluster.mutable:
        logging.error('ignore installing cluster %s since it is mutable',
                      cluster)
        return

    if not cluster.state:
        cluster.state = ClusterState()

    cluster.state.state = 'INSTALLING'
    cluster.state.progress = 0.0
    cluster.state.message = ''
    cluster.state.severity = 'INFO'

    all_hostids = [host.id for host in cluster.hosts]
    update_hostids = []
    for host in cluster.hosts:
        if host.id not in hostids:
            logging.info('ignore installing %s since it is not in %s',
                         host, hostids)
            continue

        if host.mutable:
            logging.error('ignore installing %s since it is mutable',
                          host)
            continue

        log_dir = os.path.join(
            setting.INSTALLATION_LOGDIR,
            '%s.%s' % (host.hostname, clusterid))
        logging.info('clean log dir %s', log_dir)
        shutil.rmtree(log_dir, True)
        session.query(LogProgressingHistory).filter(
            LogProgressingHistory.pathname.startswith(
                '%s/' % log_dir)).delete(
            synchronize_session='fetch')

        if not host.state:
            host.state = HostState()

        host.state.state = 'INSTALLING'
        host.state.progress = 0.0
        host.state.message = ''
        host.state.severity = 'INFO'
        update_hostids.append(host.id)

    os.system('service rsyslog restart')

    manager = ConfigManager()
    manager.update_cluster_and_host_configs(
        clusterid, all_hostids, update_hostids,
        adapter.os, adapter.target_system)
    manager.sync()
