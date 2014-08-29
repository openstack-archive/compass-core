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

"""Module to deploy a given cluster
"""
import logging

from compass.actions import util
from compass.db.api import adapter_holder as adapter_db
from compass.db.api import cluster as cluster_db
from compass.db.api import machine as machine_db
from compass.db.api import user as user_db
from compass.deployment.deploy_manager import DeployManager
from compass.deployment.utils import constants as const


def deploy(cluster_id, hosts_id_list, username=None):
    """Deploy clusters.

    :param cluster_hosts: clusters and hosts in each cluster to deploy.
    :type cluster_hosts: dict of int or str to list of int or str

    .. note::
        The function should be called out of database session.
    """
    with util.lock('serialized_action', timeout=1000) as lock:
        if not lock:
            raise Exception('failed to acquire lock to deploy')

        user = user_db.get_user_object(username)

        cluster_info = ActionHelper.get_cluster_info(cluster_id, user)
        adapter_id = cluster_info[const.ADAPTER_ID]

        adapter_info = ActionHelper.get_adapter_info(adapter_id, cluster_id,
                                                     user)
        hosts_info = ActionHelper.get_hosts_info(cluster_id, hosts_id_list,
                                                 user)

        deploy_manager = DeployManager(adapter_info, cluster_info, hosts_info)
        #deploy_manager.prepare_for_deploy()
        deployed_config = deploy_manager.deploy()

        ActionHelper.save_deployed_config(deployed_config, user)
        ActionHelper.update_state(cluster_id, hosts_id_list, user)


def redeploy(cluster_id, hosts_id_list, username=None):
    """Deploy clusters.

    :param cluster_hosts: clusters and hosts in each cluster to deploy.
    :type cluster_hosts: dict of int or str to list of int or str
    """
    with util.lock('serialized_action') as lock:
        if not lock:
            raise Exception('failed to acquire lock to deploy')

        user = user_db.get_user_object(username)
        cluster_info = ActionHelper.get_cluster_info(cluster_id, user)
        adapter_id = cluster_info[const.ADAPTER_ID]

        adapter_info = ActionHelper.get_adapter_info(adapter_id,
                                                     cluster_id,
                                                     user)
        hosts_info = ActionHelper.get_hosts_info(cluster_id,
                                                 hosts_id_list,
                                                 user)

        deploy_manager = DeployManager(adapter_info, cluster_info, hosts_info)
        # deploy_manager.prepare_for_deploy()
        deploy_manager.redeploy()
        ActionHelper.update_state(cluster_id, hosts_id_list, user)


class ServerPowerMgmt(object):
    """Power management for bare-metal machines by IPMI command."""
    @staticmethod
    def poweron(machine_id, user):
        """Power on the specified machine."""
        pass

    @staticmethod
    def poweroff(machine_id, user):
        pass

    @staticmethod
    def reset(machine_id, user):
        pass


class HostPowerMgmt(object):
    """Power management for hosts installed OS by OS installer. OS installer
       will poweron/poweroff/reset host.
    """
    @staticmethod
    def poweron(host_id, user):
        """Power on the specified host."""
        pass

    @staticmethod
    def poweroff(host_id, user):
        pass

    @staticmethod
    def reset(host_id, user):
        pass


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
        adapter_info = adapter_db.get_adapter(user, adapter_id)
        metadata = cluster_db.get_cluster_metadata(user, cluster_id)
        logging.debug('got metadata from cluster %s: %s',
                      cluster_id, metadata)
        adapter_info.update({'metadata': metadata})
        logging.debug('got updated adapter info: %s', adapter_info)

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
        cluster_info = cluster_db.get_cluster(user, cluster_id)

        # convert roles retrieved from db into a list of role names
        roles_info = cluster_info[const.FLAVOR][const.ROLES]
        cluster_info[const.FLAVOR][const.ROLES] = \
            ActionHelper._get_role_names(roles_info)

        # get cluster config info
        cluster_config = cluster_db.get_cluster_config(user, cluster_id)
        cluster_info.update(cluster_config)

        deploy_config = cluster_db.get_cluster_deployed_config(user,
                                                               cluster_id)
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
            info = cluster_db.get_cluster_host(user, cluster_id, host_id)
            info[const.ROLES] = ActionHelper._get_role_names(info[const.ROLES])

            config = cluster_db.get_cluster_host_config(user,
                                                        cluster_id,
                                                        host_id)
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
        cluster_config = deployed_config[const.CLUSTER]
        cluster_id = cluster_config[const.ID]
        del cluster_config[const.ID]
        if 'os_name' in cluster_config:
            del cluster_config['os_name']
        if 'name' in cluster_config:
            del cluster_config['name']
        logging.debug('cluster config: %s', cluster_config)
        cluster_db.update_cluster_deployed_config(user, cluster_id,
                                                  **cluster_config)

        hosts_id_list = deployed_config[const.HOSTS].keys()
        for host_id in hosts_id_list:
            config = deployed_config[const.HOSTS][host_id]
            cluster_db.update_cluster_host_deployed_config(user,
                                                           cluster_id,
                                                           host_id,
                                                           **config)

    @staticmethod
    def update_state(cluster_id, host_id_list, user):
        # update cluster state
        cluster_db.update_cluster_state(user, cluster_id, state='INSTALLING')

        # update all clusterhosts state
        for host_id in host_id_list:
            cluster_db.update_cluster_host_state(user, cluster_id, host_id,
                                                 state='INSTALLING')

    @staticmethod
    def get_machine_IPMI(machine_id, user):
        machine_info = machine_db.get_machine(user, machine_id)
        return machine_info[const.IPMI_CREDS]
