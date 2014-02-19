"""Module to provide util for actions

   .. moduleauthor:: Xiaodong Wang ,xiaodongwang@huawei.com>
"""
import logging

from compass.db import database
from compass.db.model import Switch
from compass.db.model import Cluster


def update_switch_ips(switch_ips):
    """get updated switch ips."""
    session = database.current_session()
    switches = session.query(Switch).all()
    if switch_ips:
        return [
            switch.ip for switch in switches
            if switch.ip in switch_ips
        ]
    else:
        return [switch.ip for switch in switches]


def update_cluster_hosts(cluster_hosts,
                         cluster_filter=None, host_filter=None):
    """get updated clusters and hosts per cluster from cluster hosts."""
    session = database.current_session()
    os_versions = {}
    target_systems = {}
    updated_cluster_hosts = {}
    clusters = session.query(Cluster).all()
    for cluster in clusters:
        if cluster_hosts and cluster.id not in cluster_hosts:
            logging.debug('ignore cluster %s sinc it is not in %s',
                          cluster.id, cluster_hosts)
            continue

        adapter = cluster.adapter
        if not cluster.adapter:
            logging.error('there is no adapter for cluster %s',
                          cluster.id)
            continue

        if cluster_filter and not cluster_filter(cluster):
            logging.debug('filter cluster %s', cluster.id)
            continue

        updated_cluster_hosts[cluster.id] = []
        os_versions[cluster.id] = adapter.os
        target_systems[cluster.id] = adapter.target_system

        if (
            cluster.id not in cluster_hosts or
            not cluster_hosts[cluster.id]
        ):
            hostids = [host.id for host in cluster.hosts]
        else:
            hostids = cluster_hosts[cluster.id]

        for host in cluster.hosts:
            if host.id not in hostids:
                logging.debug('ignore host %s which is not in %s',
                              host.id, hostids)
                continue

            if host_filter and not host_filter(host):
                logging.debug('filter host %s', host.id)
                continue

            updated_cluster_hosts[cluster.id].append(host.id)

    return (updated_cluster_hosts, os_versions, target_systems)
