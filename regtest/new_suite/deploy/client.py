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
import os
import re
import socket
import sys
import time
import yaml
import netaddr
import requests
import json
import itertools
import threading
from collections import defaultdict
from restful import Client

ROLE_UNASSIGNED = True
ROLE_ASSIGNED = False

import log as logging
LOG = logging.getLogger(__name__)

from oslo_config import cfg
CONF = cfg.CONF

def byteify(input):
    if isinstance(input, dict):
        return dict([(byteify(key),byteify(value)) for key,value in input.iteritems()])
    elif isinstance(input, list):
        return [byteify(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input

opts = [
    cfg.StrOpt('compass_server',
              help='compass server url',
              default='http://127.0.0.1/api'),
    cfg.StrOpt('compass_user_email',
              help='compass user email',
              default='admin@huawei.com'),
    cfg.StrOpt('compass_user_password',
              help='compass user password',
              default='admin'),
    cfg.StrOpt('switch_ips',
              help='comma seperated switch ips',
              default=''),
    cfg.StrOpt('switch_credential',
              help='comma separated <credential key>=<credential value>',
              default='version=2c,community=public'),
    cfg.IntOpt('switch_max_retries',
              help='max retries of poll switch',
              default=10),
    cfg.IntOpt('switch_retry_interval',
              help='interval to repoll switch',
              default=10),
    cfg.BoolOpt('poll_switches',
                help='if the client polls switches',
                default=True),
    cfg.StrOpt('machines',
              help='comma separated mac addresses of machines',
              default=''),
    cfg.StrOpt('subnets',
              help='comma seperated subnets',
              default=''),
    cfg.StrOpt('adapter_name',
              help='adapter name',
              default=''),
    cfg.StrOpt('adapter_os_pattern',
              help='adapter os name',
              default=r'^(?i)centos.*'),
    cfg.StrOpt('adapter_target_system_pattern',
              help='adapter target system name',
              default='^openstack$'),
    cfg.StrOpt('adapter_flavor_pattern',
              help='adapter flavor name',
              default='allinone'),
    cfg.StrOpt('cluster_name',
              help='cluster name',
              default='cluster1'),
    cfg.StrOpt('language',
              help='language',
              default='EN'),
    cfg.StrOpt('timezone',
              help='timezone',
              default='GMT'),
    cfg.StrOpt('http_proxy',
              help='http proxy',
              default=''),
    cfg.StrOpt('https_proxy',
              help='https proxy',
              default=''),
    cfg.StrOpt('no_proxy',
              help='no proxy',
              default=''),
    cfg.StrOpt('ntp_server',
              help='ntp server',
              default=''),
    cfg.StrOpt('dns_servers',
              help='dns servers',
              default=''),
    cfg.StrOpt('domain',
              help='domain',
              default=''),
    cfg.StrOpt('search_path',
              help='search path',
              default=''),
    cfg.StrOpt('local_repo_url',
              help='local repo url',
              default=''),
    cfg.StrOpt('default_gateway',
              help='default gateway',
              default=''),
    cfg.StrOpt('server_credential',
              help=(
                  'server credential formatted as '
                  '<username>=<password>'
              ),
              default='root=root'),
    cfg.StrOpt('os_config_json_file',
              help='json formatted os config file',
              default=''),
    cfg.StrOpt('service_credentials',
              help=(
                  'comma seperated service credentials formatted as '
                  '<servicename>:<username>=<password>,...'
              ),
              default=''),
    cfg.StrOpt('console_credentials',
              help=(
                  'comma seperated console credential formated as '
                  '<consolename>:<username>=<password>'
              ),
              default=''),
    cfg.StrOpt('hostnames',
              help='comma seperated hostname',
              default=''),
    cfg.StrOpt('host_networks',
              help=(
                  'semicomma seperated host name and its networks '
                  '<hostname>:<interface_name>=<ip>|<is_mgmt>|<is_promiscuous>,...'
              ),
              default=''),
    cfg.StrOpt('partitions',
              help=(
                  'comma seperated partitions '
                  '<partition name>=<partition_value>'
              ),
              default='tmp:percentage=10%,var:percentage=30%,home:percentage=30%'),
    cfg.StrOpt('network_mapping',
              help=(
                  'comma seperated network mapping '
                  '<network_type>=<interface_name>'
              ),
              default=''),
    cfg.StrOpt('package_config_json_file',
              help='json formatted os config file',
              default=''),
    cfg.StrOpt('host_roles',
              help=(
                  'semicomma separated host roles '
                  '<hostname>=<comma separated roles>'
              ),
              default=''),
    cfg.StrOpt('default_roles',
              help=(
                  'comma seperated default roles '
                  '<rolename>'
              ),
              default=''),
    cfg.IntOpt('action_timeout',
              help='action timeout in seconds',
              default=60),
    cfg.IntOpt('deployment_timeout',
              help='deployment timeout in minutes',
              default=60),
    cfg.IntOpt('progress_update_check_interval',
              help='progress update status check interval in seconds',
              default=60),
    cfg.StrOpt('dashboard_url',
              help='dashboard url',
              default=''),
    cfg.StrOpt('dashboard_link_pattern',
              help='dashboard link pattern',
              default=r'(?m)(http://\d+\.\d+\.\d+\.\d+:5000/v2\.0)'),
    cfg.StrOpt('cluster_vip',
              help='cluster ip address',
              default=''),
    cfg.StrOpt('enable_secgroup',
              help='enable security group',
              default='true'),
    cfg.StrOpt('enable_vpnaas',
              help='enable vpn as service',
              default='true'),
    cfg.StrOpt('enable_fwaas',
              help='enable firewall as service',
              default='true'),
    cfg.StrOpt('network_cfg',
              help='netowrk config file',
              default=''),
    cfg.StrOpt('neutron_cfg',
              help='netowrk config file',
              default=''),
    cfg.StrOpt('cluster_pub_vip',
              help='cluster ip address',
              default=''),
    cfg.StrOpt('cluster_prv_vip',
              help='cluster ip address',
              default=''),
    cfg.StrOpt('repo_name',
              help='repo name',
              default=''),
    cfg.StrOpt('deploy_type',
              help='deploy type',
              default='virtual'),
    cfg.StrOpt('deploy_flag',
              help='deploy flag',
              default='deploy'),
    cfg.StrOpt('rsa_file',
              help='ssh rsa key file',
              default=''),
]
CONF.register_cli_opts(opts)

def is_role_unassigned(role):
    return role

def _load_config(config_filename):
    if not config_filename:
        return {}
    with open(config_filename) as config_file:
        content = config_file.read()
        return json.loads(content)


class CompassClient(object):
    def __init__(self):
        LOG.info("xh: compass_server=%s" % CONF.compass_server)
        self.client = Client(CONF.compass_server)
        self.subnet_mapping = {}
        self.role_mapping = {}
        self.host_mapping = {}
        self.host_ips = defaultdict(list)
        self.host_roles = {}

        self.login()

    def is_ok(self, status):
        if status < 300 and status >= 200:
            return True

    def login(self):
        status, resp = self.client.get_token(
            CONF.compass_user_email,
            CONF.compass_user_password
        )

        LOG.info(
            'login status: %s, resp: %s',
            status, resp
        )
        if self.is_ok(status):
            return resp["token"]
        else:
            raise Exception(
                'failed to login %s with user %s',
                CONF.compass_server,
                CONF.compass_user_email
            )

    def get_machines(self):
        status, resp = self.client.list_machines()
        if not self.is_ok(status):
            LOG.error(
                'get all machines status: %s, resp: %s', status, resp)
            raise RuntimeError('failed to get machines')

        machines_to_add = list(set([
            machine for machine in CONF.machines.split(',')
            if machine
        ]))

        machines_db = [str(m["mac"]) for m in resp]
        LOG.info('machines in db: %s\n to add: %s', machines_db, machines_to_add)
        if not set(machines_to_add).issubset(set(machines_db)):
            raise RuntimeError('unidentify machine to add')

        return [m["id"] for m in resp if str(m["mac"]) in machines_to_add]

    def list_clusters(self):
        status, resp = self.client.list_clusters(name=CONF.cluster_name)
        if not self.is_ok(status) or not resp:
            raise RuntimeError('failed to list cluster')

        cluster = resp[0]

        return cluster['id']

    def get_adapter(self):
        """get adapter."""
        status, resp = self.client.list_adapters(name=CONF.adapter_name)
        LOG.info(
            'get all adapters status: %s, resp: %s',
            status, resp
        )

        if not self.is_ok(status) or not resp:
            raise RuntimeError('failed to get adapters')

        os_re = re.compile(CONF.adapter_os_pattern)
        flavor_re = re.compile(CONF.adapter_flavor_pattern)

        adapter_id = None
        os_id = None
        flavor_id = None
        adapter = None

        adapter = resp[0]
        adapter_id = adapter['id']
        for supported_os in adapter['supported_oses']:
            if not os_re or os_re.match(supported_os['name']):
                os_id = supported_os['os_id']
                break

        if 'flavors' in adapter:
            for flavor in adapter['flavors']:
                if not flavor_re or flavor_re.match(flavor['name']):
                    flavor_id = flavor['id']
                    break

        assert(os_id and flavor_id)
        return (adapter_id, os_id, flavor_id)

    def add_subnets(self):
        subnets = [
            subnet for subnet in CONF.subnets.split(',')
            if subnet
        ]

        assert(subnets)

        subnet_mapping = {}
        for subnet in subnets:
            try:
                netaddr.IPNetwork(subnet)
            except:
                raise RuntimeError('subnet %s format is invalid' % subnet)

            status, resp = self.client.add_subnet(subnet)
            LOG.info('add subnet %s status %s response %s',
                         subnet, status, resp)
            if not self.is_ok(status):
                raise RuntimeError('failed to add subnet %s' % subnet)

            subnet_mapping[resp['subnet']] = resp['id']

        self.subnet_mapping = subnet_mapping

    def add_cluster(self, adapter_id, os_id, flavor_id):
        """add a cluster."""
        cluster_name = CONF.cluster_name
        assert(cluster_name)
        status, resp = self.client.add_cluster(
            cluster_name, adapter_id,
            os_id, flavor_id)

        if not self.is_ok(status):
            raise RuntimeError("add cluster failed")

        LOG.info('add cluster %s status: %s resp:%s',
                     cluster_name, status,resp)

        if isinstance(resp, list):
            cluster = resp[0]
        else:
            cluster = resp

        cluster_id = cluster['id']
        flavor = cluster.get('flavor', {})
        roles = flavor.get('roles', [])

        for role in roles:
            if role.get('optional', False):
                self.role_mapping[role['name']] = ROLE_ASSIGNED
            else:
                self.role_mapping[role['name']] = ROLE_UNASSIGNED

        return cluster_id

    def add_cluster_hosts(self, cluster_id, machines):
        hostnames = [
            hostname for hostname in CONF.hostnames.split(',')
            if hostname
        ]

        assert(len(machines) == len(hostnames))

        machines_dict = []
        for machine_id, hostname in zip(machines, hostnames):
            machines_dict.append({
                'machine_id': machine_id,
                'name': hostname
            })

        # add hosts to the cluster.
        status, resp = self.client.add_hosts_to_cluster(
            cluster_id,
            {'machines': machines_dict})

        LOG.info('add machines %s to cluster %s status: %s, resp: %s',
                     machines_dict, cluster_id, status, resp)

        if not self.is_ok(status):
            raise RuntimeError("add host to cluster failed")

        for host in resp['hosts']:
            self.host_mapping[host['hostname']] = host['id']

        assert(len(self.host_mapping) == len(machines))

    def set_cluster_os_config(self, cluster_id):
        """set cluster os config."""
        os_config = {}
        language = CONF.language
        timezone = CONF.timezone
        http_proxy = CONF.http_proxy
        https_proxy = CONF.https_proxy
        local_repo_url = CONF.local_repo_url
        repo_name = CONF.repo_name
        deploy_type = CONF.deploy_type
        if not https_proxy and http_proxy:
            https_proxy = http_proxy

        no_proxy = [
            no_proxy for no_proxy in CONF.no_proxy.split(',')
            if no_proxy
        ]

        compass_server = CONF.compass_server
        if http_proxy:
            for hostname, ips in self.host_ips.items():
                no_proxy.append(hostname)
                no_proxy.extend(ips)

        ntp_server = CONF.ntp_server or compass_server

        dns_servers = [
            dns_server for dns_server in CONF.dns_servers.split(',')
            if dns_server
        ]
        if not dns_servers:
            dns_servers = [compass_server]

        domain = CONF.domain
        if not domain:
            raise Exception('domain is not defined')

        search_path = [
            search_path for search_path in CONF.search_path.split(',')
            if search_path
        ]

        if not search_path:
            search_path = [domain]

        default_gateway = CONF.default_gateway
        if not default_gateway:
            raise Exception('default gateway is not defined')

        general_config = {
            'language': language,
            'timezone': timezone,
            'ntp_server': ntp_server,
            'dns_servers': dns_servers,
            'default_gateway': default_gateway
        }

        if http_proxy:
            general_config['http_proxy'] = http_proxy
        if https_proxy:
            general_config['https_proxy'] = https_proxy
        if no_proxy:
            general_config['no_proxy'] = no_proxy
        if domain:
            general_config['domain'] = domain
        if search_path:
            general_config['search_path'] = search_path
        if local_repo_url:
            general_config['local_repo'] = local_repo_url
        if repo_name:
            general_config['repo_name'] = repo_name
        if deploy_type:
            general_config['deploy_type'] = deploy_type

        os_config["general"] = general_config

        server_credential = CONF.server_credential
        if '=' in server_credential:
            server_username, server_password = server_credential.split('=', 1)
        elif server_credential:
            server_username = server_password = server_credential
        else:
            server_username = 'root'
            server_password = 'root'

        os_config['server_credentials'] = {
            'username': server_username,
            'password': server_password
        }

        partitions = [
            partition for partition in CONF.partitions.split(',')
            if partition
        ]

        partition_config = {}
        for partition in partitions:
            assert("=" in partition)

            partition_name, partition_value = partition.split('=', 1)
            partition_name = partition_name.strip()
            partition_value = partition_value.strip()

            assert(partition_name and partition_value)

            if partition_value.endswith('%'):
                partition_type = 'percentage'
                partition_value = int(partition_value[:-1])
            else:
                partition_type = 'size'

            partition_config[partition_name] = {
                partition_type: partition_value
            }

        os_config['partition'] = partition_config

        """
        os_config_filename = CONF.os_config_json_file
        if os_config_filename:
            util.merge_dict(
                os_config, _load_config(os_config_filename)
            )
        """

        status, resp = self.client.update_cluster_config(
            cluster_id, os_config=os_config)
        LOG.info(
            'set os config %s to cluster %s status: %s, resp: %s',
            os_config, cluster_id, status, resp)
        if not self.is_ok(status):
            raise RuntimeError('failed to set os config %s to cluster %s' \
                    % (os_config, cluster_id))

    def set_host_networking(self):
        """set cluster hosts networking."""
        def get_subnet(ip_str):
            try:
                LOG.info("subnets: %s" % self.subnet_mapping.keys())
                ip = netaddr.IPAddress(ip_str)
                for cidr, subnet_id in self.subnet_mapping.items():
                    subnet = netaddr.IPNetwork(cidr)
                    if ip in subnet:
                        return True, subnet_id

                    LOG.info("ip %s not in %s" % (ip_str, cidr))
                return False, None
            except:
                LOG.exception("ip addr %s is invalid" % ip_str)
                return False, None

        for host_network in CONF.host_networks.split(';'):
            hostname, networks_str = host_network.split(':', 1)
            hostname = hostname.strip()
            networks_str = networks_str.strip()

            assert(hostname in self.host_mapping)

            host_id = self.host_mapping[hostname]
            intf_list = networks_str.split(',')
            for intf_str in intf_list:
                interface, intf_properties = intf_str.split('=', 1)
                intf_properties = intf_properties.strip().split('|')

                assert(intf_properties)
                ip_str = intf_properties[0]

                status, subnet_id = get_subnet(ip_str)
                if not status:
                    raise RuntimeError("ip addr %s is invalid" % ip_str)

                properties = dict([
                    (intf_property, True)
                    for intf_property in intf_properties[1:]
                ])

                LOG.info(
                    'add host %s interface %s ip %s network proprties %s',
                    hostname, interface, ip_str, properties)

                status, response = self.client.add_host_network(
                    host_id, interface, ip=ip_str, subnet_id=subnet_id,
                    **properties
                )

                LOG.info(
                    'add host %s interface %s ip %s network properties %s '
                    'status %s: %s',
                    hostname, interface, ip_str, properties,
                    status, response
                )

                if not self.is_ok(status):
                    raise RuntimeError("add host network failed")

                self.host_ips[hostname].append(ip_str)

    def set_cluster_package_config(self, cluster_id):
        """set cluster package config."""
        package_config = {"security": {}}

        service_credentials = [
            service_credential
            for service_credential in CONF.service_credentials.split(',')
            if service_credential
        ]

        service_credential_cfg = {}
        LOG.info(
            'service credentials: %s', service_credentials
        )

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
            service_credential_cfg[service_name] = {
                'username': username,
                'password': password
            }

        console_credentials = [
            console_credential
            for console_credential in CONF.console_credentials.split(',')
            if console_credential
        ]

        LOG.info(
            'console credentials: %s', console_credentials
        )

        console_credential_cfg = {}
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
            console_credential_cfg[console_name] = {
                'username': username,
                'password': password
            }

        package_config["security"] = {"service_credentials": service_credential_cfg,
                                      "console_credentials": console_credential_cfg}

        network_mapping = dict([
            network_pair.split('=', 1)
            for network_pair in CONF.network_mapping.split(',')
            if '=' in network_pair
        ])

        package_config['network_mapping'] = network_mapping

        assert(os.path.exists(CONF.network_cfg))
        network_cfg = yaml.load(open(CONF.network_cfg))
        package_config["network_cfg"] = network_cfg

        assert(os.path.exists(CONF.neutron_cfg))
        neutron_cfg = yaml.load(open(CONF.neutron_cfg))
        package_config["neutron_config"] = neutron_cfg

        """
        package_config_filename = CONF.package_config_json_file
        if package_config_filename:
            util.merge_dict(
                package_config, _load_config(package_config_filename)
            )
        """
        package_config['ha_proxy'] = {}
        if CONF.cluster_vip:
            package_config["ha_proxy"]["vip"] = CONF.cluster_vip

        package_config['enable_secgroup'] = (CONF.enable_secgroup == "true")
        package_config['enable_fwaas'] = (CONF.enable_fwaas== "true")
        package_config['enable_vpnaas'] = (CONF.enable_vpnaas== "true")

        status, resp = self.client.update_cluster_config(
            cluster_id, package_config=package_config)
        LOG.info(
            'set package config %s to cluster %s status: %s, resp: %s',
            package_config, cluster_id, status, resp)

        if not self.is_ok(status):
            raise RuntimeError("set cluster package_config failed")

    def set_host_roles(self, cluster_id, host_id, roles):
        status, response = self.client.update_cluster_host(
            cluster_id, host_id, roles=roles)

        LOG.info(
            'set cluster %s host %s roles %s status %s: %s',
            cluster_id, host_id, roles, status, response
        )

        if not self.is_ok(status):
            raise RuntimeError("set host roles failed")

        for role in roles:
            if role in self.role_mapping:
                self.role_mapping[role] = ROLE_ASSIGNED

    def set_all_hosts_roles(self, cluster_id):
        for host_str in CONF.host_roles.split(';'):
            host_str = host_str.strip()
            hostname, roles_str = host_str.split('=', 1)

            assert(hostname in self.host_mapping)
            host_id = self.host_mapping[hostname]

            roles = [role.strip() for role in roles_str.split(',') if role]

            self.set_host_roles(cluster_id, host_id, roles)
            self.host_roles[hostname] = roles

        unassigned_hostnames = list(set(self.host_mapping.keys()) \
                                    - set(self.host_roles.keys()))

        unassigned_roles = [ role for role, status in self.role_mapping.items()
                             if is_role_unassigned(status)]

        assert(len(unassigned_hostnames) >= len(unassigned_roles))

        for hostname, role in map(None, unassigned_hostnames, unassigned_roles):
            host_id = self.host_mapping[hostname]
            self.set_host_roles(cluster_id, host_id, [role])
            self.host_roles[hostname] = [role]

        unassigned_hostnames = list(set(self.host_mapping.keys()) \
                                    - set(self.host_roles.keys()))

        if not unassigned_hostnames:
            return

        # assign default roles to unassigned hosts
        default_roles = [
            role for role in CONF.default_roles.split(',')
            if role
        ]

        assert(default_roles)

        cycle_roles = itertools.cycle(default_roles)
        for hostname in unassigned_hostnames:
            host_id = self.host_mapping[hostname]
            roles = [cycle_roles.next()]
            self.set_host_roles(cluster_id, host_id, roles)
            self.host_roles[hostname] = roles

    def deploy_clusters(self, cluster_id):
        host_ids = self.host_mapping.values()

        status, response = self.client.review_cluster(
            cluster_id, review={'hosts': host_ids}
        )
        LOG.info(
            'review cluster %s hosts %s, status %s: %s',
            cluster_id, host_ids, status, response
        )

        #TODO, what this doning?
        if not self.is_ok(status):
            raise RuntimeError("review cluster host failed")

        status, response = self.client.deploy_cluster(
            cluster_id, deploy={'hosts': host_ids}
        )
        LOG.info(
            'deploy cluster %s hosts %s status %s: %s',
            cluster_id, host_ids, status, response
        )

        if not self.is_ok(status):
            raise RuntimeError("deploy cluster failed")

    def redeploy_clusters(self, cluster_id):
        status, response = self.client.redeploy_cluster(
            cluster_id
        )

        if not self.is_ok(status):
            LOG.info(
                'deploy cluster %s status %s: %s',
                cluster_id, status, response
            )
            raise RuntimeError("redeploy cluster failed")

    def get_installing_progress(self, cluster_id):
        def _get_installing_progress():
            """get intalling progress."""
            action_timeout = time.time() + 60 * float(CONF.action_timeout)
            deployment_timeout = time.time() + 60 * float(
                CONF.deployment_timeout)

            current_time = time.time
            while current_time() < deployment_timeout:
                status, cluster_state = self.client.get_cluster_state(cluster_id)
                if not self.is_ok(status):
                    LOG.error("can not get cluster state")

                    # maybe a transient error?
                    time.sleep(5)
                    status, cluster_state = self.client.get_cluster_state(cluster_id)
                    if not self.is_ok(status):
                        # OK, there's something wrong
                        raise RuntimeError("can not get cluster state")

                if cluster_state['state'] in ['UNINITIALIZED', 'INITIALIZED']:
                    if current_time() >= action_timeout:
                        raise RuntimeError("installation timeout")
                    else:
                        time.sleep(5)
                        continue

                elif cluster_state['state'] == 'SUCCESSFUL':
                    LOG.info(
                         'get cluster %s state status %s: %s, successful',
                         cluster_id, status, cluster_state
                    )
                    break
                elif cluster_state['state'] == 'ERROR':
                    raise RuntimeError(
                         'get cluster %s state status %s: %s, error',
                         (cluster_id, status, cluster_state)
                    )
        try:
            _get_installing_progress()
        finally:
            # do this twice, make sure process be killed
            kill_print_proc()
            kill_print_proc()

    def check_dashboard_links(self, cluster_id):
        dashboard_url = CONF.dashboard_url
        if not dashboard_url:
            LOG.info('no dashboarde url set')
            return
        dashboard_link_pattern = re.compile(
            CONF.dashboard_link_pattern)
        r = requests.get(dashboard_url, verify=False)
        r.raise_for_status()
        match = dashboard_link_pattern.search(r.text)
        if match:
            LOG.info(
                'dashboard login page for cluster %s can be downloaded',
                cluster_id)
        else:
            msg = (
                '%s failed to be downloaded\n'
                'the context is:\n%s\n'
            ) % (dashboard_url, r.text)
            raise Exception(msg)


def print_ansible_log():
    os.system("ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i %s root@192.168.200.2 \
              'while ! tail -f /var/ansible/run/openstack_liberty-opnfv2/ansible.log 2>/dev/null; do :; sleep 1; done'" % CONF.rsa_file)

def kill_print_proc():
    os.system("ps aux|grep -v grep|grep -E 'ssh.+root@192.168.200.2'|awk '{print $2}'|xargs kill -9")

def deploy():
    client = CompassClient()
    machines = client.get_machines()

    LOG.info('machines are %s', machines)

    client.add_subnets()
    adapter_id, os_id, flavor_id = client.get_adapter()
    cluster_id = client.add_cluster(adapter_id, os_id, flavor_id)

    client.add_cluster_hosts(cluster_id, machines)
    client.set_host_networking()
    client.set_cluster_os_config(cluster_id)

    if flavor_id:
        client.set_cluster_package_config(cluster_id)

    client.set_all_hosts_roles(cluster_id)
    client.deploy_clusters(cluster_id)

    LOG.info("compass OS installtion is begin")
    threading.Thread(target=print_ansible_log).start()
    client.get_installing_progress(cluster_id)
    client.check_dashboard_links(cluster_id)

def redeploy():
    client = CompassClient()

    cluster_id = client.list_clusters()

    client.redeploy_clusters(cluster_id)

    client.get_installing_progress(cluster_id)
    client.check_dashboard_links(cluster_id)

def main():
    if CONF.deploy_flag == "redeploy":
        redeploy()
    else:
        deploy()


if __name__ == "__main__":
    CONF(args=sys.argv[1:])
    main()
