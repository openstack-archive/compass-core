#!/usr/bin/python
# copyright 2014 Huawei Technologies Co. Ltd
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

"""Example code to deploy a cluster by compass client api."""
import os
import re
import sys
import time

# from compass.apiclient.restful import Client
from restful import Client

COMPASS_SERVER_URL = 'http://localhost/api'
COMPASS_LOGIN_EMAIL = 'admin@huawei.com'
COMPASS_LOGIN_PASSWORD = 'admin'
SWITCH_IP = '172.29.8.40'
SWITCH_SNMP_VERSION = '2c'
SWITCH_SNMP_COMMUNITY = 'public'
CLUSTER_NAME = 'test_cluster'
HOST_NAME_PREFIX = 'host'
SERVICE_USERNAME = 'service'
SERVICE_PASSWORD = 'service'
CONSOLE_USERNAME = 'console'
CONSOLE_PASSWORD = 'console'
HA_VIP = ''

MANAGEMENT_IP_START = '10.145.88.130'
MANAGEMENT_IP_END = '10.145.88.254'
MANAGEMENT_IP_GATEWAY = '10.145.88.1'
MANAGEMENT_NETMASK = '255.255.255.0'
MANAGEMENT_NIC = 'eth0'
MANAGEMENT_PROMISC = 0
TENANT_IP_START = '192.168.10.130'
TENANT_IP_END = '192.168.10.255'
TENANT_IP_GATEWAY = '192.168.10.1'
TENANT_NETMASK = '255.255.255.0'
TENANT_NIC = 'eth0'
TENANT_PROMISC = 0
PUBLIC_IP_START = '12.234.32.130'
PUBLIC_IP_END = '12.234.32.255'
PUBLIC_IP_GATEWAY = '12.234.32.1'
PUBLIC_NETMASK = '255.255.255.0'
PUBLIC_NIC = 'eth1'
PUBLIC_PROMISC = 1
STORAGE_IP_START = '172.16.100.130'
STORAGE_IP_END = '172.16.100.255'
STORAGE_NETMASK = '255.255.255.0'
STORAGE_IP_GATEWAY = '172.16.100.1'
STORAGE_NIC = 'eth0'
STORAGE_PROMISC = 0
HOME_PERCENTAGE = 5
TMP_PERCENTAGE = 5
VAR_PERCENTAGE = 10
HOST_OS = 'CentOS-6.5-x86_64'


PRESET_VALUES = {
    'LANGUAGE': 'EN',
    'TIMEZONE': 'GMT',
    'HTTPS_PROXY': 'http://10.145.89.100:3128',
    'NO_PROXY': ['127.0.0.1'],
    'DOMAIN': 'ods.com',
    'NAMESERVERS': ['10.145.89.100'],
    'NTP_SERVER': '10.145.89.100',
    'GATEWAY': '10.145.88.1',
    'PROXY': 'http://10.145.89.100:3128',
    'OS_NAME_PATTERN': 'CentOS.*',
    'ADAPTER_NAME': 'openstack_icehouse',
    'FLAVOR_PATTERN': 'allinone.*',
    'ROLES_LIST': ['allinone-compute'],
    'MACHINES_TO_ADD': ['00:0c:29:a7:ea:4b'],
    'BUILD_TIMEOUT': 60,
    'SEARCH_PATH': ['ods.com'],
    'SERVER_USERNAME': 'root',
    'SERVER_PASSWORD': 'root'
}
for v in PRESET_VALUES:
    if v in os.environ.keys():
        PRESET_VALUES[v] = os.environ.get(v)
        print (v + PRESET_VALUES[v] + " is set by env variables")
    else:
        print (PRESET_VALUES[v])

# instantiate a client
client = Client(COMPASS_SERVER_URL)

# login
status, response = client.login(COMPASS_LOGIN_EMAIL, COMPASS_LOGIN_PASSWORD)
print '============================================================'
print 'login status: %s response: %s' % (status, response)
if status >= 400:
    sys.exit(1)

# list all switches
status, response = client.list_switches()
print '============================================================='
print 'get all switches status: %s response: %s' % (status, response)

# add a switch
status, response = client.add_switch(
    SWITCH_IP,
    SWITCH_SNMP_VERSION,
    SWITCH_SNMP_COMMUNITY
)
print '============================================'
print 'adding a switch..status: %s, response: %s' % (status, response)

# if switch already exists, get one from all switches
switch = None
if status < 400:
    switch = response
else:
    status, response = client.list_switches()
    print '========================================='
    print 'list switches status %s response %s' % (status, response)
    if status >= 400:
        sys.exit(1)
    for switch_ in response:
        if switch_['ip'] == SWITCH_IP:
            switch = switch_
            break

switch_id = switch['id']
switch_ip = switch['ip']
print '======================'
print 'switch has been set as %s' % switch_ip

# wait till switch state becomes under_monitoring
while switch['state'] != 'under_monitoring':
    print 'waiting for state to become under_monitoring'
    client.poll_switch(switch_id)
    status, resp = client.get_switch(switch_id)
    print '====================================='
    print 'poll switch status %s response %s' % (status, resp)
    switch = resp
    print 'switch is in state: %s' % switch['state']
    time.sleep(5)

print '========================================='
print 'switch state now is %s' % (switch['state'])

# create a machine list
machine_macs = {}
machines = {}
for machine in PRESET_VALUES['MACHINES_TO_ADD']:
    status, response = client.list_machines(mac=machine)
    print '============================================'
    print 'list machines status %s response %s' % (status, response)
    if status >= 400:
        sys.exit(1)
    if status == 200 and response != []:
        machine_id = response[0]['id']
        machine_macs[machine_id] = response[0]['mac']
        machines = response

print '================================='
print 'found machines are : %s' % machines

machines_to_add = PRESET_VALUES['MACHINES_TO_ADD']
if set(machine_macs.values()) != set(machines_to_add):
    print 'only found macs %s while expected are %s' % (
        machine_macs.values(), machines_to_add)
    sys.exit(1)

# list all adapters
status, response = client.list_adapters()
print '==============================='
print 'all adapters are: %s' % response
if status >= 400:
    sys.exit(1)

adapters = response
adapter_id = None
os_id = None
flavor_id = None
adapter_name = PRESET_VALUES['ADPATER_NAME']
os_pattern = re.compile(PRESET_VALUES['OS_NAME_PATTERN'])
flavor_pattern = re.compile(PRESET_VALUES['FLAVOR_PATTERN'])
for adapter in adapters:
    if adapter_name == adapter['name']:
        adapter_id = adapter['id']
    for supported_os in adapter['supported_oses']:
        if os_pattern.match(supported_os['name']):
            os_id = supported_os['id']
            break
    for flavor in adapter['flavors']:
        if flavor_pattern.match(flavor['name']):
            flavor_id = flavor['id']
    if adapter_id and os_id and flavor_id:
        break

print '======================================================='
print 'using adapter %s os %s flavor %s to deploy cluster' % (
    adapter_id, os_id, flavor_id
)

# add a cluster
status, response = client.add_cluster(
    CLUSTER_NAME,
    adapter_id,
    os_id,
    flavor_id
)
print '==============================================================='
print 'add cluster %s status %s: %s' % (CLUSTER_NAME, status, response)
if status >= 400:
    sys.exit(1)

status, response = client.list_clusters(name=CLUSTER_NAME)
print '================================================================'
print 'list clusters %s status %s: %s' % (CLUSTER_NAME, status, response)
if status >= 400:
    sys.exit(1)

cluster = response[0]
cluster_id = cluster['id']

print '=================='
print 'cluster is %s' % cluster

# Add hosts to the cluster
machines_dict = {}
machine_id_list = []
for machine in machines:
    id_mapping = {}
    id_mapping['machine_id'] = machine['id']
    machine_id_list.append(id_mapping)

machines_dict['machines'] = machine_id_list

status, response = client.add_hosts_to_cluster(
    cluster_id, machines_dict
)
print '==================================='
print 'add hosts %s to cluster status %s response %s' % (
    machines_dict, status, response)
if status >= 400:
    sys.exit(1)

# Add two subnets
subnet_1 = '10.145.89.0/24'
subnet_2 = '192.168.100.0/24'

status, response = client.add_subnet(subnet_1)
print '=================='
print 'add subnet %s status %s: %s' % (subnet_1, status, response)
if status >= 400:
    sys.exit(1)

status, response = client.add_subnet(subnet_2)
print '=================='
print 'add subnet %s status %s: %s' % (subnet_2, status, response)
if status >= 400:
    sys.exit(1)

status, subnet1 = client.list_subnets(subnet=subnet_1)
print '==========================================================='
print 'list subnet %s status %s: %s' % (subnet_1, status, subnet1)
if status >= 400:
    sys.exit(1)

status, subnet2 = client.list_subnets(subnet=subnet_2)
print '==========================================================='
print 'list subnet %s status %s: %s' % (subnet_2, status, subnet2)
if status >= 400:
    sys.exit(1)

subnet1_id = subnet1[0]['id']
subnet2_id = subnet2[0]['id']
print '========================'
print 'subnet1 has id: %s, subnet is %s' % (subnet1_id, subnet1)
print 'subnet2 has id: %s, subnet is %s' % (subnet2_id, subnet2)

# Add host network
status, response = client.list_cluster_hosts(cluster_id)
print '================================================'
print 'list cluster hosts status %s: %s' % (status, response)
if status >= 400:
    sys.exit(1)

host = response[0]
host_id = host['id']
print '=================='
print 'host is: %s' % host

status, response = client.add_host_network(
    host_id,
    'eth0',
    '10.145.89.200',
    subnet1_id,
    is_mgmt=True
)
print '======================='
print 'add eth0 network status %s: %s' % (status, response)
if status >= 400:
    sys.exit(1)

status, response = client.add_host_network(
    host_id,
    'eth1',
    '192.168.100.200',
    subnet2_id,
    is_promiscuous=True
)
print '======================='
print 'add eth1 network status %s: %s' % (status, response)
if status >= 400:
    sys.exit(1)

# Update os config to cluster
cluster_os_config = {
    'general': {
        'language': PRESET_VALUES['LANGUAGE'],
        'timezone': PRESET_VALUES['TIMEZONE'],
        'http_proxy': PRESET_VALUES['PROXY'],
        'https_proxy': PRESET_VALUES['HTTPS_PROXY'],
        'no_proxy': PRESET_VALUES['NO_PROXY'],
        'ntp_server': PRESET_VALUES['NTP_SERVER'],
        'dns_servers': PRESET_VALUES['NAMESERVERS'],
        'domain': PRESET_VALUES['DOMAIN'],
        'search_path': PRESET_VALUES['SEARCH_PATH'],
        'default_gateway': PRESET_VALUES['GATEWAY']
    },
    'server_credentials': {
        'username': PRESET_VALUES['SERVER_USERNAME'],
        'password': PRESET_VALUES['SERVER_PASSWORD']
    },
    'partition': {
        '/var': {
            'percentage': VAR_PERCENTAGE,
        },
        '/home': {
            'percentage': HOME_PERCENTAGE,
        }
    }
}


cluster_package_config = {
    'security': {
        'service_credentials': {
            'image': {
                'username': SERVICE_USERNAME,
                'password': SERVICE_PASSWORD
            },
            'compute': {
                'username': SERVICE_USERNAME,
                'password': SERVICE_PASSWORD
            },
            'dashboard': {
                'username': SERVICE_USERNAME,
                'password': SERVICE_PASSWORD
            },
            'identity': {
                'username': SERVICE_USERNAME,
                'password': SERVICE_PASSWORD
            },
            'metering': {
                'username': SERVICE_USERNAME,
                'password': SERVICE_PASSWORD
            },
            'rabbitmq': {
                'username': SERVICE_USERNAME,
                'password': SERVICE_PASSWORD
            },
            'volume': {
                'username': SERVICE_USERNAME,
                'password': SERVICE_PASSWORD
            },
            'mysql': {
                'username': SERVICE_USERNAME,
                'password': SERVICE_PASSWORD
            }
        },
        'console_credentials': {
            'admin': {
                'username': CONSOLE_USERNAME,
                'password': CONSOLE_PASSWORD
            },
            'compute': {
                'username': CONSOLE_USERNAME,
                'password': CONSOLE_PASSWORD
            },
            'dashboard': {
                'username': CONSOLE_USERNAME,
                'password': CONSOLE_PASSWORD
            },
            'image': {
                'username': CONSOLE_USERNAME,
                'password': CONSOLE_PASSWORD
            },
            'metering': {
                'username': CONSOLE_USERNAME,
                'password': CONSOLE_PASSWORD
            },
            'network': {
                'username': CONSOLE_USERNAME,
                'password': CONSOLE_PASSWORD
            },
            'object-store': {
                'username': CONSOLE_USERNAME,
                'password': CONSOLE_PASSWORD
            },
            'volume': {
                'username': CONSOLE_USERNAME,
                'password': CONSOLE_PASSWORD
            }
        }
    },
    'network_mapping': {
        'management': MANAGEMENT_NIC,
        'tenant': TENANT_NIC,
        'storage': STORAGE_NIC,
        'public': PUBLIC_NIC
    }
}

status, response = client.update_cluster_config(
    cluster_id,
    cluster_os_config,
    cluster_package_config
)

print '======================================='
print 'cluster %s update status %s: %s' % (
    cluster_id, status, response)
if status >= 400:
    sys.exit(1)

status, response = client.update_cluster_host(
    cluster_id, host_id, roles=PRESET_VALUES['ROLES_LIST'])
print '================================================='
print 'update cluster host %s/%s status %s: %s' % (
    cluster_id, host_id, status, response)
if status >= 400:
    sys.exit(1)

# Review and deploy
status, response = client.review_cluster(
    cluster_id, review={'hosts': [host_id]})
print '======================================='
print 'reviewing cluster status %s: %s' % (status, response)
if status >= 400:
    sys.exit(1)

status, response = client.deploy_cluster(
    cluster_id, deploy={'hosts': [host_id]})
print '======================================='
print 'deploy cluster status %s: %s' % (status, response)
if status >= 400:
    sys.exit(1)
