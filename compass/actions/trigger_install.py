"""Module to deploy a given cluster

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import logging

from compass.db import database
from compass.db.model import Cluster, ClusterState, HostState
from compass.config_management.utils.config_manager import ConfigManager


def trigger_install(clusterid):
    """Deploy a given cluster.

    :param clusterid: the id of the cluster to deploy.
    :type clusterid: int

    .. note::
        The function should be called in database session.
    """
    session = database.current_session()
    cluster = session.query(Cluster).filter_by(id=clusterid).first()
    if not cluster:
        logging.error('no cluster found for %s', clusterid)
        return

    adapter = cluster.adapter
    if not adapter:
        logging.error('no proper adapter found for cluster %s', cluster.id)
        return

    if not cluster.state:
        cluster.state = ClusterState()

    if cluster.state.state and cluster.state.state != 'UNINITIALIZED':
        logging.error('ignore installing cluster %s since the state is %s',
                      cluster.id, cluster.state)
        return

    cluster.state.state = 'INSTALLING'
    hostids = [host.id for host in cluster.hosts]
    update_hostids = []
    for host in cluster.hosts:
        if not host.state:
            host.state = HostState()
        elif host.state.state and host.state.state != 'UNINITIALIZED':
            logging.info('ignore installing host %s sinc the state is %s',
                         host.id, host.state)
            continue

        host.state.state = 'INSTALLING'
        update_hostids.append(host.id)

    manager = ConfigManager()
    manager.update_cluster_and_host_configs(
        clusterid, hostids, update_hostids,
        adapter.os, adapter.target_system)
    manager.sync()
