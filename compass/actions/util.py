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

"""Module to provide util for actions

   .. moduleauthor:: Xiaodong Wang ,xiaodongwang@huawei.com>
"""
import logging
import redis

from contextlib import contextmanager

from compass.db import database
from compass.db.model import Cluster
from compass.db.model import Switch


@contextmanager
def lock(lock_name, blocking=True, timeout=10):
    redis_instance = redis.Redis()
    instance_lock = redis_instance.lock(lock_name, timeout=timeout)
    try:
        locked = instance_lock.acquire(blocking=blocking)
        if locked:
            logging.debug('acquired lock %s', lock_name)
            yield instance_lock
        else:
            logging.info('lock %s is already hold', lock_name)

    except Exception as error:
        logging.info(
            'redis fails to acquire the lock %s', lock_name)
        logging.exception(error)

    finally:
        instance_lock.acquired_until = 0
        instance_lock.release()
        logging.debug('released lock %s', lock_name)


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
        if cluster_hosts and (
            cluster.id not in cluster_hosts and
            str(cluster.id) not in cluster_hosts and
            cluster.name not in cluster_hosts
        ):
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

        if cluster.id in cluster_hosts:
            hosts = cluster_hosts[cluster.id]
        elif str(cluster.id) in cluster_hosts:
            hosts = cluster_hosts[str(cluster.id)]
        elif cluster.name in cluster_hosts:
            hosts = cluster_hosts[cluster.name]
        else:
            hosts = []

        if not hosts:
            hosts = [host.id for host in cluster.hosts]

        for host in cluster.hosts:
            if (
                host.id not in hosts and
                str(host.id) not in hosts and
                host.hostname not in hosts
            ):
                logging.debug('ignore host %s which is not in %s',
                              host.id, hosts)
                continue

            if host_filter and not host_filter(host):
                logging.debug('filter host %s', host.id)
                continue

            updated_cluster_hosts[cluster.id].append(host.id)

    return (updated_cluster_hosts, os_versions, target_systems)
