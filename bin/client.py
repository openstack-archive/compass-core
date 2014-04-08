#!/usr/bin/python
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
import re
import requests
import time

from compass.apiclient.restful import Client
from compass.utils import flags
from compass.utils import logsetting


flags.add('compass_server',
          help='compass server url',
          default='http://127.0.0.1/api')
flags.add('switch_ips',
          help='comma seperated switch ips',
          default='')
flags.add('switch_credential',
          help='comma separated <credential key>=<credential value>',
          default='version=v2c,community=public')
flags.add('switch_max_retries', type='int',
          help='max retries of poll switch',
          default=-1)
flags.add('switch_retry_interval', type='int',
          help='interval to repoll switch',
          default=10)
flags.add_bool('poll_switches',
               help='if the client polls switches',
               default=True)
flags.add('machines',
          help='comma separated mac addresses of machines',
          default='')
flags.add('adapter_os_name',
          help='adapter os name',
          default=r'(?i)centos.*')
flags.add('adapter_target_system',
          help='adapter target system name',
          default='openstack')
flags.add('cluster_name',
          help='cluster name',
          default='cluster1')
flags.add('credentials',
          help=(
              'comma separated credentials formatted as '
              '<credential_name>:<username>=<password>'
          ),
          default=(
              'server:root=root,service:service=service,'
              'console:console=console'
          ))
flags.add('networking',
          help=(
              'semicomma seperated network property and its value '
              '<network_property_name>=<value>'
          ),
          default='')
flags.add('partitions',
          help=(
              'comma seperated partitions '
              '<partition name>:<partition_type>=<partition_value>'
          ),
          default='tmp:percentage=10,var:percentage=20,home:percentage=40')
flags.add('host_roles',
          help=(
              'semicomma separated host roles '
              '<hostname>=<comma separated roles>',
          ),
          default='')
flags.add('deployment_timeout',
          help='deployment timeout in minutes',
          default=60)
flags.add('progress_update_check_interval',
          help='progress update status check interval in seconds',
          default=60)
flags.add('dashboard_role',
          help='dashboard role name',
          default='os-dashboard')
flags.add('dashboard_link_pattern',
          help='dashboard link pattern',
          default=r'(?m)(http://\d+\.\d+\.\d+\.\d+:5000/v2\.0)')


def _get_client():
    """get apiclient object."""
    return Client(flags.OPTIONS.compass_server)


def _get_machines(client):
    """get machines connected to the switch."""
    status, resp = client.get_machines()
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
    for machine in resp['machines']:
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
    status, resp = client.get_switches()
    logging.info('get all switches status: %s resp: %s', status, resp)
    if status >= 400:
        msg = 'failed to get switches'
        raise Exception(msg)

    all_switches = {}
    for switch in resp['switches']:
        all_switches[switch['ip']] = switch

    # add a switch.
    switch_ips = [
        switch_ip for switch_ip in flags.OPTIONS.switch_ips.split(',')
        if switch_ip
    ]
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

            all_switches[switch_ip] = resp['switch']
        else:
            logging.info('switch %s is already added', switch_ip)

    remain_retries = flags.OPTIONS.switch_max_retries
    while True:
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

            switch = resp['switch']
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
        
        if remain_retires > 0:
            for switch_ip, switch in all_switches.items():
                status, resp = client.update_switch(
                    switch_id, switch_ip, **switch_credential)
                if status >= 400:
                    msg = 'failed to update switch %s' % switch_ip
                    raise Exception(msg)

            remain_retries -= 1
        else:
            msg = 'max retries reached'
            raise Exception(msg)


def _get_adapter(client):
    """get adapter."""
    status, resp = client.get_adapters()
    logging.info('get all adapters status: %s, resp: %s', status, resp)
    if status >= 400:
        msg = 'failed to get adapters'
        raise Exception(msg)

    os_name_pattern = flags.OPTIONS.adapter_os_name
    os_name_re = re.compile(os_name_pattern)
    target_system = flags.OPTIONS.adapter_target_system
    adapter_id = None
    for adapter in resp['adapters']:
        if (
            os_name_re.match(adapter['os']) and
            target_system == adapter['target_system']
        ):
            adapter_id = adapter['id']

    if not adapter_id:
        msg = 'no adapter found for %s and %s' % (
            os_name_pattern, target_system)
        raise Exception(msg)

    logging.info('adpater for deploying a cluster: %s', adapter_id)
    return adapter_id


def _add_cluster(client, adapter_id, machines):
    """add a cluster."""
    cluster_name = flags.OPTIONS.cluster_name
    status, resp = client.add_cluster(
        cluster_name=cluster_name, adapter_id=adapter_id)
    logging.info('add cluster %s status: %s, resp: %s',
                 cluster_name, status, resp)
    if status >= 400:
        msg = 'failed to add cluster %s with adapter %s' % (
            cluster_name, adapter_id)
        raise Exception(msg)

    cluster = resp['cluster']
    cluster_id = cluster['id']

    # add hosts to the cluster.
    status, resp = client.add_hosts(
        cluster_id=cluster_id,
        machine_ids=machines.keys())
    logging.info('add hosts to cluster %s status: %s, resp: %s',
                 cluster_id, status, resp)
    if status >= 400:
        msg = 'failed to add machines %s to cluster %s' % (
            machines, cluster_name)
        raise Exception(msg)

    host_ids = []
    for host in resp['cluster_hosts']:
        host_ids.append(host['id'])

    logging.info('added hosts in cluster %s: %s', cluster_id, host_ids)
    if len(host_ids) != len(machines):
        msg = 'machines %s to add to the cluster %s while hosts %s' % (
            machines, cluster_name, host_ids)
        raise Exception(msg)

    return {cluster_id: host_ids}


def _set_cluster_security(client, cluster_hosts):
    """set cluster security."""
    credentials = [
        credential for credential in flags.OPTIONS.credentials.split(',')
        if ':' in credential
    ]
    logging.info('set cluster security: %s', credentials)
    credential_mapping = {}
    for credential in credentials:
        credential_name, username_and_password = credential.split(':', 1)
        if not credential_name:
            raise Exception('there is no credential name in %s' % credential)

        if not username_and_password:
            raise Exception('there is no username/password in %s' % credential)

        if '=' not in username_and_password:
            raise Exception('there is no = in %s' % username_and_password)

        username, password = username_and_password.split('=', 1)
        if not username or not password:
            raise Exception(
                'there is no username or password in %s' % (
                    username_and_password))

        credential_mapping['%s_username' % credential_name] = username
        credential_mapping['%s_password' % credential_name] = password

    for cluster_id, host_ids in cluster_hosts.items():
        status, resp = client.set_security(
            cluster_id, **credential_mapping)
        logging.info(
            'set security config to cluster %s status: %s, resp: %s',
            cluster_id, status, resp)
        if status >= 400:
            msg = 'failed to set security %s for cluster %s' % (
                credential_mapping, cluster_id)
            raise Exception(msg)


def _set_cluster_networking(client, cluster_hosts):
    """set cluster networking."""
    networking_map = {}
    networkings = [
        network for network in flags.OPTIONS.networking.split(';')
        if '=' in network
    ]
    logging.info('set cluster networking: %s', networkings)
    for networking in networkings:
        networking_name, networking_value = networking.split('=', 1)
        if not networking_name:
            raise Exception(
                'there is no networking name in %s' % networking)

        if networking_name.endswith('_promisc'):
            networking_map[networking_name] = int(networking_value)
        else:
            networking_map[networking_name] = networking_value

    for cluster_id, host_ids in cluster_hosts.items():
        status, resp = client.set_networking(
            cluster_id, **networking_map)
        logging.info(
            'set networking config %s to cluster %s status: %s, resp: %s',
            networking_map, cluster_id, status, resp)
        if status >= 400:
            msg = 'failed to set networking config %s to cluster %s' % (
                networking_map, cluster_id)
            raise Exception(msg)


def _set_cluster_partition(client, cluster_hosts):
    """set partiton of each host in cluster."""
    partitions = [
        partition for partition in flags.OPTIONS.partitions.split(',')
        if ':' in partition
    ]
    logging.info('set cluster partition: %s', partitions)
    partiton_mapping = {}
    for partition in partitions:
        partition_name, partition_pair = partition.split(':', 1)
        if not partition_name:
            raise Exception(
                'there is no partition name in %s' % partition)

        if not partition_pair:
            raise Exception(
                'there is no partition pair in %s' % partition)

        if '=' not in partition_pair:
            raise Exception(
                'there is no = in %s' % partition_pair)

        partition_type, partition_value = partition_pair.split('=', 1)
        if partition_type == 'percentage':
            partition_value = int(partition_value)
        elif partition_type == 'mbytes':
            partition_value = int(partition_value)
        else:
            raise Exception(
                'unsupported partition type %s' % partition_type)

        partiton_mapping[
            '%s_%s' % (partition_name, partition_type)
        ] = partition_value

    for cluster_id, host_ids in cluster_hosts.items():
        status, resp = client.set_partition(
            cluster_id, **partiton_mapping)
        logging.info(
            'set partition config %s to cluster %s status: %s, resp: %s',
            partiton_mapping, cluster_id, status, resp)
        if status >= 400:
            msg = 'failed to set partition %s to cluster %s' % (
                partiton_mapping, cluster_id)
            raise Exception(msg)


def _set_host_config(client, cluster_hosts):
    host_configs = []
    for host in flags.OPTIONS.host_roles.split(';'):
        if not host:
            continue

        hostname, roles = host.split('=', 1)
        if hostname:
            roles = [role for role in roles.split(',') if role]

        host_configs.append({
            'hostname': hostname,
            'roles': roles
        })

    total_hosts = 0
    for cluster_id, host_ids in cluster_hosts.items():
        total_hosts += len(host_ids)

    if total_hosts != len(host_configs):
        msg = '%s host to assign but got %s host configs' % (
            total_hosts, len(host_configs))
        raise Exception(msg)

    for cluster_id, host_ids in cluster_hosts.items():
        for hostid in host_ids:
            host_config = host_configs.pop(0)
            status, resp = client.update_host_config(
                hostid, **host_config)
            logging.info(
                'set host %s config %s status: %s, resp: %s',
                hostid, host_config, status, resp
            )
            if status >= 400:
                msg = 'failed to set host %s config %s' % (
                    hostid, host_config)
                raise Exception(msg)


def _deploy_clusters(client, cluster_hosts):
    """deploy cluster."""
    for cluster_id, host_ids in cluster_hosts.items():
        status, resp = client.deploy_hosts(cluster_id)
        logging.info(
            'deploy cluster %s status: %s, resp: %s',
            cluster_id, status, resp)
        if status >= 400:
            msg = 'failed to deploy cluster %s' % cluster_id
            raise Exception(msg)


def _get_installing_progress(client, cluster_hosts):
    """get intalling progress."""
    timeout = time.time() + 60 * float(flags.OPTIONS.deployment_timeout)
    clusters_progress = {}
    hosts_progress = {}
    install_finished = False
    failed_hosts = {}
    failed_clusters = {}
    while time.time() < timeout:
        found_installing_clusters = False
        found_installing_hosts = False
        for cluster_id, host_ids in cluster_hosts.items():
            for hostid in host_ids:
                if hostid in hosts_progress:
                    continue

                status, resp = client.get_host_installing_progress(hostid)
                logging.info(
                    'get host %s installing progress status: %s, resp: %s',
                    hostid, status, resp)
                if status >= 400:
                    msg = 'failed to get host %s progress' % hostid
                    raise Exception(msg)

                progress = resp['progress']
                if (
                    progress['state'] not in ['UNINITIALIZED', 'INSTALLING'] or
                    progress['percentage'] >= 1.0
                ):
                    hosts_progress[hostid] = progress
                    if progress['state'] in ['ERROR']:
                        failed_hosts[hostid] = progress

                else:
                    found_installing_hosts = True

            if cluster_id in clusters_progress:
                continue

            status, resp = client.get_cluster_installing_progress(cluster_id)
            logging.info(
                'get cluster %s installing progress status: %s, resp: %s',
                cluster_id, status, resp)
            if status >= 400:
                msg = 'failed to get cluster %s intsalling progress' % (
                    cluster_id)
                raise Exception(msg)

            progress = resp['progress']
            if (
                progress['state'] not in ['UNINITIALIZED', 'INSTALLING'] or
                progress['percentage'] >= 1.0
            ):
                clusters_progress[cluster_id] = progress
                if progress['state'] in ['ERROR']:
                    failed_clusters[cluster_id] = progress

            else:
                found_installing_clusters = True

        if found_installing_clusters and found_installing_hosts:
            logging.info(
                'there are some clusters/hosts in installing.'
                'sleep %s seconds and retry',
                flags.OPTIONS.progress_update_check_interval)
            time.sleep(float(flags.OPTIONS.progress_update_check_interval))
        else:
            install_finished = True
            logging.info('all clusters/hosts are installed.')
            break

    if not install_finished:
        msg = 'installing %s is not all finished: hosts %s clusters %s' % (
            cluster_hosts, hosts_progress, clusters_progress)
        raise Exception(msg)

    if failed_hosts:
        msg = 'installing hosts failed: %s' % failed_hosts
        raise Exception(msg)

    if failed_clusters:
        msg = 'installing clusters failed: %s' % failed_clusters
        raise Exception(msg)


def _check_dashboard_links(client, cluster_hosts):
    dashboard_role = flags.OPTIONS.dashboard_role
    dashboard_link_pattern = re.compile(
        flags.OPTIONS.dashboard_link_pattern)
    for cluster_id, host_ids in cluster_hosts.items():
        status, resp = client.get_dashboard_links(cluster_id)
        logging.info(
            'get cluster %s dashboard links status: %s, resp: %s',
            cluster_id, status, resp)
        if status >= 400:
            msg = 'failed to get cluster %s dashboard links' % cluster_id
            raise Exception(msg)

        dashboardlinks = resp['dashboardlinks']
        if dashboard_role not in dashboardlinks:
            msg = 'no dashboard role %s found in %s' % (
                dashboard_role, dashboardlinks)
            raise Exception(msg)

        r = requests.get(dashboardlinks[dashboard_role], verify=False)
        r.raise_for_status()
        match = dashboard_link_pattern.search(r.text)
        if match:
            logging.info(
                'dashboard login page for cluster %s can be downloaded',
                cluster_id)
        else:
            msg = (
                '%s dashboard login page failed to be downloaded\n'
                'the context is:\n%s\n'
            ) % (dashboard_role, r.text)
            raise Exception(msg)


import sys

def main():
    flags.init()
    logsetting.init()
    client = _get_client()
    if flags.OPTIONS.poll_switches:
        machines = _poll_switches(client)
    else:
        machines = _get_machines(client)

    adapter_id = _get_adapter(client)
    cluster_hosts = _add_cluster(client, adapter_id, machines)
    _set_cluster_security(client, cluster_hosts)
    _set_cluster_networking(client, cluster_hosts)
    _set_cluster_partition(client, cluster_hosts)
    _set_host_config(client, cluster_hosts)
    _deploy_clusters(client, cluster_hosts)
    _get_installing_progress(client, cluster_hosts)
    _check_dashboard_links(client, cluster_hosts)


if __name__ == "__main__":
    main()
