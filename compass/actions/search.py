"""Module to search configs of given clusters

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import logging

from compass.actions import util
from compass.config_management.utils.config_manager import ConfigManager
from compass.db import database


def search(cluster_hosts, cluster_propreties_match,
           cluster_properties_name, host_properties_match,
           host_properties_name):
    """search clusters.

    :param cluster_hosts: clusters and hosts in each cluster to search.
    :type cluster_hosts: dict of int to list of int

    .. note::
        The function should be called out of database session.
    """
    logging.debug('search cluster_hosts: %s', cluster_hosts)
    with database.session():
        cluster_hosts, os_versions, target_systems = (
            util.update_cluster_hosts(cluster_hosts))
        manager = ConfigManager()
        return manager.filter_cluster_and_hosts(
            cluster_hosts, cluster_propreties_match,
            cluster_properties_name, host_properties_match,
            host_properties_name, os_versions,
            target_systems)
