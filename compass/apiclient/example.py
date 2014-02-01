#!/usr/bin/python
"""Example code to deploy a cluster by compass client api."""
import sys
import time

from compass.apiclient.restful import Client


COMPASS_SERVER_URL = 'http://10.145.88.210:8080'
SWITCH_IP = '10.145.88.1'
SWITCH_SNMP_VERSION = 'v2c'
SWITCH_SNMP_COMMUNITY = 'public'
MACHINES_TO_ADD = ['00:0c:29:c3:40:7c', '00:0c:29:e9:f6:a6']
CLUSTER_NAME = 'cluster'
HOST_NAME_PREFIX = 'host'
SERVER_USERNAME = 'root'
SERVER_PASSWORD = 'root'
SERVICE_USERNAME = 'service'
SERVICE_PASSWORD = 'service'
CONSOLE_USERNAME = 'console'
CONSOLE_PASSWORD = 'console'
NAMESERVERS = '10.145.88.210'
SEARCH_PATH = 'ods.com'
GATEWAY = '10.145.88.1'
PROXY = 'http://10.145.88.210:3128'
NTP_SERVER = '10.145.88.210'
MANAGEMENT_IP_START = '10.145.88.130'
MANAGEMENT_IP_END = '10.145.88.255'
MANAGEMENT_GATEWAY = '10.145.88.1'
MANAGEMENT_NETMASK = '255.255.255.0'
MANAGEMENT_NIC = 'eth0'
MANAGEMENT_PROMISC = 0
TENANT_IP_START = '192.168.100.100'
TENANT_IP_END = '192.168.100.255'
TENANT_GATEWAY = '192.168.100.1'
TENANT_NETMASK = '255.255.255.0'
TENANT_NIC = 'eth0'
TENANT_PROMISC = 0
PUBLIC_IP_START = '12.234.32.100'
PUBLIC_IP_END = '12.234.32.255'
PUBLIC_GATEWAY = '12.234.32.1'
PUBLIC_NETMASK = '255.255.255.0'
PUBLIC_NIC = 'eth1'
PUBLIC_PROMISC = 1
STORAGE_IP_START = '172.16.100.100'
STORAGE_IP_END = '172.16.100.255'
STORAGE_GATEWAY = '172.16.100.1'
STORAGE_NETMASK = '255.255.255.0'
STORAGE_NIC = 'eth0'
STORAGE_PROMISC = 0
HOME_PERCENTAGE = 40
TMP_PERCENTAGE = 10
VAR_PERCENTAGE = 15
ROLES_LIST = [[], ['os-single-controller']]


# get apiclient object.
client = Client(COMPASS_SERVER_URL)


# get all switches.
status, resp = client.get_switches()
print 'get all switches status: %s resp: %s' % (status, resp)

# add a switch.
status, resp = client.add_switch(
    SWITCH_IP, version=SWITCH_SNMP_VERSION,
    community=SWITCH_SNMP_COMMUNITY)

print 'add a switch status: %s resp: %s' % (status, resp)

if status < 400:
    switch = resp['switch']
else:
    status, resp =  client.get_switches()
    print 'get all switches status: %s resp: %s' % (status, resp)
    switch = None
    for switch in resp['switches']:
        if switch['ip'] == SWITCH_IP:
            break

switch_id = switch['id']
switch_ip = switch['ip']


# if the switch is not in under_monitoring, wait for the poll switch task
# update the swich information and change the switch state.
while switch['state'] != 'under_monitoring':
    print 'waiting for the switch into under_monitoring'
    status, resp = client.get_switch(switch_id)
    print 'get switch %s status: %s, resp: %s' % (switch_id, status, resp)
    switch = resp['switch']
    time.sleep(10)


# get machines connected to the switch.
status, resp = client.get_machines(switch_id=switch_id)
print 'get all machines under switch %s status: %s, resp: %s' % (
    switch_id, status, resp)
machines = {}
for machine in resp['machines']:
    mac = machine['mac']
    if mac in MACHINES_TO_ADD:
        machines[machine['id']] = mac

print 'machine to add: %s' % machines

if set(machines.values()) != set(MACHINES_TO_ADD):
    print 'only found macs %s while expected are %s' % (
        machines.values(), MACHINES_TO_ADD)
    sys.exit(1)


# get adapters.
status, resp = client.get_adapters()
print 'get all adapters status: %s, resp: %s' % (status, resp)
adapter_ids = []
for adapter in resp['adapters']:
    adapter_ids.append(adapter['id'])

adapter_id = adapter_ids[0]
print 'adpater for deploying a cluster: %s' % adapter_id


# add a cluster.
status, resp = client.add_cluster(
    cluster_name=CLUSTER_NAME, adapter_id=adapter_id)
print 'add cluster %s status: %s, resp: %s' % (CLUSTER_NAME, status, resp)
cluster = resp['cluster']
cluster_id = cluster['id']

# add hosts to the cluster.
status, resp = client.add_hosts(
    cluster_id=cluster_id,
    machine_ids=machines.keys())
print 'add hosts to cluster %s status: %s, resp: %s' % (
    cluster_id, status, resp)
host_ids = []
for host in resp['cluster_hosts']:
    host_ids.append(host['id'])

print 'added hosts: %s' % host_ids


# set cluster security
status, resp = client.set_security(
    cluster_id, server_username=SERVER_USERNAME,
    server_password=SERVER_PASSWORD,
    service_username=SERVICE_USERNAME,
    service_password=SERVICE_PASSWORD,
    console_username=CONSOLE_USERNAME,
    console_password=CONSOLE_PASSWORD)
print 'set security config to cluster %s status: %s, resp: %s' % (
    cluster_id, status, resp)


# set cluster networking
status, resp = client.set_networking(
    cluster_id,
    nameservers=NAMESERVERS,
    search_path=SEARCH_PATH,
    gateway=GATEWAY,
    proxy=PROXY,
    ntp_server=NTP_SERVER,
    management_ip_start=MANAGEMENT_IP_START,
    management_ip_end=MANAGEMENT_IP_END,
    management_gateway=MANAGEMENT_GATEWAY,
    management_netmask=MANAGEMENT_NETMASK,
    management_nic=MANAGEMENT_NIC,
    management_promisc=MANAGEMENT_PROMISC,
    tenant_ip_start=TENANT_IP_START,
    tenant_ip_end=TENANT_IP_END,
    tenant_gateway=TENANT_GATEWAY,
    tenant_netmask=TENANT_NETMASK,
    tenant_nic=TENANT_NIC,
    tenant_promisc=TENANT_PROMISC,
    public_ip_start=PUBLIC_IP_START,
    public_ip_end=PUBLIC_IP_END,
    public_gateway=PUBLIC_GATEWAY,
    public_netmask=PUBLIC_NETMASK,
    public_nic=PUBLIC_NIC,
    public_promisc=PUBLIC_PROMISC,
    storage_ip_start=STORAGE_IP_START,
    storage_ip_end=STORAGE_IP_END,
    storage_gateway=STORAGE_GATEWAY,
    storage_netmask=STORAGE_NETMASK,
    storage_nic=STORAGE_NIC,
    storage_promisc=STORAGE_PROMISC)
print 'set networking config to cluster %s status: %s, resp: %s' % (
    cluster_id, status, resp)


# set partiton of each host in cluster
status, resp = client.set_partition(cluster_id,
    home_percentage=HOME_PERCENTAGE,
    tmp_partition_percentage=TMP_PERCENTAGE,
    var_partition_percentage=VAR_PERCENTAGE)
print 'set partition config to cluster %s status: %s, resp: %s' % (
    cluster_id, status, resp)


# set each host config in cluster.
for host_id in host_ids:
    if ROLES_LIST:
        roles = ROLES_LIST.pop(0)
    else:
        roles = []
    status, resp = client.update_host_config(
        host_id, hostname='%s%s' % (HOST_NAME_PREFIX, host_id),
        roles=roles)
    print 'set roles to host %s status: %s, resp: %s' % (
        host_id, status, resp)


# deploy cluster.
status, resp = client.deploy_hosts(cluster_id)
print 'deploy cluster %s status: %s, resp: %s' % (cluster_id, status, resp)


# get intalling progress.
while True:
    status, resp = client.get_cluster_installing_progress(cluster_id)
    print 'get cluster %s installing progress status: %s, resp: %s' % (
        cluster_id, status, resp)
    progress = resp['progress']
    if (progress['state'] not in ['UNINITIALIZED', 'INSTALLING'] or
        progress['percentage'] >= 1.0):
        break

    for host_id in host_ids:
        status, resp = client.get_host_installing_progress(host_id)
        print 'get host %s installing progress status: %s, resp: %s' % (
            host_id, status, resp)

    time.sleep(10)


status, resp = client.get_dashboard_links(cluster_id)
print 'get cluster %s dashboardlinks status: %s, resp: %s' % (
    cluster_id, status, resp)
