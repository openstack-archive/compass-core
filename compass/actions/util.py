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

from compass.db.api import adapter_holder as adapter_db
from compass.db.api import cluster as cluster_db
from compass.db.api import host as host_db
from compass.db.api import machine as machine_db
from compass.deployment.utils import constants as const


@contextmanager
def lock(lock_name, blocking=True, timeout=10):
    """acquire a lock to do some actions.

    The lock is acquired by lock_name among the whole distributed
    systems.
    """
    # TODO(xicheng): in future we should explicitly told which redis
    # server we want to talk to make the lock works on distributed
    # systems.
    redis_instance = redis.Redis()
    instance_lock = redis_instance.lock(lock_name, timeout=timeout)
    owned = False
    try:
        locked = instance_lock.acquire(blocking=blocking)
        if locked:
            owned = True
            logging.debug('acquired lock %s', lock_name)
            yield instance_lock
        else:
            logging.info('lock %s is already hold', lock_name)
            yield None

    except Exception as error:
        logging.info(
            'redis fails to acquire the lock %s', lock_name)
        logging.exception(error)
        yield None

    finally:
        if owned:
            instance_lock.acquired_until = 0
            instance_lock.release()
            logging.debug('released lock %s', lock_name)
        else:
            logging.debug('nothing to release %s', lock_name)


class ActionHelper(object):

    @staticmethod
    def get_adapter_info(adapter_id, cluster_id, user):
        """Get adapter information. Return a dictionary as below,

           {
              "id": 1,
              "name": "xxx",
              "flavors": [
                  {
                      "flavor_name": "xxx",
                      "roles": ['xxx', 'yyy', ...],
                      "template": "xxx.tmpl"
                  },
                  ...
              ],
              "metadata": {
                  "os_config": {
                      ...
                  },
                  "package_config": {
                      ...
                  }
              },
              "os_installer": {
                  "name": "cobbler",
                  "settings": {....}
              },
              "pk_installer": {
                  "name": "chef",
                  "settings": {....}
              },
              ...
           }
           To view a complete output, please refer to backend doc.
        """

        adapter_info = adapter_db.get_adapter(adapter_id, user=user)
        metadata = cluster_db.get_cluster_metadata(cluster_id, user=user)
        adapter_info.update({const.METADATA: metadata})

        for flavor_info in adapter_info[const.FLAVORS]:
            roles = flavor_info[const.ROLES]
            flavor_info[const.ROLES] = ActionHelper._get_role_names(roles)

        return adapter_info

    @staticmethod
    def _get_role_names(roles):
        return [role[const.NAME] for role in roles]

    @staticmethod
    def get_cluster_info(cluster_id, user):
        """Get cluster information.Return a dictionary as below,

           {
               "id": 1,
               "adapter_id": 1,
               "os_version": "CentOS-6.5-x86_64",
               "name": "cluster_01",
               "flavor": {
                   "flavor_name": "zzz",
                   "template": "xx.tmpl",
                   "roles": [...]
               }
               "os_config": {..},
               "package_config": {...},
               "deployed_os_config": {},
               "deployed_package_config": {},
               "owner": "xxx"
           }
        """

        cluster_info = cluster_db.get_cluster(cluster_id, user=user)

        # convert roles retrieved from db into a list of role names
        roles_info = cluster_info.setdefault(
            const.FLAVOR, {}).setdefault(const.ROLES, [])
        cluster_info[const.FLAVOR][const.ROLES] = \
            ActionHelper._get_role_names(roles_info)

        # get cluster config info
        cluster_config = cluster_db.get_cluster_config(cluster_id, user=user)
        cluster_info.update(cluster_config)

        deploy_config = cluster_db.get_cluster_deployed_config(cluster_id,
                                                               user=user)
        cluster_info.update(deploy_config)

        return cluster_info

    @staticmethod
    def get_hosts_info(cluster_id, hosts_id_list, user):
        """Get hosts information. Return a dictionary as below,

           {
               "hosts": {
                   1($host_id): {
                        "reinstall_os": True,
                        "mac": "xxx",
                        "name": "xxx",
                        "roles": [xxx, yyy]
                        },
                        "networks": {
                            "eth0": {
                                "ip": "192.168.1.1",
                                "netmask": "255.255.255.0",
                                "is_mgmt": True,
                                "is_promiscuous": False,
                                "subnet": "192.168.1.0/24"
                            },
                            "eth1": {...}
                        },
                        "os_config": {},
                        "package_config": {},
                        "deployed_os_config": {},
                        "deployed_package_config": {}
                   },
                   2: {...},
                   ....
               }
           }
        """

        hosts_info = {}
        for host_id in hosts_id_list:
            info = cluster_db.get_cluster_host(cluster_id, host_id, user=user)
            logging.debug("checking on info %r %r" % (host_id, info))

            info[const.ROLES] = ActionHelper._get_role_names(info[const.ROLES])

            # TODO(grace): Is following line necessary??
            info.setdefault(const.ROLES, [])

            config = cluster_db.get_cluster_host_config(cluster_id,
                                                        host_id,
                                                        user=user)
            info.update(config)

            networks = info[const.NETWORKS]
            networks_dict = {}
            # Convert networks from list to dictionary format
            for entry in networks:
                nic_info = {}
                nic_info = {
                    entry[const.NIC]: {
                        const.IP_ADDR: entry[const.IP_ADDR],
                        const.NETMASK: entry[const.NETMASK],
                        const.MGMT_NIC_FLAG: entry[const.MGMT_NIC_FLAG],
                        const.PROMISCUOUS_FLAG: entry[const.PROMISCUOUS_FLAG],
                        const.SUBNET: entry[const.SUBNET]
                    }
                }
                networks_dict.update(nic_info)

            info[const.NETWORKS] = networks_dict

            hosts_info[host_id] = info

        return hosts_info

    @staticmethod
    def save_deployed_config(deployed_config, user):
        """Save deployed config."""
        cluster_config = deployed_config[const.CLUSTER]
        cluster_id = cluster_config[const.ID]
        del cluster_config[const.ID]

        cluster_db.update_cluster_deployed_config(cluster_id, user=user,
                                                  **cluster_config)

        hosts_id_list = deployed_config[const.HOSTS].keys()
        for host_id in hosts_id_list:
            config = deployed_config[const.HOSTS][host_id]
            cluster_db.update_cluster_host_deployed_config(cluster_id,
                                                           host_id,
                                                           user=user,
                                                           **config)

    @staticmethod
    def update_state(
        cluster_id, host_id_list, user, **kwargs
    ):
        # update all clusterhosts state
        for host_id in host_id_list:
            cluster_db.update_cluster_host_state(
                cluster_id,
                host_id,
                user=user,
                **kwargs
            )

        # update cluster state
        cluster_db.update_cluster_state(
            cluster_id,
            user=user,
            **kwargs
        )

    @staticmethod
    def delete_cluster(
        cluster_id, host_id_list, user, delete_underlying_host=False
    ):
        """Delete cluster.

        If delete_underlying_host is set, underlying hosts will also
        be deleted.
        """
        if delete_underlying_host:
            for host_id in host_id_list:
                host_db.del_host(
                    host_id, True, True, user=user
                )
        cluster_db.del_cluster(
            cluster_id, True, True, user=user
        )

    @staticmethod
    def delete_cluster_host(
        cluster_id, host_id, user, delete_underlying_host=False
    ):
        """Delete clusterhost.

        If delete_underlying_host set, also delete underlying host.
        """
        if delete_underlying_host:
            host_db.del_host(
                host_id, True, True, user=user
            )
        cluster_db.del_cluster_host(
            cluster_id, host_id, True, True, user=user
        )

    @staticmethod
    def delete_host(host_id, user):
        host_db.del_host(
            host_id, True, True, user=user
        )

    @staticmethod
    def host_ready(host_id, from_database_only, user):
        """Trigger host ready."""
        host_db.update_host_state_internal(
            host_id, from_database_only=from_database_only,
            user=user, ready=True
        )

    @staticmethod
    def cluster_host_ready(
        cluster_id, host_id, from_database_only, user
    ):
        """Trigger clusterhost ready."""
        cluster_db.update_cluster_host_state_internal(
            cluster_id, host_id, from_database_only=from_database_only,
            user=user, ready=True
        )

    @staticmethod
    def is_cluster_os_ready(cluster_id, user=None):
        return cluster_db.is_cluster_os_ready(cluster_id, user=user)

    @staticmethod
    def cluster_ready(cluster_id, from_database_only, user):
        """Trigger cluster ready."""
        cluster_db.update_cluster_state_internal(
            cluster_id, from_database_only=from_database_only,
            user=user, ready=True
        )

    @staticmethod
    def get_machine_IPMI(machine_id, user):
        machine_info = machine_db.get_machine(machine_id, user=user)
        return machine_info[const.IPMI_CREDS]
