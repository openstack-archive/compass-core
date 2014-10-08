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

__author__ = "Grace Yu (grace.yu@huawei.com)"


"""Module to manage and access cluster, hosts and adapter config.
"""
from copy import deepcopy
import logging


from compass.deployment.utils import constants as const


class BaseConfigManager(object):

    def __init__(self, adapter_info, cluster_info, hosts_info):
        self.adapter_info = adapter_info
        self.cluster_info = cluster_info
        self.hosts_info = hosts_info

    def get_cluster_id(self):
        return self.__get_cluster_item(const.ID)

    def get_clustername(self):
        return self.__get_cluster_item(const.NAME)

    def get_os_version(self):
        return self.__get_cluster_item(const.OS_VERSION)

    def get_cluster_baseinfo(self):
        """Get cluster base information, including cluster_id, os_version,
           and cluster_name.
        """
        attr_names = [const.ID, const.NAME, const.OS_VERSION]

        base_info = {}
        for name in attr_names:
            base_info[name] = self.__get_cluster_item(name)

        return base_info

    def get_host_id_list(self):
        if not self.hosts_info:
            logging.info("hosts config is None or {}")
            return []

        return self.hosts_info.keys()

    def get_cluster_flavor_info(self):
        return self.__get_cluster_item(const.FLAVOR, {})

    def get_cluster_flavor_name(self):
        flavor_info = self.get_cluster_flavor_info()
        return flavor_info.setdefault(const.FLAVOR_NAME, None)

    def get_cluster_flavor_roles(self):
        flavor_info = self.get_cluster_flavor_info()
        return flavor_info.setdefault(const.ROLES, [])

    def get_cluster_flavor_template(self):
        flavor_info = self.get_cluster_flavor_info()
        return flavor_info.setdefault(const.TMPL, None)

    def get_cluster_os_config(self):
        return deepcopy(self.__get_cluster_item(const.OS_CONFIG, {}))

    def get_cluster_package_config(self):
        return deepcopy(self.__get_cluster_item(const.PK_CONFIG, {}))

    def get_cluster_network_mapping(self):
        package_config = self.get_cluster_package_config()
        if not package_config:
            logging.info("cluster package_config is None or {}.")
            return {}

        mapping = package_config.setdefault(const.NETWORK_MAPPING, {})
        logging.info("Network mapping in the config is '%s'!", mapping)

        return mapping

    def get_cluster_deployed_os_config(self):
        return deepcopy(self.__get_cluster_item(const.DEPLOYED_OS_CONFIG, {}))

    def get_cluster_deployed_package_config(self):
        return deepcopy(self.__get_cluster_item(const.DEPLOYED_PK_CONFIG, {}))

    def __get_cluster_item(self, item, default_value=None):
        if not self.cluster_info:
            logging.info("cluster config is None or {}")
            return None

        return self.cluster_info.setdefault(item, default_value)

    def get_cluster_roles_mapping(self):
        if not self.cluster_info:
            logging.info("cluster config is None or {}")
            return {}

        deploy_config = self.get_cluster_deployed_package_config()
        mapping = deploy_config.setdefault(const.ROLES_MAPPING, {})

        if not mapping:
            mapping = self._get_cluster_roles_mapping_helper()
            deploy_config[const.ROLES_MAPPING] = mapping

        return mapping

    def _get_host_info(self, host_id):
        if not self.hosts_info:
            logging.info("hosts config is None or {}")
            return {}

        if host_id not in self.hosts_info:
            logging.info("Cannot find host, ID is '%s'", host_id)
            return {}

        return self.hosts_info[host_id]

    def __get_host_item(self, host_id, item, default_value=None):
        host_info = self._get_host_info(host_id)
        if not host_info:
            return {}

        return deepcopy(host_info.setdefault(item, default_value))

    def get_host_baseinfo(self, host_id):
        """Get host base information."""
        host_info = self._get_host_info(host_id)
        if not host_info:
            return {}

        attr_names = [const.REINSTALL_OS_FLAG, const.MAC_ADDR, const.NAME,
                      const.HOSTNAME, const.NETWORKS]
        base_info = {}
        for attr in attr_names:
            temp = host_info[attr]
            if isinstance(temp, dict) or isinstance(temp, list):
                base_info[attr] = deepcopy(temp)
            else:
                base_info[attr] = temp

        base_info[const.DNS] = self.get_host_dns(host_id)

        return base_info

    def get_host_fullname(self, host_id):
        return self.__get_host_item(host_id, const.NAME, None)

    def get_host_dns(self, host_id):
        host_info = self._get_host_info(host_id)
        if not host_info:
            return None

        if const.DNS not in host_info:
            hostname = host_info[const.HOSTNAME]
            domain = self.get_host_domain(host_id)
            host_info[const.DNS] = '.'.join((hostname, domain))

        return host_info[const.DNS]

    def get_host_mac_address(self, host_id):
        return self.__get_host_item(host_id, const.MAC_ADDR, None)

    def get_hostname(self, host_id):
        return self.__get_host_item(host_id, const.HOSTNAME, None)

    def get_host_networks(self, host_id):
        return self.__get_host_item(host_id, const.NETWORKS, {})

    def get_host_interfaces(self, host_id):
        networks = self.get_host_networks(host_id)
        return networks.keys()

    def get_host_interface_config(self, host_id, interface):
        networks = self.get_host_networks(host_id)
        return networks.setdefault(interface, {})

    def get_host_interface_ip(self, host_id, interface):
        interface_config = self._get_host_interface_config(host_id, interface)
        return interface_config.setdefault(const.IP_ADDR, None)

    def get_host_interface_netmask(self, host_id, interface):
        interface_config = self.get_host_interface_config(host_id, interface)
        return interface_config.setdefault(const.NETMASK, None)

    def get_host_interface_subnet(self, host_id, interface):
        nic_config = self.get_host_interface_config(host_id, interface)
        return nic_config.setdefault(const.SUBNET, None)

    def is_interface_promiscuous(self, host_id, interface):
        nic_config = self.get_host_interface_config(host_id, interface)
        if not nic_config:
            raise Exception("Cannot find interface '%s'", interface)

        return nic_config[const.PROMISCUOUS_FLAG]

    def is_interface_mgmt(self, host_id, interface):
        nic_config = self.get_host_interface_config(host_id, interface)
        if not nic_config:
            raise Exception("Cannot find interface '%s'", interface)

        return nic_config[const.MGMT_NIC_FLAG]

    def get_host_os_config(self, host_id):
        return self.__get_host_item(host_id, const.OS_CONFIG, {})

    def get_host_domain(self, host_id):
        os_config = self.get_host_os_config(host_id)
        os_general_config = os_config.setdefault(const.OS_CONFIG_GENERAL, {})
        domain = os_general_config.setdefault(const.DOMAIN, None)
        if domain is None:
            global_config = self.get_cluster_os_config()
            global_general = global_config.setdefault(const.OS_CONFIG_GENERAL,
                                                      {})
            domain = global_general.setdefault(const.DOMAIN, None)

        return domain

    def get_host_network_mapping(self, host_id):
        package_config = self.get_host_package_config(host_id)
        if const.NETWORK_MAPPING not in package_config:
            network_mapping = self.get_cluster_network_mapping()
        else:
            network_mapping = package_config[const.NETWORK_MAPPING]

        return network_mapping

    def get_host_package_config(self, host_id):
        return self.__get_host_item(host_id, const.PK_CONFIG, {})

    def get_host_deployed_os_config(self, host_id):
        host_info = self._get_host_info(host_id)
        return host_info.setdefault(const.DEPLOYED_OS_CONFIG, {})

    def get_host_deployed_package_config(self, host_id):
        host_info = self._get_host_info(host_id)
        return host_info.setdefault(const.DEPLOYED_PK_CONFIG, {})

    def get_host_roles(self, host_id):
        return self.__get_host_item(host_id, const.ROLES, [])

    def get_all_hosts_roles(self, hosts_id_list=None):
        roles = []
        if hosts_id_list is None:
            hosts_id_list = self.get_host_id_list()

        for host_id in hosts_id_list:
            host_roles = self.get_host_roles(host_id)
            roles.extend([role for role in host_roles if role not in roles])

        return roles

    def get_host_roles_mapping(self, host_id):
        roles_mapping = {}
        deployed_pk_config = self.get_host_package_config(host_id)

        if const.ROLES_MAPPING not in deployed_pk_config:
            roles_mapping = self._get_host_roles_mapping_helper(host_id)
            deployed_pk_config[const.ROLES_MAPPING] = roles_mapping
        else:
            roles_mapping = deployed_pk_config[const.ROLES_MAPPING]

        return deepcopy(roles_mapping)

    def get_host_ipmi_info(self, host_id):
        ipmi_info = self.__get_host_item(host_id, const.IPMI, {})

        if not ipmi_info:
            return (None, None, None)

        ipmi_ip = ipmi_info[const.IP_ADDR]
        ipmi_user = ipmi_info[const.IPMI_CREDS][const.USERNAME]
        ipmi_pass = ipmi_info[const.IPMI_CREDS][const.PASSWORD]

        return (ipmi_ip, ipmi_user, ipmi_pass)

    def __get_adapter_item(self, item, default_value=None):
        if not self.adapter_info:
            logging.info("Adapter Info is None!")
            return None

        return deepcopy(self.adapter_info.setdefault(item, default_value))

    def get_adapter_name(self):
        return self.__get_adapter_item(const.NAME, None)

    def get_dist_system_name(self):
        return self.__get_adapter_item(const.NAME, None)

    def get_os_installer_settings(self):
        installer_info = self.__get_adapter_item(const.OS_INSTALLER, {})
        return installer_info.setdefault(const.INSTALLER_SETTINGS, {})

    def get_pk_installer_settings(self):
        installer_info = self.__get_adapter_item(const.PK_INSTALLER, {})
        return installer_info.setdefault(const.INSTALLER_SETTINGS, {})

    def get_os_config_metadata(self):
        metadata = self.__get_adapter_item(const.METADATA, {})
        return metadata.setdefault(const.OS_CONFIG, {})

    def get_pk_config_meatadata(self):
        metadata = self.__get_adapter_item(const.METADATA, {})
        return metadata.setdefault(const.PK_CONFIG, {})

    def get_adapter_all_flavors(self):
        return self.__get_adapter_item(const.FLAVORS, [])

    def get_adapter_flavor(self, flavor_name):
        flavors = self.__get_adapter_item(const.FLAVORS, [])
        for flavor in flavors:
            if flavor[const.FLAVOR_NAME] == flavor_name:
                return flavor

        return None

    def _get_cluster_roles_mapping_helper(self):
        """The ouput format will be as below, for example:
           {
               "controller": {
                   "hostname": "xxx",
                   "management": {
                       "interface": "eth0",
                       "ip": "192.168.1.10",
                       "netmask": "255.255.255.0",
                       "subnet": "192.168.1.0/24",
                       "is_mgmt": True,
                       "is_promiscuous": False
                   },
                   ...
               },
                   ...
           }
        """
        mapping = {}
        hosts_id_list = self.get_host_id_list()
        network_mapping = self.get_cluster_network_mapping()
        if not network_mapping:
            return {}

        for host_id in hosts_id_list:
            roles_mapping = self.get_host_roles_mapping(host_id)
            for role in roles_mapping:
                if role not in mapping:
                    mapping[role] = roles_mapping[role]

        return mapping

    def _get_host_roles_mapping_helper(self, host_id):
        """The format will be the same as cluster roles mapping."""
        network_mapping = self.get_host_network_mapping(host_id)
        if not network_mapping:
            return {}

        hostname = self.get_hostname(host_id)
        roles = self.get_host_roles(host_id)
        interfaces = self.get_host_interfaces(host_id)

        mapping = {}
        temp = {const.HOSTNAME: hostname}
        for key in network_mapping:
            nic = network_mapping[key][const.NIC]
            if nic in interfaces:
                temp[key] = self.get_host_interface_config(host_id, nic)
                temp[key][const.NIC] = nic

        for role in roles:
            role = role.replace("-", "_")
            mapping[role] = temp
        return mapping
