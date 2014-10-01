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


import datetime
import logging
import os
import sys
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from base import BaseTest
from compass.db.api import adapter as adapter_api
from compass.db.api import adapter_holder as adapter
from compass.db.api import cluster
from compass.db.api import database
from compass.db.api import host
from compass.db.api import machine
from compass.db.api import metadata as metadata_api
from compass.db.api import metadata_holder as metadata
from compass.db.api import network
from compass.db.api import switch
from compass.db.api import user as user_api
from compass.db import exception
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import util


class HostTestCase(unittest2.TestCase):
    """Host case test case."""

    def setUp(self):
        super(HostTestCase, self).setUp()
        reload(setting)
        setting.CONFIG_DIR = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'data'
        )
        database.init('sqlite://')
        database.create_db()
        adapter.load_adapters()
        metadata.load_metadatas()

        self.user_object = (
            user_api.get_user_object(
                setting.COMPASS_ADMIN_EMAIL
            )
        )
        # get adapter information
        list_adapters = adapter.list_adapters(self.user_object)
        for list_adapter in list_adapters:
            for supported_os in list_adapter['supported_oses']:
                self.os_id = supported_os['os_id']
                break
            if list_adapter['flavors']:
                details = list_adapter['flavors']
                for detail in details:
                    if detail['display_name'] == 'allinone':
                        roles = detail['roles']
                        for role in roles:
                            self.adapter_id = role['adapter_id']
                            self.flavor_id = role['flavor_id']
                            break

        # add cluster
        cluster_names = ['test_cluster1', 'test_cluster2']
        for cluster_name in cluster_names:
            cluster.add_cluster(
                self.user_object,
                adapter_id=self.adapter_id,
                os_id=self.os_id,
                flavor_id=self.flavor_id,
                name=cluster_name
            )
        clusters = cluster.list_clusters(self.user_object)
        self.roles = None
        for list_cluster in clusters:
            for item in list_cluster['flavor']['roles']:
                self.roles = item
            if list_cluster['name'] == 'test_cluster1':
                self.cluster_id = list_cluster['id']
                break
        # add switch
        switch.add_switch(
            self.user_object,
            ip='172.29.8.40'
        )
        switches = switch.list_switches(self.user_object)
        self.switch_id = None
        for item in switches:
            self.switch_id = item['id']
        macs = ['28:6e:d4:46:c4:25', '00:0c:29:bf:eb:1d']
        for mac in macs:
            switch.add_switch_machine(
                self.user_object,
                self.switch_id,
                mac=mac,
                port='1'
            )
        # get machine information
        machines = machine.list_machines(self.user_object)
        self.machine_ids = []
        for item in machines:
            self.machine_ids.append(item['id'])
        # add cluster host
        name = ['newname1', 'newname2']
        for i in range(0, 2):
            cluster.add_cluster_host(
                self.user_object,
                self.cluster_id,
                machine_id=self.machine_ids[i],
                name=name[i]
            )
        self.host_ids = []
        clusterhosts = cluster.list_clusterhosts(self.user_object)
        for clusterhost in clusterhosts:
            self.host_ids.append(clusterhost['host_id'])
        # add subnet
        subnets = ['10.145.88.0/23', '192.168.100.0/23']
        for subnet in subnets:
            network.add_subnet(
                self.user_object,
                subnet=subnet
            )
        list_subnet = network.list_subnets(
            self.user_object
        )
        self.subnet_ids = []
        for item in list_subnet:
            self.subnet_ids.append(item['id'])
        # add host network
        host.add_host_network(
            self.user_object,
            self.host_ids[0],
            interface='eth0',
            ip='10.145.88.0',
            subnet_id=self.subnet_ids[0],
            is_mgmt=True
        )
        host.add_host_network(
            self.user_object,
            self.host_ids[1],
            interface='eth1',
            ip='192.168.100.0',
            subnet_id=self.subnet_ids[1],
            is_promiscuous=True
        )
        # add log history
        filenames = ['log1', 'log2']
        for filename in filenames:
            host.add_host_log_history(
                self.user_object,
                self.host_ids[0],
                filename=filename
            )

        self.os_configs = {
            'general': {
                'language': 'EN',
                'timezone': 'UTC',
                'http_proxy': 'http://127.0.0.1:3128',
                'https_proxy': 'http://127.0.0.1:3128',
                'no_proxy': [
                    '127.0.0.1',
                    'compass'
                ],
                'ntp_server': '127.0.0.1',
                'dns_servers': [
                    '127.0.0.1'
                ],
                'domain': 'ods.com',
                'search_path': [
                    'ods.com'
                ],
                'default_gateway': '127.0.0.1',
            },
            'server_credentials': {
                'username': 'root',
                'password': 'root',
            },
            'partition': {
                '/var': {
                    'max_size': '100G',
                    'percentage': 10,
                    'size': '1G'
                }
            }
        }
        self.package_configs = {
            'security': {
                'service_credentials': {
                    '$service': {
                        'username': 'root',
                        'password': 'root'
                    }
                },
                'console_credentials': {
                    '$console': {
                        'username': 'root',
                        'password': 'root'
                    }
                }
            },
            'network_mapping': {
                '$interface_type': 'eth0'
            }
        }


class TestListHosts(HostTestCase):
    """Test list hosts."""

    def setUp(self):
        super(TestListHosts, self).setUp()

    def tearDown(self):
        super(TestListHosts, self).tearDown()

    def test_list_hosts(self):
        list_hosts = host.list_hosts(
            self.user_object
        )
        result = []
        for list_host in list_hosts:
            result.append(list_host['name'])
        for item in result:
            self.assertIn(item, ['newname1', 'newname2'])


class TestListMachinesOrHosts(HostTestCase):
    """Test list machines or hosts."""

    def setUp(self):
        super(TestListMachinesOrHosts, self).setUp()

    def tearDown(self):
        super(TestListMachinesOrHosts, self).tearDown()

    def test_list__hosts(self):
        list_hosts = host.list_machines_or_hosts(
            self.user_object
        )
        result = []
        for list_host in list_hosts:
            result.append(list_host['name'])
        for item in result:
            self.assertIn(item, ['newname1', 'newname2'])

    def test_list_machines(self):
        host.del_host(
            self.user_object,
            self.host_ids[0]
        )
        host.del_host(
            self.user_object,
            self.host_ids[1]
        )
        list_hosts = host.list_machines_or_hosts(
            self.user_object
        )
        macs = []
        names = []
        for list_host in list_hosts:
            for k, v in list_host.iteritems():
                if k == 'mac':
                    macs.append(v)
                if k == 'name':
                    names.append(v)
        for mac in macs:
            self.assertIn(mac, ['28:6e:d4:46:c4:25', '00:0c:29:bf:eb:1d'])
        self.assertEqual(names, [])


class TestGetHost(HostTestCase):
    """Test get host."""

    def setUp(self):
        super(TestGetHost, self).setUp()

    def tearDown(self):
        super(TestGetHost, self).tearDown()

    def test_get_host(self):
        get_host = host.get_host(
            self.user_object,
            self.host_ids[0]
        )
        self.assertIsNotNone(get_host)
        self.assertEqual(get_host['mac'], '28:6e:d4:46:c4:25')


class TestGetMachineOrHost(HostTestCase):
    """Test get machine or host."""

    def setUp(self):
        super(TestGetMachineOrHost, self).setUp()

    def tearDown(self):
        super(TestGetMachineOrHost, self).tearDown()

    def test_get_host(self):
        get_host = host.get_machine_or_host(
            self.user_object,
            self.host_ids[0]
        )
        self.assertIsNotNone(get_host)
        self.assertEqual(get_host['mac'], '28:6e:d4:46:c4:25')

    def test_get_machine(self):
        host.del_host(
            self.user_object,
            self.host_ids[0]
        )
        get_machine = host.get_machine_or_host(
            self.user_object,
            self.host_ids[0]
        )
        name = []
        for k, v in get_machine.items():
            if k == 'name':
                name.append(v)
        self.assertEqual(name, [])
        self.assertEqual(get_machine['mac'], '28:6e:d4:46:c4:25')


class TestGetHostClusters(HostTestCase):
    """Test get host clusters."""

    def setUp(self):
        super(TestGetHostClusters, self).setUp()

    def tearDown(self):
        super(TestGetHostClusters, self).tearDown()

    def test_get_host_clusters(self):
        host_clusters = host.get_host_clusters(
            self.user_object,
            self.host_ids[0]
        )
        name = None
        for item in host_clusters:
            name = item['name']
        self.assertEqual(name, 'test_cluster1')


class TestUpdateHost(HostTestCase):
    """Test update host."""

    def setUp(self):
        super(TestUpdateHost, self).setUp()

    def tearDown(self):
        super(TestUpdateHost, self).tearDown()

    def test_update_host(self):
        host.update_host(
            self.user_object,
            self.host_ids[0],
            name='update_test_name'
        )
        update_host = host.get_host(
            self.user_object,
            self.host_ids[0]
        )
        self.assertEqual(update_host['name'], 'update_test_name')

    def test_is_host_etitable(self):
        host.update_host_state(
            self.user_object,
            self.host_ids[0],
            state='INSTALLING'
        )
        self.assertRaises(
            exception.Forbidden,
            host.update_host,
            self.user_object,
            self.host_ids[0],
            name='invalid'
        )

    def test_invalid_parameter(self):
        self.assertRaises(
            exception.InvalidParameter,
            host.update_host,
            self.user_object,
            self.host_ids[1],
            name='newname1'
        )


class TestUpdateHosts(HostTestCase):
    """Test update hosts."""

    def setUp(self):
        super(TestUpdateHosts, self).setUp()

    def tearDown(self):
        super(TestUpdateHosts, self).tearDown()

    def test_update_hosts(self):
        update_hosts = host.update_hosts(
            self.user_object,
            data=[
                {
                    'host_id': self.host_ids[0],
                    'name': 'test_update1'
                },
                {
                    'host_id': self.host_ids[1],
                    'name': 'test_update2'
                }
            ]
        )
        results = []
        for update_host in update_hosts:
            results.append(update_host['name'])
        for result in results:
            self.assertIn(result, ['test_update1', 'test_update2'])


class TestDelHost(HostTestCase):
    """Test delete host."""

    def setUp(self):
        super(TestDelHost, self).setUp()

    def tearDown(self):
        super(TestDelHost, self).tearDown()

    def test_del_host(self):
        host.del_host(
            self.user_object,
            self.host_ids[0]
        )
        del_host = host.list_hosts(
            self.user_object
        )
        ids = []
        for item in del_host:
            ids.append(item['id'])
        self.assertNotIn(self.host_ids[0], ids)

    def test_is_host_editable(self):
        host.update_host_state(
            self.user_object,
            self.host_ids[0],
            state='INSTALLING'
        )
        self.assertRaises(
            exception.Forbidden,
            host.del_host,
            self.user_object,
            self.host_ids[0]
        )


class TestGetHostConfig(HostTestCase):
    """Test get host config."""

    def setUp(self):
        super(TestGetHostConfig, self).setUp()
        host.update_host_config(
            self.user_object,
            self.host_ids[0],
            os_config=self.os_configs
        )

    def tearDown(self):
        super(TestGetHostConfig, self).tearDown()

    def test_get_host_config(self):
        os_configs = host.get_host_config(
            self.user_object,
            self.host_ids[0]
        )
        self.assertItemsEqual(self.os_configs, os_configs['os_config'])


class TestGetHostDeployedConfig(HostTestCase):
    """Test get host deployed config."""

    def setUp(self):
        super(TestGetHostDeployedConfig, self).setUp()
        host.update_host_config(
            self.user_object,
            self.host_ids[0],
            os_config=self.os_configs
        )
        cluster.update_cluster_config(
            self.user_object,
            self.cluster_id,
            os_config=self.os_configs,
            package_config=self.package_configs
        )
        cluster.update_cluster_host(
            self.user_object,
            self.cluster_id,
            self.host_ids[0],
            roles=['allinone-compute']
        )
        cluster.review_cluster(
            self.user_object,
            self.cluster_id,
            review={
                'hosts': [self.host_ids[0]]
            }
        )
        host.update_host_deployed_config(
            self.user_object,
            self.host_ids[0],
            os_config=self.os_configs
        )

    def tearDown(self):
        super(TestGetHostDeployedConfig, self).tearDown()

    def test_get_host_deployed_config(self):
        os_configs = host.get_host_deployed_config(
            self.user_object,
            self.host_ids[0]
        )
        self.assertItemsEqual(
            os_configs['deployed_os_config'],
            self.os_configs
        )


class TestUpdateHostDeployedConfig(HostTestCase):
    """Test update host deployed config."""

    def setUp(self):
        super(TestUpdateHostDeployedConfig, self).setUp()
        host.update_host_config(
            self.user_object,
            self.host_ids[0],
            os_config=self.os_configs
        )
        cluster.update_cluster_config(
            self.user_object,
            self.cluster_id,
            os_config=self.os_configs,
            package_config=self.package_configs
        )
        cluster.update_cluster_host(
            self.user_object,
            self.cluster_id,
            self.host_ids[0],
            roles=['allinone-compute']
        )
        cluster.review_cluster(
            self.user_object,
            self.cluster_id,
            review={
                'hosts': [self.host_ids[0]]
            }
        )

    def tearDown(self):
        super(TestUpdateHostDeployedConfig, self).tearDown()

    def test_update_host_deployed_config(self):
        host.update_host_deployed_config(
            self.user_object,
            self.host_ids[0],
            os_config=self.os_configs
        )
        os_configs = host.get_host_deployed_config(
            self.user_object,
            self.host_ids[0]
        )
        self.assertItemsEqual(
            os_configs['deployed_os_config'],
            self.os_configs
        )

    def test_is_host_editable(self):
        host.update_host_state(
            self.user_object,
            self.host_ids[0],
            state='INSTALLING'
        )
        self.assertRaises(
            exception.Forbidden,
            host.update_host_deployed_config,
            self.user_object,
            self.host_ids[0],
            os_config=self.os_configs
        )


class TestUpdateHostConfig(HostTestCase):
    """Test update host config."""

    def setUp(self):
        super(TestUpdateHostConfig, self).setUp()

    def tearDown(self):
        super(TestUpdateHostConfig, self).tearDown()

    def test_update_host_config(self):
        host.update_host_config(
            self.user_object,
            self.host_ids[0],
            os_config=self.os_configs
        )
        os_configs = host.get_host_config(
            self.user_object,
            self.host_ids[0]
        )
        self.assertItemsEqual(self.os_configs, os_configs['os_config'])

    def test_is_host_editable(self):
        host.update_host_state(
            self.user_object,
            self.host_ids[0],
            state='INSTALLING'
        )
        self.assertRaises(
            exception.Forbidden,
            host.update_host_config,
            self.user_object,
            self.host_ids[0],
            os_config=self.os_configs
        )


class TestPatchHostConfig(HostTestCase):
    """Test patch host config."""

    def setUp(self):
        super(TestPatchHostConfig, self).setUp()

    def tearDown(self):
        super(TestPatchHostConfig, self).tearDown()

    def test_patch_host_config(self):
        host.patch_host_config(
            self.user_object,
            self.host_ids[0],
            os_config=self.os_configs
        )
        os_configs = host.get_host_config(
            self.user_object,
            self.host_ids[0]
        )
        self.assertItemsEqual(self.os_configs, os_configs['os_config'])

    def test_is_host_editable(self):
        host.update_host_state(
            self.user_object,
            self.host_ids[0],
            state='INSTALLING'
        )
        self.assertRaises(
            exception.Forbidden,
            host.patch_host_config,
            self.user_object,
            self.host_ids[0],
            os_config=self.os_configs
        )


class TestDelHostConfig(HostTestCase):
    """Test delete host config."""

    def setUp(self):
        super(TestDelHostConfig, self).setUp()
        host.update_host_config(
            self.user_object,
            self.host_ids[0],
            os_config=self.os_configs
        )

    def tearDown(self):
        super(TestDelHostConfig, self).tearDown()

    def test_del_host_config(self):
        host.del_host_config(
            self.user_object,
            self.host_ids[0]
        )
        os_configs = host.get_host_config(
            self.user_object,
            self.host_ids[0]
        )
        self.assertEqual(os_configs['os_config'], {})

    def test_is_host_editable(self):
        host.update_host_state(
            self.user_object,
            self.host_ids[0],
            state='INSTALLING'
        )
        self.assertRaises(
            exception.Forbidden,
            host.del_host_config,
            self.user_object,
            self.host_ids[0]
        )


class TestListHostNetworks(HostTestCase):
    """Test list host networks."""

    def setUp(self):
        super(TestListHostNetworks, self).setUp()
        host.add_host_network(
            self.user_object,
            self.host_ids[0],
            interface='eth1',
            ip='10.145.88.10',
            subnet_id=self.subnet_ids[0],
            is_promiscuous=True
        )

    def tearDown(self):
        super(TestListHostNetworks, self).tearDown()

    def test_list_host_networs(self):
        host_networks = host.list_host_networks(
            self.user_object,
            self.host_ids[0]
        )
        results = []
        for host_network in host_networks:
            results.append(host_network['ip'])
        for result in results:
            self.assertIn(result, ['10.145.88.10', '10.145.88.0'])


class TestListHostnetworks(HostTestCase):
    """Test list hostnetworks."""

    def setUp(self):
        super(TestListHostnetworks, self).setUp()

    def tearDown(self):
        super(TestListHostnetworks, self).tearDown()

    def test_list_hostnetworks(self):
        host_networks = host.list_hostnetworks(
            self.user_object,
        )
        results = []
        for host_network in host_networks:
            results.append(host_network['ip'])
        for result in results:
            self.assertIn(result, ['10.145.88.0', '192.168.100.0'])


class TestGetHostNetwork(HostTestCase):
    """Test get host network."""

    def setUp(self):
        super(TestGetHostNetwork, self).setUp()

    def tearDown(self):
        super(TestGetHostNetwork, self).tearDown()

    def test_get_host_network(self):
        host_network = host.get_host_network(
            self.user_object,
            self.host_ids[0],
            self.host_ids[0]
        )
        self.assertEqual(host_network['ip'], '10.145.88.0')

    def test_record_not_exists(self):
        self.assertRaises(
            exception.RecordNotExists,
            host.get_host_network,
            self.user_object,
            2,
            self.host_ids[0]
        )


class TestGetHostnetwork(HostTestCase):
    """Test get hostnetwork."""

    def setUp(self):
        super(TestGetHostnetwork, self).setUp()

    def tearDown(self):
        super(TestGetHostnetwork, self).tearDown()

    def test_get_hostnetwork(self):
        host_network = host.get_hostnetwork(
            self.user_object,
            self.host_ids[0]
        )
        self.assertEqual(host_network['ip'], '10.145.88.0')


class TestAddHostNetwork(HostTestCase):
    """Test add host network."""

    def setUp(self):
        super(TestAddHostNetwork, self).setUp()

    def tearDown(self):
        super(TestAddHostNetwork, self).tearDown()

    def test_add_host_network(self):
        host.add_host_network(
            self.user_object,
            self.host_ids[0],
            interface='eth1',
            ip='10.145.88.20',
            subnet_id=self.subnet_ids[0],
            is_mgmt=True
        )
        host_network = host.list_host_networks(
            self.user_object,
            self.host_ids[0]
        )
        result = []
        for item in host_network:
            result.append(item['ip'])
        self.assertIn('10.145.88.20', result)

    def test_invalid_parameter(self):
        self.assertRaises(
            exception.InvalidParameter,
            host.add_host_network,
            self.user_object,
            self.host_ids[0],
            interface='eth3',
            ip='10.145.88.0',
            subnet_id=self.subnet_ids[0]
        )


class TestAddHostNetworks(HostTestCase):
    """Test add host networks."""

    def setUp(self):
        super(TestAddHostNetworks, self).setUp()

    def tearDown(self):
        super(TestAddHostNetworks, self).tearDown()

    def test_addhost_networks(self):
        host_networks = host.add_host_networks(
            self.user_object,
            data=[
                {
                    'host_id': self.host_ids[0],
                    'networks': [
                        {
                            'interface': 'eth2',
                            'ip': '10.145.88.20',
                            'subnet_id': self.subnet_ids[0],
                            'is_mgmt': True
                        },
                        {
                            'interface': 'eth3',
                            'ip': '10.145.88.0',
                            'subnet_id': self.subnet_ids[0],
                            'is_mgmt': True
                        }
                    ]
                }
            ]
        )
        ip = []
        for host_network in host_networks['hosts']:
            for item in host_network['networks']:
                ip.append(item['ip'])
        fail_ip = []
        for fail_host in host_networks['failed_hosts']:
            for item in fail_host['networks']:
                fail_ip.append(item['ip'])
        self.assertIn('10.145.88.20', ip)
        self.assertIn('10.145.88.0', fail_ip)


class TestUpdateHostNetwork(HostTestCase):
    """Test update host network."""

    def setUp(self):
        super(TestUpdateHostNetwork, self).setUp()

    def tearDown(self):
        super(TestUpdateHostNetwork, self).tearDown()

    def test_update_host_network(self):
        host.update_host_network(
            self.user_object,
            self.host_ids[0],
            self.host_ids[0],
            interface='eth10',
            ip='10.145.88.100'
        )
        host_networks = host.list_host_networks(
            self.user_object,
            self.host_ids[0]
        )
        interface = None
        ip = None
        for host_network in host_networks:
            interface = host_network['interface']
            ip = host_network['ip']
        self.assertEqual(interface, 'eth10')
        self.assertEqual(ip, '10.145.88.100')

    def test_record_not_exists(self):
        self.assertRaises(
            exception.RecordNotExists,
            host.update_host_network,
            self.user_object,
            self.host_ids[0],
            2
        )


class TestUpdateHostnetwork(HostTestCase):
    """Test update hostnetwork."""

    def setUp(self):
        super(TestUpdateHostnetwork, self).setUp()

    def tearDown(self):
        super(TestUpdateHostnetwork, self).tearDown()

    def test_update_hostnetwork(self):
        host.update_hostnetwork(
            self.user_object,
            self.host_ids[0],
            interface='eth10',
            ip='10.145.88.100'
        )
        host_networks = host.list_host_networks(
            self.user_object,
            self.host_ids[0]
        )
        interface = None
        ip = None
        for host_network in host_networks:
            interface = host_network['interface']
            ip = host_network['ip']
        self.assertEqual(interface, 'eth10')
        self.assertEqual(ip, '10.145.88.100')

    def test_invalid_parameter(self):
        host.add_host_network(
            self.user_object,
            self.host_ids[0],
            interface='eth11',
            ip='10.145.88.101',
            subnet_id=self.subnet_ids[0],
            is_promiscuous=True
        )
        self.assertRaises(
            exception.InvalidParameter,
            host.update_hostnetwork,
            self.user_object,
            self.host_ids[0],
            interface='eth11'
        )
        self.assertRaises(
            exception.InvalidParameter,
            host.update_hostnetwork,
            self.user_object,
            self.host_ids[0],
            ip='10.145.88.101'
        )


class TestDelHostNetwork(HostTestCase):
    """Test delete host network."""

    def setUp(self):
        super(TestDelHostNetwork, self).setUp()

    def tearDown(self):
        super(TestDelHostNetwork, self).tearDown()

    def test_del_host_network(self):
        host.del_host_network(
            self.user_object,
            self.host_ids[0],
            self.host_ids[0]
        )
        host_network = host.list_host_networks(
            self.user_object,
            self.host_ids[0]
        )
        self.assertEqual(host_network, [])

    def test_record_not_exists(self):
        self.assertRaises(
            exception.RecordNotExists,
            host.del_host_network,
            self.user_object,
            100,
            self.host_ids[0]
        )


class TestDelHostnetwork(HostTestCase):
    """Test delete hostnetwork."""

    def setUp(self):
        super(TestDelHostnetwork, self).setUp()

    def tearDown(self):
        super(TestDelHostnetwork, self).tearDown()

    def test_del_hostnetwork(self):
        host.del_hostnetwork(
            self.user_object,
            self.host_ids[0]
        )
        host_network = host.list_host_networks(
            self.user_object,
            self.host_ids[0]
        )
        self.assertEqual(host_network, [])


class TestGetHostState(HostTestCase):
    """Test get host state."""

    def setUp(self):
        super(TestGetHostState, self).setUp()

    def tearDown(self):
        super(TestGetHostState, self).tearDown()

    def test_get_host_state(self):
        host_states = host.get_host_state(
            self.user_object,
            self.host_ids[0]
        )
        self.assertEqual(host_states['state'], 'UNINITIALIZED')


class TestUpdateHostState(HostTestCase):
    """Test update host state."""

    def setUp(self):
        super(TestUpdateHostState, self).setUp()

    def tearDown(self):
        super(TestUpdateHostState, self).tearDown()

    def test_update_host_state(self):
        host.update_host_state(
            self.user_object,
            self.host_ids[0],
            state='INSTALLING'
        )
        host_states = host.get_host_state(
            self.user_object,
            self.host_ids[0]
        )
        self.assertEqual(host_states['state'], 'INSTALLING')


class TestGetHostLogHistories(HostTestCase):
    """Test get host log histories."""

    def setUp(self):
        super(TestGetHostLogHistories, self).setUp()

    def tearDown(self):
        super(TestGetHostLogHistories, self).tearDown()

    def test_get_host_log_histories(self):
        logs = host.get_host_log_histories(
            self.user_object,
            self.host_ids[0]
        )
        filenames = []
        for log in logs:
            filenames.append(log['filename'])
        for filename in filenames:
            self.assertIn(filename, ['log1', 'log2'])


class TestGetHostLogHistory(HostTestCase):
    """Test get host log history."""

    def setUp(self):
        super(TestGetHostLogHistory, self).setUp()

    def tearDown(self):
        super(TestGetHostLogHistory, self).tearDown()

    def test_get_host_log_history(self):
        log = host.get_host_log_history(
            self.user_object,
            self.host_ids[0],
            'log1'
        )
        self.assertEqual(log['filename'], 'log1')


class TestUpdateHostLogHistory(HostTestCase):
    """Test update host log history."""

    def setUp(self):
        super(TestUpdateHostLogHistory, self).setUp()

    def tearDown(self):
        super(TestUpdateHostLogHistory, self).tearDown()

    def test_update_host_log_history(self):
        host.update_host_log_history(
            self.user_object,
            self.host_ids[0],
            'log1',
            severity='WARNING',
            message='update log'
        )
        logs = host.get_host_log_histories(
            self.user_object,
            self.host_ids[0]
        )
        result = []
        for log in logs:
            result.append(log['severity'])
            result.append(log['message'])
        expects = ['WARNING', 'update log']
        for expect in expects:
            self.assertIn(expect, result)


class TestAddHostLogHistory(HostTestCase):
    """Test add host log history."""

    def setUp(self):
        super(TestAddHostLogHistory, self).setUp()

    def tearDown(self):
        super(TestAddHostLogHistory, self).tearDown()

    def test_add_host_log_history(self):
        host.add_host_log_history(
            self.user_object,
            self.host_ids[0],
            filename='add_log'
        )
        logs = host.get_host_log_histories(
            self.user_object,
            self.host_ids[0]
        )
        result = []
        for log in logs:
            result.append(log['filename'])
        self.assertIn('add_log', result)


class TestPoweronHost(HostTestCase):
    """Test poweron host."""

    def setUp(self):
        super(TestPoweronHost, self).setUp()
        host.update_host_config(
            self.user_object,
            self.host_ids[0],
            os_config=self.os_configs
        )
        cluster.update_cluster_config(
            self.user_object,
            self.cluster_id,
            os_config=self.os_configs,
            package_config=self.package_configs
        )
        cluster.update_cluster_host(
            self.user_object,
            self.cluster_id,
            self.host_ids[0],
            roles=['allinone-compute']
        )
        cluster.review_cluster(
            self.user_object,
            self.cluster_id,
            review={
                'hosts': [self.host_ids[0]]
            }
        )

    def tearDown(self):
        super(TestPoweronHost, self).tearDown()

    def test_poweron_host(self):
        poweron_host = host.poweron_host(
            self.user_object,
            self.host_ids[0],
            poweron={'poweron': True}
        )
        self.assertEqual(
            poweron_host['status'],
            'poweron newname1 action sent'
        )


class TestPoweroffHost(HostTestCase):
    """Test poweroff host."""

    def setUp(self):
        super(TestPoweroffHost, self).setUp()
        host.update_host_config(
            self.user_object,
            self.host_ids[0],
            os_config=self.os_configs
        )
        cluster.update_cluster_config(
            self.user_object,
            self.cluster_id,
            os_config=self.os_configs,
            package_config=self.package_configs
        )
        cluster.update_cluster_host(
            self.user_object,
            self.cluster_id,
            self.host_ids[0],
            roles=['allinone-compute']
        )
        cluster.review_cluster(
            self.user_object,
            self.cluster_id,
            review={
                'hosts': [self.host_ids[0]]
            }
        )

    def tearDown(self):
        super(TestPoweroffHost, self).tearDown()

    def test_poweroff_host(self):
        poweroff_host = host.poweroff_host(
            self.user_object,
            self.host_ids[0],
            poweroff={'poweroff': True}
        )
        self.assertEqual(
            poweroff_host['status'],
            'poweroff newname1 action sent'
        )


class TestResetHost(HostTestCase):
    """Test reset host."""

    def setUp(self):
        super(TestResetHost, self).setUp()
        host.update_host_config(
            self.user_object,
            self.host_ids[0],
            os_config=self.os_configs
        )
        cluster.update_cluster_config(
            self.user_object,
            self.cluster_id,
            os_config=self.os_configs,
            package_config=self.package_configs
        )
        cluster.update_cluster_host(
            self.user_object,
            self.cluster_id,
            self.host_ids[0],
            roles=['allinone-compute']
        )
        cluster.review_cluster(
            self.user_object,
            self.cluster_id,
            review={
                'hosts': [self.host_ids[0]]
            }
        )

    def tearDown(self):
        super(TestResetHost, self).tearDown()

    def test_reset_host(self):
        reset_host = host.reset_host(
            self.user_object,
            self.host_ids[0],
            reset={'reset': True}
        )
        self.assertEqual(reset_host['status'], 'reset newname1 action sent')


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
