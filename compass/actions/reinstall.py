"""Module to reinstall a given cluster

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import logging

from compass.actions import util
from compass.config_management.utils.config_manager import ConfigManager
from compass.db import database


def reinstall(cluster_hosts):
    """Reinstall clusters.

    :param cluster_hosts: clusters and hosts in each cluster to reinstall.
    :type cluster_hosts: dict of int to list of int

    .. note::
        The function should be called out of database session.
    """
    logging.debug('reinstall cluster_hosts: %s', cluster_hosts)
    with database.session():
        cluster_hosts, os_versions, target_systems = (
            util.update_cluster_hosts(cluster_hosts))
        manager = ConfigManager()
        manager.reinstall_cluster_and_hosts(
            cluster_hosts, os_versions, target_systems)
        manager.sync()
