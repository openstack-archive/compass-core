#!/usr/bin/env python
#
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

"""binary to deploy a cluster by compass client api."""
import logging
import netaddr
import os
import re
import requests
import site
import socket
import sys
import time

activate_this = '$PythonHome/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))
site.addsitedir('$PythonHome/lib/python2.6/site-packages')
sys.path.append('$PythonHome')
os.environ['PYTHON_EGG_CACHE'] = '/tmp/.egg'

from compass.apiclient.restful import Client
from compass.utils import flags
from compass.utils import logsetting


flags.add('compass_server',
          help='compass server url',
          default='http://127.0.0.1/api')
flags.add('compass_user_email',
          help='compass user email',
          default='admin@huawei.com')
flags.add('compass_user_password',
          help='compass user password',
          default='admin')
flags.add('switch_ips',
          help='comma seperated switch ips',
          default='')
flags.add('switch_credential',
          help='comma separated <credential key>=<credential value>',
          default='version=2c,community=public')
flags.add('switch_max_retries', type='int',
          help='max retries of poll switch',
          default=5)
flags.add('switch_retry_interval', type='int',
          help='interval to repoll switch',
          default=10)
flags.add_bool('poll_switches',
               help='if the client polls switches',
               default=True)
flags.add('machines',
          help='comma separated mac addresses of machines',
          default='')
flags.add('subnets',
          help='comma seperated subnets',
          default='')
flags.add('adapter_name',
          help='adapter name',
          default='')
flags.add('adapter_os_pattern',
          help='adapter os name',
          default=r'(?i)centos.*')
flags.add('adapter_target_system_pattern',
          help='adapter target system name',
          default='openstack.*')
flags.add('adapter_flavor_pattern',
          help='adapter flavor name',
          default='allinone')
flags.add('cluster_name',
          help='cluster name',
          default='cluster1')
flags.add('language',
          help='language',
          default='EN')
flags.add('timezone',
          help='timezone',
          default='GMT')
flags.add('http_proxy',
          help='http proxy',
          default='')
flags.add('https_proxy',
          help='https proxy',
          default='')
flags.add('no_proxy',
          help='no proxy',
          default='')
flags.add('ntp_server',
          help='ntp server',
          default='')
flags.add('dns_servers',
          help='dns servers',
          default='')
flags.add('domain',
          help='domain',
          default='')
flags.add('search_path',
          help='search path',
          default='')
flags.add('default_gateway',
          help='default gateway',
          default='')
flags.add('server_credential',
          help=(
              'server credential formatted as '
              '<username>=<password>'
          ),
          default='root=root')
flags.add('service_credentials',
          help=(
              'comma seperated service credentials formatted as '
              '<servicename>:<username>=<password>,...'
          ),
          default='')
flags.add('console_credentials',
          help=(
              'comma seperated console credential formated as '
              '<consolename>:<username>=<password>'
          ),
          default='')
flags.add('hostnames',
          help='comma seperated hostname',
          default='')
flags.add('host_networks',
          help=(
              'semicomma seperated host name and its networks '
              '<hostname>:<interface_name>=<ip>|<is_mgmt>|<is_promiscuous>,...'
          ),
          default='')
flags.add('partitions',
          help=(
              'comma seperated partitions '
              '<partition name>=<partition_value>'
          ),
          default='tmp:percentage=10%,var:percentage=30%,home:percentage=30%')
flags.add('network_mapping',
          help=(
              'comma seperated network mapping '
              '<network_type>=<interface_name>'
          ),
          default='')
flags.add('host_roles',
          help=(
              'semicomma separated host roles '
              '<hostname>=<comma separated roles>'
          ),
          default='')
flags.add('default_roles',
          help=(
              'comma seperated default roles '
              '<rolename>'
          ),
          default='')
flags.add('deployment_timeout',
          help='deployment timeout in minutes',
          default=60)
flags.add('progress_update_check_interval',
          help='progress update status check interval in seconds',
          default=60)
flags.add('dashboard_url',
          help='dashboard url',
          default='')
flags.add('dashboard_link_pattern',
          help='dashboard link pattern',
          default=r'(?m)(http://\d+\.\d+\.\d+\.\d+:5000/v2\.0)')


def _get_client():
    """get apiclient object."""
    return Client(flags.OPTIONS.compass_server)


def _login(client):
    """get apiclient token."""
    status, resp = client.get_token(
        flags.OPTIONS.compass_user_email,
        flags.OPTIONS.compass_user_password
    )
    logging.info(
        'login status: %s, resp: %s',
        status, resp
    )
    if status >= 400:
        raise Exception(
            'failed to login %s with user %s',
            flags.OPTIONS.compass_server,
            flags.OPTIONS.compass_user_email
        )
    return resp['token']


def _get_machines(client):
    """get machines connected to the switch."""
    status, resp = client.list_machines()
    logging.info(
        'get all machines status: %s, resp: %s', status, resp)
    if status >= 400:
        msg = 'failed to get machines'
        raise Exception(msg)

    machines_to_add = set([
        machine for machine in flags.OPTIONS.machines.split(',')
        if machine
    ])
    logging.info('machines to add: %s', list(machines_to_add))
    machines = {}
    for machine in resp:
        mac = machine['mac']
        if mac in machines_to_add:
            machines[machine['id']] = mac

    logging.info('found machines: %s', machines.values())

    if set(machines.values()) != machines_to_add:
        msg = 'machines %s is missing' % (
            list(machines_to_add - set(machines.values()))
        )
        raise Exception(msg)

    return machines


def _poll_switches(client):
    """get all switches."""
    status, resp = client.list_switches()
    logging.info('get all switches status: %s resp: %s', status, resp)
    if status >= 400:
        msg = 'failed to get switches'
        raise Exception(msg)

    all_switches = {}
    for switch in resp:
        all_switches[switch['ip']] = switch

    # add a switch.
    switch_ips = [
        switch_ip for switch_ip in flags.OPTIONS.switch_ips.split(',')
        if switch_ip
    ]
    if not switch_ips:
        raise Exception(
            'there is no switches to poll')

    switch_credential = dict([
        credential.split('=', 1)
        for credential in flags.OPTIONS.switch_credential.split(',')
        if '=' in credential
    ])
    for switch_ip in switch_ips:
        if switch_ip not in all_switches:
            status, resp = client.add_switch(switch_ip, **switch_credential)
            logging.info('add switch %s status: %s resp: %s',
                         switch_ip, status, resp)
            if status >= 400:
                msg = 'failed to add switch %s' % switch_ip
                raise Exception(msg)

            all_switches[switch_ip] = resp
        else:
            logging.info('switch %s is already added', switch_ip)

    remain_retries = flags.OPTIONS.switch_max_retries
    while True:
        for switch_ip, switch in all_switches.items():
            status, resp = client.poll_switch(switch['id'])
            logging.info(
                'get switch %s status %s: %s',
                switch_ip, status, resp)
            if status >= 400:
                msg = 'failed to update switch %s' % switch_ip
                raise Exception(msg)
        remain_retries -= 1
        time.sleep(flags.OPTIONS.switch_retry_interval)
        for switch_ip, switch in all_switches.items():
            switch_id = switch['id']
            # if the switch is not in under_monitoring, wait for the
            # poll switch task update the switch information and change
            # the switch state.
            logging.info(
                'waiting for the switch %s into under_monitoring',
                switch_ip)
            status, resp = client.get_switch(switch_id)
            logging.info('get switch %s status: %s, resp: %s',
                         switch_ip, status, resp)
            if status >= 400:
                msg = 'failed to get switch %s' % switch_ip
                raise Exception(msg)

            switch = resp
            all_switches[switch_ip] = switch

            if switch['state'] == 'notsupported':
                msg = 'switch %s is not supported', switch_ip
                raise Exception(msg)
            elif switch['state'] in ['initialized', 'repolling']:
                logging.info('switch %s is not updated', switch_ip)
            elif switch['state'] == 'under_monitoring':
                logging.info('switch %s is ready', switch_ip)
        try:
            return _get_machines(client)
        except Exception:
            logging.error('failed to get all machines')

        if remain_retries <= 0:
            msg = 'max retries reached'
            raise Exception(msg)


def _get_adapter(client):
    """get adapter."""
    status, resp = client.list_adapters()
    logging.info(
        'get all adapters status: %s, resp: %s',
        status, resp
    )
    if status >= 400:
        msg = 'failed to get adapters'
        raise Exception(msg)

    adapter_name = flags.OPTIONS.adapter_name
    os_pattern = flags.OPTIONS.adapter_os_pattern
    if os_pattern:
        os_re = re.compile(os_pattern)
    else:
        os_re = None
    target_system_pattern = flags.OPTIONS.adapter_target_system_pattern
    if target_system_pattern:
        target_system_re = re.compile(target_system_pattern)
    else:
        target_system_re = None
    flavor_pattern = flags.OPTIONS.adapter_flavor_pattern
    if flavor_pattern:
        flavor_re = re.compile(flavor_pattern)
    else:
        flavor_re = None
    adapter_id = None
    os_id = None
    flavor_id = None
    adapter = None
    for item in resp:
        adapter_id = None
        os_id = None
        flavor_id = None
        adapter = item
        for supported_os in adapter['supported_oses']:
            if not os_re or os_re.match(supported_os['name']):
                os_id = supported_os['os_id']
                break

        if not os_id:
            logging.info('no os found for adapter %s', adapter)
            continue

        if 'flavors' in adapter:
            for flavor in adapter['flavors']:
                if not flavor_re or flavor_re.match(flavor['name']):
                    flavor_id = flavor['id']
                    break

        if adapter_name and adapter['name'] == adapter_name:
            adapter_id = adapter['id']
            logging.info('adapter name %s match: %s', adapter_name, adapter)
        elif 'distributed_system_name' in item:
            if (
                not target_system_re or
                target_system_re.match(adapter['distributed_system_name'])
            ):
                adapter_id = adapter['id']
                logging.info(
                    'distributed system name pattern %s match: %s',
                    target_system_pattern, adapter
                )

        if adapter_id:
            logging.info('adadpter does not match: %s', adapter)
            break

    if not adapter_id:
        msg = 'no adapter found'
        raise Exception(msg)

    if not os_id:
        msg = 'no os found for %s' % os_pattern
        raise Exception(msg)

    if flavor_re and not flavor_id:
        msg = 'no flavor found for %s' % flavor_pattern
        raise Exception(msg)

    logging.info('adpater for deploying a cluster: %s', adapter_id)
    return (adapter_id, os_id, flavor_id)


def _add_subnets(client):
    status, resp = client.list_subnets()
    logging.info('get all subnets status: %s resp: %s', status, resp)
    if status >= 400:
        msg = 'failed to get subnets'
        raise Exception(msg)

    all_subnets = {}
    for subnet in resp:
        all_subnets[subnet['subnet']] = subnet

    subnets = [
        subnet for subnet in flags.OPTIONS.subnets.split(',')
        if subnet
    ]
    subnet_mapping = {}
    for subnet in subnets:
        if subnet not in all_subnets:
            status, resp = client.add_subnet(subnet)
            logging.info('add subnet %s status %s response %s',
                         subnet, status, resp)
            if status >= 400:
                msg = 'failed to add subnet %s' % subnet
                raise Exception(msg)
            subnet_mapping[resp['subnet']] = resp['id']
        else:
            subnet_mapping[subnet] = all_subnets[subnet]['id']
    if not subnet_mapping:
        raise Exception(
            'there is not subnets found'
        )
    return subnet_mapping


def _add_cluster(client, adapter_id, os_id, flavor_id, machines):
    """add a cluster."""
    cluster_name = flags.OPTIONS.cluster_name
    if not cluster_name:
        raise Exception(
            'no cluster name set')
    status, resp = client.add_cluster(
        cluster_name, adapter_id,
        os_id, flavor_id)
    logging.info('add cluster %s status: %s, resp: %s',
                 cluster_name, status, resp)
    if status >= 400:
        msg = 'failed to add cluster %s with adapter %s os %s flavor %s' % (
            cluster_name, adapter_id, os_id, flavor_id)
        raise Exception(msg)

    cluster = resp
    cluster_id = cluster['id']
    if 'flavor' in cluster:
        flavor = cluster['flavor']
    else:
        flavor = None
    if flavor and 'roles' in flavor:
        roles = flavor['roles']
    else:
        roles = []
    role_mapping = {}
    for role in roles:
        if role.get('optional', False):
            role_mapping[role['name']] = 1
        else:
            role_mapping[role['name']] = 0
    logging.info('cluster %s role mapping: %s', cluster_id, role_mapping)

    hostnames = [
        hostname for hostname in flags.OPTIONS.hostnames.split(',')
        if hostname
    ]
    if len(machines) != len(hostnames):
        msg = 'hostname %s length does not match machines mac %s length' % (
            hostnames, machines)
        raise Exception(msg)

    machines_dict = []
    for machine_id, hostname in map(None, machines, hostnames):
        machines_dict.append({
            'machine_id': machine_id,
            'name': hostname
        })
    # add hosts to the cluster.
    status, resp = client.add_hosts_to_cluster(
        cluster_id,
        {'machines': machines_dict})
    logging.info('add machines %s to cluster %s status: %s, resp: %s',
                 machines_dict, cluster_id, status, resp)
    if status >= 400:
        msg = 'failed to add machines %s to cluster %s' % (
            machines, cluster_name)
        raise Exception(msg)
    host_mapping = {}
    for host in resp['hosts']:
        host_mapping[host['hostname']] = host['id']
    logging.info('added hosts in cluster %s: %s', cluster_id, host_mapping)
    if len(host_mapping) != len(machines):
        msg = 'machines %s to add to the cluster %s while hosts %s' % (
            machines, cluster_name, host_mapping)
        raise Exception(msg)
    return (cluster_id, host_mapping, role_mapping)


def _set_cluster_os_config(client, cluster_id, host_ips):
    """set cluster os config."""
    os_config = {}
    language = flags.OPTIONS.language
    timezone = flags.OPTIONS.timezone
    http_proxy = flags.OPTIONS.http_proxy
    https_proxy = flags.OPTIONS.https_proxy
    if not https_proxy and http_proxy:
        https_proxy = http_proxy
    no_proxy = [
        no_proxy for no_proxy in flags.OPTIONS.no_proxy.split(',')
        if no_proxy
    ]
    compass_name = socket.gethostname()
    compass_ip = socket.gethostbyname(compass_name)
    if http_proxy:
        for hostname, ips in host_ips.items():
            no_proxy.append(hostname)
            no_proxy.extend(ips)
    ntp_server = flags.OPTIONS.ntp_server
    if not ntp_server:
        ntp_server = compass_ip
    dns_servers = [
        dns_server for dns_server in flags.OPTIONS.dns_servers.split(',')
        if dns_server
    ]
    if not dns_servers:
        dns_servers = [compass_ip]
    domain = flags.OPTIONS.domain
    if not domain:
        raise Exception('domain is not defined')
    search_path = [
        search_path for search_path in flags.OPTIONS.search_path.split(',')
        if search_path
    ]
    if not search_path:
        search_path = [domain]
    default_gateway = flags.OPTIONS.default_gateway
    if not default_gateway:
        raise Exception('default gateway is not defined')
    os_config['general'] = {
        'language': language,
        'timezone': timezone,
        'ntp_server': ntp_server,
        'dns_servers': dns_servers,
        'default_gateway': default_gateway
    }
    if http_proxy:
        os_config['general']['http_proxy'] = http_proxy
    if https_proxy:
        os_config['general']['https_proxy'] = https_proxy
    if no_proxy:
        os_config['general']['no_proxy'] = no_proxy
    if domain:
        os_config['general']['domain'] = domain
    if search_path:
        os_config['general']['search_path'] = search_path
    server_credential = flags.OPTIONS.server_credential
    if '=' in server_credential:
        server_username, server_password = server_credential.split('=', 1)
    elif server_credential:
        server_username = server_credential
        server_password = server_username
    else:
        server_username = 'root'
        server_password = 'root'
    os_config['server_credentials'] = {
        'username': server_username,
        'password': server_password
    }
    partitions = [
        partition for partition in flags.OPTIONS.partitions.split(',')
        if partition
    ]
    os_config['partition'] = {}
    for partition in partitions:
        if '=' not in partition:
            raise Exception(
                'there is no = in partition %s' % partition
            )
        partition_name, partition_value = partition.split('=', 1)
        if not partition_name:
            raise Exception(
                'there is no partition name in %s' % partition)
        if not partition_value:
            raise Exception(
                'there is no partition value in %s' % partition)

        if partition_value.endswith('%'):
            partition_type = 'percentage'
            partition_value = int(partition_value[:-1])
        else:
            partition_type = 'size'
        os_config['partition'][partition_name] = {
            partition_type: partition_value
        }
    status, resp = client.update_cluster_config(
        cluster_id, os_config=os_config)
    logging.info(
        'set os config %s to cluster %s status: %s, resp: %s',
        os_config, cluster_id, status, resp)
    if status >= 400:
        msg = 'failed to set os config %s to cluster %s' % (
            os_config, cluster_id)
        raise Exception(msg)


def _set_host_networking(client, host_mapping, subnet_mapping):
    """set cluster hosts networking."""
    host_ips = {}
    for host_network in flags.OPTIONS.host_networks.split(';'):
        hostname, networks_str = host_network.split(':', 1)
        if hostname not in host_mapping:
            msg = 'hostname %s does not exist in host mapping %s' % (
                hostname, host_mapping
            )
            raise Exception(msg)
        host_id = host_mapping[hostname]
        networks = networks_str.split(',')
        for network in networks:
            interface, network_properties_str = network.split('=', 1)
            network_properties = network_properties_str.split('|')
            ip_addr = network_properties[0]
            if not ip_addr:
                raise Exception(
                    'ip is not set for host %s interface %s' % (
                        hostname, interface
                    )
                )
            ip = netaddr.IPAddress(ip_addr)
            subnet_id = None
            for subnet_addr, subnetid in subnet_mapping.items():
                subnet = netaddr.IPNetwork(subnet_addr)
                if ip in subnet:
                    subnet_id = subnetid
                    break
            if not subnet_id:
                msg = 'no subnet found for ip %s' % ip_addr
                raise Exception(msg)
            properties = dict([
                (network_property, True)
                for network_property in network_properties[1:]
            ])
            logging.info(
                'add host %s interface %s ip %s network proprties %s',
                hostname, interface, ip_addr, properties)
            status, response = client.add_host_network(
                host_id, interface, ip=ip_addr, subnet_id=subnet_id,
                **properties
            )
            logging.info(
                'add host %s interface %s ip %s network properties %s '
                'status %s: %s',
                hostname, interface, ip_addr, properties,
                status, response
            )
            if status >= 400:
                msg = 'failed to set host %s interface %s network' % (
                    hostname, interface
                )
                raise Exception(msg)
            host_ips.setdefault(hostname, []).append(ip_addr)
    return host_ips


def _set_cluster_package_config(client, cluster_id):
    """set cluster package config."""
    package_config = {
        'security': {
            'service_credentials': {
            },
            'console_credentials': {
            }
        }
    }
    service_credentials = [
        service_credential
        for service_credential in flags.OPTIONS.service_credentials.split(',')
        if service_credential
    ]
    for service_credential in service_credentials:
        if ':' not in service_credential:
            raise Exception(
                'there is no : in service credential %s' % service_credential
            )
        service_name, service_pair = service_credential.split(':', 1)
        if '=' not in service_pair:
            raise Exception(
                'there is no = in service %s security' % service_name
            )
        username, password = service_pair.split('=', 1)
        package_config['security']['service_credentials'][service_name] = {
            'username': username,
            'password': password
        }
    console_credentials = [
        console_credential
        for console_credential in flags.OPTIONS.console_credentials.split(',')
        if console_credential
    ]
    for console_credential in console_credentials:
        if ':' not in console_credential:
            raise Exception(
                'there is no : in console credential %s' % console_credential
            )
        console_name, console_pair = console_credential.split(':', 1)
        if '=' not in console_pair:
            raise Exception(
                'there is no = in console %s security' % console_name
            )
        username, password = console_pair.split('=', 1)
        package_config['security']['console_credentials'][service_name] = {
            'username': username,
            'password': password
        }
    package_config['network_mapping'] = dict([
        network_pair.split('=', 1)
        for network_pair in flags.OPTIONS.network_mapping.split(',')
        if '=' in network_pair
    ])
    status, resp = client.update_cluster_config(
        cluster_id, package_config=package_config)
    logging.info(
        'set package config %s to cluster %s status: %s, resp: %s',
        package_config, cluster_id, status, resp)
    if status >= 400:
        msg = 'failed to set package config %s to cluster %s' % (
            package_config, cluster_id)
        raise Exception(msg)


def _set_host_roles(client, cluster_id, host_id, roles, role_mapping):
    status, response = client.update_cluster_host(
        cluster_id, host_id, roles=roles)
    logging.info(
        'set cluster %s host %s roles %s status %s: %s',
        cluster_id, host_id, roles, status, response
    )
    if status >= 400:
        raise Exception(
            'failed to set cluster %s host %s roles %s' % (
                cluster_id, host_id, roles
            )
        )
    for role in roles:
        if role in role_mapping and role_mapping[role] > 0:
            role_mapping[role] -= 1


def _set_hosts_roles(client, cluster_id, host_mapping, role_mapping):
    host_roles = {}
    for host_str in flags.OPTIONS.host_roles.split(';'):
        if not host_str:
            continue
        hostname, roles_str = host_str.split('=', 1)
        if hostname not in host_mapping:
            raise Exception(
                'hostname %s not found in host mapping %s' % (
                    hostname, host_mapping
                )
            )
        host_id = host_mapping[hostname]
        roles = [role for role in roles_str.split(',') if role]
        _set_host_roles(client, cluster_id, host_id, roles, role_mapping)
        host_roles[hostname] = roles

    # assign unassigned roles to unassigned hosts
    unassigned_hostnames = []
    for hostname, _ in host_mapping.items():
        if hostname not in host_roles:
            unassigned_hostnames.append(hostname)
    unassigned_roles = []
    for role, count in role_mapping.items():
        if count > 0:
            unassigned_roles.append(role)
    if len(unassigned_hostnames) < len(unassigned_roles):
        raise Exception(
            'there is no enough hosts %s to assign roles %s' % (
                unassigned_hostnames, unassigned_roles
            )
        )
    for offset, role in enumerate(unassigned_roles):
        hostname = unassigned_hostnames[offset]
        host_id = host_mapping[hostname]
        roles = [role]
        _set_host_roles(client, cluster_id, host_id, roles, role_mapping)
        host_roles[hostname] = roles
    unassigned_hostnames = unassigned_hostnames[len(unassigned_roles):]
    unassigned_roles = []

    # assign default roles to unassigned hosts
    default_roles = [
        role for role in flags.OPTIONS.default_roles.split(',')
        if role
    ]
    if not default_roles and unassigned_hostnames:
        raise Exception(
            'hosts %s do not have roles set' % unassigned_hostnames
        )
    for hostname in unassigned_hostnames:
        host_id = host_mapping[hostname]
        roles = [default_roles[0]]
        _set_host_roles(client, cluster_id, host_id, roles, role_mapping)
        host_roles[hostname] = roles
        default_roles = default_roles[1:]
        default_roles.extend(roles)

    return host_roles


def _deploy_clusters(client, cluster_id, host_mapping):
    """deploy cluster."""
    host_ids = [host_id for _, host_id in host_mapping.items()]
    status, response = client.review_cluster(
        cluster_id, review={'hosts': host_ids}
    )
    logging.info(
        'review cluster %s hosts %s, status %s: %s',
        cluster_id, host_ids, status, response
    )
    if status >= 400:
        raise Exception(
            'review cluster %s fails' % cluster_id
        )
    status, response = client.deploy_cluster(
        cluster_id, deploy={'hosts': host_ids}
    )
    logging.info(
        'deploy cluster %s hosts %s status %s: %s',
        cluster_id, host_ids, status, response
    )
    if status >= 400:
        raise Exception(
            'deploy cluster %s fails' % cluster_id
        )


def _get_installing_progress(client, cluster_id, host_mapping):
    """get intalling progress."""
    timeout = time.time() + 60 * float(flags.OPTIONS.deployment_timeout)
    cluster_installed = False
    cluster_failed = False
    hosts_installed = {}
    hosts_failed = {}
    install_finished = False
    while time.time() < timeout:
        status, cluster_state = client.get_cluster_state(cluster_id)
        logging.info(
            'get cluster %s state status %s: %s',
            cluster_id, status, cluster_state
        )
        if status >= 400:
            raise Exception(
                'failed to acquire cluster %s state' % cluster_id
            )
        if cluster_state['state'] == 'SUCCESSFUL':
            cluster_installed = True
        if cluster_state['state'] == 'ERROR':
            cluster_failed = True
        for hostname, host_id in host_mapping.items():
            status, host_state = client.get_cluster_host_state(
                cluster_id, host_id
            )
            logging.info(
                'get cluster %s host %s state status %s: %s',
                cluster_id, host_id, status, host_state
            )
            if status >= 400:
                raise Exception(
                    'failed to acquire cluster %s host %s state' % (
                        cluster_id, host_id
                    )
                )
            if host_state['state'] == 'SUCCESSFUL':
                hosts_installed[host_id] = True
            else:
                hosts_installed[host_id] = False
            if host_state['state'] == 'ERROR':
                hosts_failed[host_id] = True
            else:
                hosts_failed[host_id] = False

        cluster_finished = cluster_installed or cluster_failed
        hosts_finished = {}
        for _, host_id in host_mapping.items():
            hosts_finished[host_id] = (
                hosts_installed.get(host_id, False) or
                hosts_failed.get(host_id, False)
            )
        if cluster_finished and all(hosts_finished.values()):
            logging.info('all clusters/hosts are installed.')
            install_finished = True
            break
        else:
            logging.info(
                'there are some clusters/hosts in installing.'
                'sleep %s seconds and retry',
                flags.OPTIONS.progress_update_check_interval)
            time.sleep(float(flags.OPTIONS.progress_update_check_interval))

    if not install_finished:
        raise Exception(
            'cluster %s installation not finished: '
            'installed %s, failed: %s' % (
                cluster_id, hosts_installed, hosts_failed
            )
        )
    if cluster_failed or any(hosts_failed.values()):
        msg = 'cluster %s hosts %s is not all finished. failed hosts %s' % (
            cluster_id, host_mapping.values(), hosts_failed.keys()
        )
        raise Exception(msg)


def _check_dashboard_links(client, cluster_id):
    dashboard_url = flags.OPTIONS.dashboard_url
    if not dashboard_url:
        logging.info('no dashboarde url set')
        return
    dashboard_link_pattern = re.compile(
        flags.OPTIONS.dashboard_link_pattern)
    r = requests.get(dashboard_url, verify=False)
    r.raise_for_status()
    match = dashboard_link_pattern.search(r.text)
    if match:
        logging.info(
            'dashboard login page for cluster %s can be downloaded',
            cluster_id)
    else:
        msg = (
            '%s failed to be downloaded\n'
            'the context is:\n%s\n'
        ) % (dashboard_url, r.text)
        raise Exception(msg)


def main():
    flags.init()
    logsetting.init()
    client = _get_client()
    _login(client)
    if flags.OPTIONS.poll_switches:
        machines = _poll_switches(client)
    else:
        machines = _get_machines(client)
    subnet_mapping = _add_subnets(client)
    adapter_id, os_id, flavor_id = _get_adapter(client)
    cluster_id, host_mapping, role_mapping = _add_cluster(
        client, adapter_id, os_id, flavor_id, machines)
    host_ips = _set_host_networking(
        client, host_mapping, subnet_mapping
    )
    _set_cluster_os_config(client, cluster_id, host_ips)
    if flavor_id:
        _set_cluster_package_config(client, cluster_id)
    if role_mapping:
        _set_hosts_roles(client, cluster_id, host_mapping, role_mapping)
    _deploy_clusters(client, cluster_id, host_mapping)
    _get_installing_progress(client, cluster_id, host_mapping)
    _check_dashboard_links(client, cluster_id)


if __name__ == "__main__":
    main()
