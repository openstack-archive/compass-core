# Copyright 2014 Huawei Technologies Co. Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__author__ = "Grace Yu (grace.yu@huawei.com)"


"""All keywords variables in deployment are defined in this module."""


# General keywords
BASEINFO = 'baseinfo'
CLUSTER = 'cluster'
HOST = 'host'
HOSTS = 'hosts'
ID = 'id'
NAME = 'name'
PASSWORD = 'password'
USERNAME = 'username'


# Adapter info related keywords
FLAVOR = 'flavor'
FLAVORS = 'flavors'
PLAYBOOK = 'playbook'
FLAVOR_NAME = 'flavor_name'
HEALTH_CHECK_CMD = 'health_check_cmd'
TMPL = 'template'
INSTALLER_SETTINGS = 'settings'
METADATA = 'metadata'
OS_INSTALLER = 'os_installer'
PK_INSTALLER = 'package_installer'
SUPPORT_OSES = 'supported_oses'


# Cluster info related keywords
ADAPTER_ID = 'adapter_id'
OS_VERSION = 'os_name'


# Host info related keywords
DNS = 'dns'
DOMAIN = 'domain'
HOST_ID = 'host_id'
HOSTNAME = 'hostname'
IP_ADDR = 'ip'
IPMI = 'ipmi'
IPMI_CREDS = 'ipmi_credentials'
MAC_ADDR = 'mac'
MGMT_NIC_FLAG = 'is_mgmt'
NETMASK = 'netmask'
NETWORKS = 'networks'
NIC = 'interface'
CLUSTER_ID = 'cluster_id'
ORIGIN_CLUSTER_ID = 'origin_cluster_id'
PROMISCUOUS_FLAG = 'is_promiscuous'
REINSTALL_OS_FLAG = 'reinstall_os'
SUBNET = 'subnet'


# Cluster/host config related keywords
COMPLETED_PK_CONFIG = 'completed_package_config'
COMPLETED_OS_CONFIG = 'completed_os_config'
DEPLOYED_OS_CONFIG = 'deployed_os_config'
DEPLOYED_PK_CONFIG = 'deployed_package_config'
NETWORK_MAPPING = 'network_mapping'
OS_CONFIG = 'os_config'
OS_CONFIG_GENERAL = 'general'
PK_CONFIG = 'package_config'
ROLES = 'roles'
PATCHED_ROLES = 'patched_roles'
ROLES_MAPPING = 'roles_mapping'
SERVER_CREDS = 'server_credentials'
TMPL_VARS_DICT = 'vars_dict'
