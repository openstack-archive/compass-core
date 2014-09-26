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
import mock
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


class ClusterTestCase(unittest2.TestCase):
    """Cluster base test case."""

    def setUp(self):
        super(ClusterTestCase, self).setUp()
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
        self.adapter_id = None
        self.os_id = None
        self.flavor_id = None
        self.cluster_id = None

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
        # add cluster config
        cluster.update_cluster_config(
            self.user_object,
            self.cluster_id,
            os_config=self.os_configs,
            package_config=self.package_configs
        )
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
        self.host_id = []
        self.clusterhost_id = []
        clusterhosts = cluster.list_clusterhosts(self.user_object)
        for clusterhost in clusterhosts:
            self.host_id.append(clusterhost['host_id'])
            self.clusterhost_id.append(clusterhost['clusterhost_id'])

        # add log file
        file_names = ['log_file1', 'log_file2']
        for file_name in file_names:
            cluster.add_cluster_host_log_history(
                self.user_object,
                self.cluster_id,
                self.host_id[0],
                filename=file_name
            )

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
            self.host_id[0],
            interface='eth0',
            ip='10.145.88.0',
            subnet_id=self.subnet_ids[0],
            is_mgmt=True
        )
        host.add_host_network(
            self.user_object,
            self.host_id[0],
            interface='eth1',
            ip='10.145.88.10',
            subnet_id=self.subnet_ids[0],
            is_promiscuous=True
        )
        host.list_host_networks(
            self.user_object,
            self.host_id[0]
        )

    def tearDown(self):
        super(ClusterTestCase, self).tearDown()


class TestListClusters(ClusterTestCase):
    """Test list clusters."""

    def setUp(self):
        super(TestListClusters, self).setUp()

    def tearDown(self):
        super(TestListClusters, self).tearDown()

    def test_list_clusters(self):
        clusters = cluster.list_clusters(self.user_object)
        result = []
        for list_cluster in clusters:
            result.append(list_cluster['name'])
        expects = ['test_cluster1', 'test_cluster2']
        self.assertIsNotNone(clusters)
        for expect in expects:
            self.assertIn(expect, result)


class TestGetCluster(ClusterTestCase):
    """Test get cluster."""

    def setUp(self):
        super(TestGetCluster, self).setUp()

    def tearDown(self):
        super(TestGetCluster, self).tearDown()

    def test_get_cluster(self):
        get_cluster = cluster.get_cluster(
            self.user_object,
            self.cluster_id
        )
        self.assertIsNotNone(get_cluster)
        self.assertEqual(get_cluster['name'], 'test_cluster1')

    def test_non_exsit_cluster_id(self):
        self.assertRaises(
            exception.RecordNotExists,
            cluster.get_cluster,
            self.user_object,
            99
        )


class TestAddCluster(ClusterTestCase):
    """Test add cluster."""

    def setUp(self):
        super(TestAddCluster, self).setUp()

    def tearDown(self):
        super(TestAddCluster, self).tearDown()

    def test_add_cluster(self):
        cluster.add_cluster(
            self.user_object,
            adapter_id=self.adapter_id,
            os_id=self.os_id,
            flavor_id=self.flavor_id,
            name='test_add_cluster'
        )
        add_clusters = cluster.list_clusters(self.user_object)
        result = []
        for add_cluster in add_clusters:
            result.append(add_cluster['name'])
        self.assertIn('test_add_cluster', result)


class TestUpdateCluster(ClusterTestCase):
    """Test update cluster."""

    def setUp(self):
        super(TestUpdateCluster, self).setUp()

    def tearDown(self):
        super(TestUpdateCluster, self).tearDown()

    def test_update_cluster(self):
        cluster.update_cluster(
            self.user_object,
            self.cluster_id,
            name='test_update_cluster'
        )
        update_cluster = cluster.get_cluster(
            self.user_object,
            self.cluster_id
        )
        self.assertEqual(update_cluster['name'], 'test_update_cluster')

    def test_is_cluster_editable(self):
        # state is INSTALLING
        cluster.update_cluster_state(
            self.user_object,
            self.cluster_id,
            state='INSTALLING'
        )
        self.assertRaises(
            exception.Forbidden,
            cluster.update_cluster,
            self.user_object,
            self.cluster_id,
            name='cluster_editable'
        )

        #reinstall
        self.assertRaises(
            exception.Forbidden,
            cluster.update_cluster,
            self.user_object,
            self.cluster_id,
            reinstall_distributed_system=True
        )


class TestDelCluster(ClusterTestCase):
    """Test delete cluster."""

    def setUp(self):
        super(TestDelCluster, self).setUp()

    def tearDown(self):
        super(TestDelCluster, self).setUp()

    def test_del_cluster(self):
        cluster.del_cluster(
            self.user_object,
            self.cluster_id
        )
        del_clusters = cluster.list_clusters(self.user_object)
        cluster_ids = []
        for del_cluster in del_clusters:
            cluster_ids.append(del_cluster['id'])
        self.assertNotIn(self.cluster_id, cluster_ids)

    def test_is_cluster_editable(self):
        #state is INSTALLING
        cluster.update_cluster_state(
            self.user_object,
            self.cluster_id,
            state='INSTALLING'
        )
        self.assertRaises(
            exception.Forbidden,
            cluster.del_cluster,
            self.user_object,
            self.cluster_id,
        )


class TestGetClusterConfig(ClusterTestCase):
    """Test get cluster config."""

    def setUp(self):
        super(TestGetClusterConfig, self).setUp()
        cluster.update_cluster_config(
            self.user_object,
            self.cluster_id,
            os_config=self.os_configs,
            package_config=self.package_configs
        )

    def tearDown(self):
        super(TestGetClusterConfig, self).tearDown()

    def test_get_cluster_config(self):
        cluster_config = cluster.get_cluster_config(
            self.user_object,
            self.cluster_id
        )
        package_config = cluster_config['package_config']
        os_config = cluster_config['os_config']
        self.assertItemsEqual(package_config, self.package_configs)
        self.assertItemsEqual(os_config, self.os_configs)


class TestGetClusterDeployedConfig(ClusterTestCase):

    def setUp(self):
        super(TestGetClusterDeployedConfig, self).setUp()
        cluster.update_cluster_config(
            self.user_object,
            self.cluster_id,
            os_config=self.os_configs,
            package_config=self.package_configs
        )
        cluster.update_cluster_host(
            self.user_object,
            self.cluster_id,
            self.host_id[0],
            roles=['allinone-compute']
        )
        cluster.review_cluster(
            self.user_object,
            self.cluster_id,
            review={
                'hosts': [self.host_id[0]]
            }
        )
        cluster.update_cluster_deployed_config(
            self.user_object,
            self.cluster_id,
            os_config=self.os_configs,
            package_config=self.package_configs
        )

    def tearDown(self):
        super(TestGetClusterDeployedConfig, self).tearDown()

    def test_get_cluster_deployed_config(self):
        configs = cluster.get_cluster_deployed_config(
            self.user_object,
            self.cluster_id
        )
        os_config = configs['deployed_os_config']
        package_config = configs['deployed_package_config']
        self.assertItemsEqual(os_config, self.os_configs)
        self.assertItemsEqual(package_config, self.package_configs)


class TestGetClusterMetadata(ClusterTestCase):
    """Test get cluster metadata."""

    def setUp(self):
        super(TestGetClusterMetadata, self).setUp()

    def tearDown(self):
        super(TestGetClusterMetadata, self).tearDown()

    def test_get_cluster_metadata(self):
        cluster_metadata = cluster.get_cluster_metadata(
            self.user_object,
            self.cluster_id
        )
        results = []
        for k, v in cluster_metadata.items():
            results.append(k)
        expected = ['os_config', 'package_config']
        self.assertIsNotNone(cluster_metadata)
        for result in results:
            self.assertIn(result, expected)


class TestUpdateClusterConfig(ClusterTestCase):
    """Test update cluster config."""

    def setUp(self):
        super(TestUpdateClusterConfig, self).setUp()

    def tearDown(self):
        super(TestUpdateClusterConfig, self).tearDown()

    def test_update_cluster_config(self):
        cluster.update_cluster_config(
            self.user_object,
            self.cluster_id,
            put_os_config=self.os_configs,
            put_package_config=self.package_configs
        )
        update_cluster_config = cluster.get_cluster_config(
            self.user_object,
            self.cluster_id
        )
        package_config = update_cluster_config['package_config']
        os_config = update_cluster_config['os_config']
        self.assertItemsEqual(package_config, self.package_configs)
        self.assertItemsEqual(os_config, self.os_configs)


class TestPatchClusterConfig(ClusterTestCase):
    """Test patch cluster config."""

    def setUp(self):
        super(TestPatchClusterConfig, self).setUp()

    def tearDown(self):
        super(TestPatchClusterConfig, self).tearDown()

    def test_patch_cluster_config(self):
        patch_cluster_config = cluster.patch_cluster_config(
            self.user_object,
            self.cluster_id,
            package_config=self.package_configs,
            os_config=self.os_configs
        )
        package_config = patch_cluster_config['package_config']
        os_config = patch_cluster_config['os_config']
        self.assertItemsEqual(package_config, self.package_configs)
        self.assertItemsEqual(os_config, self.os_configs)


class TestDelClusterConfig(ClusterTestCase):
    """Test delete a cluster config."""

    def setUp(self):
        super(TestDelClusterConfig, self).setUp()
        cluster.update_cluster_config(
            self.user_object,
            self.cluster_id,
            os_config=self.os_configs,
            package_config=self.package_configs
        )

    def tearDown(self):
        super(TestDelClusterConfig, self).tearDown()

    def test_del_cluster_config(self):
        cluster.del_cluster_config(
            self.user_object,
            self.cluster_id
        )
        del_cluster_config = cluster.get_cluster_config(
            self.user_object,
            self.cluster_id
        )
        configs = []
        for k, v in del_cluster_config.items():
            if k == 'package_config' or k == 'os_config':
                configs.append(v)
        for config in configs:
            self.assertEqual(config, {})

    def test_cluster_editable(self):
        cluster.update_cluster_state(
            self.user_object,
            self.cluster_id,
            state='INSTALLING'
        )
        self.assertRaises(
            exception.Forbidden,
            cluster.del_cluster_config,
            self.user_object,
            self.cluster_id
        )


class TestListClusterHosts(ClusterTestCase):
    """Test list cluster hosts."""

    def setUp(self):
        super(TestListClusterHosts, self).setUp()

    def tearDown(self):
        super(TestListClusterHosts, self).tearDown()

    def test_list_cluster_hosts(self):
        list_cluster_hosts = cluster.list_cluster_hosts(
            self.user_object,
            self.cluster_id
        )
        results = []
        expected = ['28:6e:d4:46:c4:25', '00:0c:29:bf:eb:1d']
        for item in list_cluster_hosts:
            results.append(item['mac'])
        for result in results:
            self.assertIn(result, expected)


class TestListClusterhosts(ClusterTestCase):
    """Test list clusterhosts."""

    def setUp(self):
        super(TestListClusterhosts, self).setUp()

    def tearDown(self):
        super(TestListClusterhosts, self).tearDown()

    def test_list_clusterhosts(self):
        list_clusterhosts = cluster.list_clusterhosts(self.user_object)
        results = []
        expected = ['28:6e:d4:46:c4:25', '00:0c:29:bf:eb:1d']
        for item in list_clusterhosts:
            results.append(item['mac'])
        for result in results:
            self.assertIn(result, expected)


class TestGetClusterHost(ClusterTestCase):
    """Test get cluster host."""

    def setUp(self):
        super(TestGetClusterHost, self).setUp()

    def tearDown(self):
        super(TestGetClusterHost, self).tearDown()

    def test_get_cluster_host(self):
        get_cluster_host = cluster.get_cluster_host(
            self.user_object,
            self.cluster_id,
            self.host_id[1]
        )
        self.assertEqual(get_cluster_host['mac'], '00:0c:29:bf:eb:1d')


class TestGetClusterhost(ClusterTestCase):
    """Test get clusterhost."""

    def setUp(self):
        super(TestGetClusterhost, self).setUp()

    def tearDown(self):
        super(TestGetClusterhost, self).tearDown()

    def test_get_clusterhost(self):
        get_clusterhost = cluster.get_clusterhost(
            self.user_object,
            self.clusterhost_id[1]
        )
        self.assertEqual(get_clusterhost['mac'], '00:0c:29:bf:eb:1d')


class TestAddClusterHost(ClusterTestCase):
    """Test add cluster host."""

    def setUp(self):
        super(TestAddClusterHost, self).setUp()
        switch.add_switch_machine(
            self.user_object,
            self.switch_id,
            mac='00:0c:29:5b:ee:eb',
            port='1'
        )
        machines = machine.list_machines(self.user_object)
        self.add_machine_id = None
        for item in machines:
            if item['mac'] == '00:0c:29:5b:ee:eb':
                self.add_machine_id = item['id']

    def tearDown(self):
        super(TestAddClusterHost, self).tearDown()

    def test_add_cluster_host(self):
        # add a cluster_host
        cluster.add_cluster_host(
            self.user_object,
            self.cluster_id,
            machine_id=self.add_machine_id,
            name='test_add_cluster_host'
        )
        add_cluster_hosts = cluster.list_clusterhosts(self.user_object)
        result = []
        for item in add_cluster_hosts:
            result.append(item['mac'])
        self.assertIn('00:0c:29:5b:ee:eb', result)

    def test_is_cluster_editable(self):
        # installing
        cluster.update_cluster_state(
            self.user_object,
            self.cluster_id,
            state='INSTALLING'
        )
        self.assertRaises(
            exception.Forbidden,
            cluster.add_cluster_host,
            self.user_object,
            self.cluster_id,
            machine_id=self.add_machine_id
        )


class TestUpdateClusterHost(ClusterTestCase):
    """Test update cluster host."""

    def setUp(self):
        super(TestUpdateClusterHost, self).setUp()

    def tearDown(self):
        super(TestUpdateClusterHost, self).tearDown()

    def test_update_cluster_host(self):
        cluster.update_cluster_host(
            self.user_object,
            self.cluster_id,
            self.host_id[0],
            roles=['allinone-compute']
        )
        update_cluster_hosts = cluster.list_cluster_hosts(
            self.user_object,
            self.cluster_id
        )
        result = None
        for item in update_cluster_hosts:
            if item['roles']:
                result = item['roles'][0]['display_name']
        self.assertEqual(result, 'all in one compute')

    def test_invalid_role(self):
        self.assertRaises(
            exception.InvalidParameter,
            cluster.update_cluster_host,
            self.user_object,
            self.cluster_id,
            self.host_id[0],
            roles=['invalid_role']
        )

    def test_is_cluster_editable(self):
        # state is INSTALLING
        cluster.update_cluster_state(
            self.user_object,
            self.cluster_id,
            state='INSTALLING'
        )
        self.assertRaises(
            exception.Forbidden,
            cluster.update_cluster_host,
            self.user_object,
            self.cluster_id,
            self.host_id[0],
        )


class TestUpdateClusterhost(ClusterTestCase):
    """Test update clusterhost."""

    def setUp(self):
        super(TestUpdateClusterhost, self).setUp()

    def tearDown(self):
        super(TestUpdateClusterhost, self).tearDown()

    def test_update_clusterhost(self):
        cluster.update_clusterhost(
            self.user_object,
            self.clusterhost_id[0],
            roles=['allinone-compute']
        )
        update_clusterhosts = cluster.list_clusterhosts(
            self.user_object,
        )
        result = None
        for item in update_clusterhosts:
            if item['roles']:
                result = item['roles'][0]['display_name']
        self.assertEqual(result, 'all in one compute')

    def test_invalid_role(self):
        self.assertRaises(
            exception.InvalidParameter,
            cluster.update_clusterhost,
            self.user_object,
            self.clusterhost_id[0],
            roles=['invalid_role']
        )

    def test_is_cluster_editable(self):
        # state is INSTALLING
        cluster.update_cluster_state(
            self.user_object,
            self.cluster_id,
            state='INSTALLING'
        )
        self.assertRaises(
            exception.Forbidden,
            cluster.update_clusterhost,
            self.user_object,
            self.clusterhost_id[0]
        )


class TestPatchClusterHost(ClusterTestCase):

    def setUp(self):
        super(TestPatchClusterHost, self).setUp()

    def tearDown(self):
        super(TestPatchClusterHost, self).tearDown()

    def test_patch_cluster_host(self):
        cluster.patch_cluster_host(
            self.user_object,
            self.cluster_id,
            self.host_id[0],
            roles=['allinone-compute']
        )
        patch = cluster.list_cluster_hosts(
            self.user_object,
            self.cluster_id
        )
        result = None
        for item in patch:
            for role in item['roles']:
                result = role['display_name']
        self.assertEqual(result, 'all in one compute')

    def test_is_cluster_editable(self):
        cluster.update_cluster_state(
            self.user_object,
            self.cluster_id,
            state='INSTALLING'
        )
        self.assertRaises(
            exception.Forbidden,
            cluster.patch_cluster_host,
            self.user_object,
            self.cluster_id,
            self.host_id[0]
        )


class TestPatchClusterhost(ClusterTestCase):
    def setUp(self):
        super(TestPatchClusterhost, self).setUp()

    def tearDown(self):
        super(TestPatchClusterhost, self).tearDown()

    def test_patch_clusterhost(self):
        cluster.patch_clusterhost(
            self.user_object,
            self.clusterhost_id[0],
            roles=['allinone-compute']
        )
        patch = cluster.list_cluster_hosts(
            self.user_object,
            self.cluster_id
        )
        result = None
        for item in patch:
            for role in item['roles']:
                result = role['display_name']
        self.assertEqual(result, 'all in one compute')

    def testi_is_cluster_editable(self):
        cluster.update_cluster_state(
            self.user_object,
            self.cluster_id,
            state='INSTALLING'
        )
        self.assertRaises(
            exception.Forbidden,
            cluster.patch_clusterhost,
            self.user_object,
            self.clusterhost_id[0]
        )


class TestDelClusterHost(ClusterTestCase):
    """test delete cluster host."""

    def setUp(self):
        super(TestDelClusterHost, self).setUp()

    def tearDown(self):
        super(TestDelClusterHost, self).tearDown()

    def test_del_cluster_host(self):
        cluster.del_cluster_host(
            self.user_object,
            self.cluster_id,
            self.host_id[0]
        )
        del_cluster_host = cluster.list_cluster_hosts(
            self.user_object,
            self.cluster_id
        )
        result = []
        for item in del_cluster_host:
            result.append(item['hostname'])
        self.assertNotIn('newname1', result)

    def test_is_cluster_editable(self):
        cluster.update_cluster_state(
            self.user_object,
            self.cluster_id,
            state='INSTALLING'
        )
        self.assertRaises(
            exception.Forbidden,
            cluster.del_cluster_host,
            self.user_object,
            self.cluster_id,
            self.host_id[0]
        )


class TestDelClusterhost(ClusterTestCase):
    """test delete clusterhost."""

    def setUp(self):
        super(TestDelClusterhost, self).setUp()

    def tearDown(self):
        super(TestDelClusterhost, self).tearDown()

    def test_del_clusterhost(self):
        cluster.del_clusterhost(
            self.user_object,
            self.clusterhost_id[0]
        )
        del_clusterhost = cluster.list_clusterhosts(self.user_object)
        result = []
        for item in del_clusterhost:
            result.append(item['hostname'])
        self.assertNotIn('newname1', result)

    def test_is_cluster_editable(self):
        cluster.update_cluster_state(
            self.user_object,
            self.cluster_id,
            state='INSTALLING'
        )
        self.assertRaises(
            exception.Forbidden,
            cluster.del_clusterhost,
            self.user_object,
            self.clusterhost_id[0]
        )


class TestGetClusterHostConfig(ClusterTestCase):
    """Test get cluster host config."""

    def setUp(self):
        super(TestGetClusterHostConfig, self).setUp()
        cluster.update_cluster_host_config(
            self.user_object,
            self.cluster_id,
            self.host_id[0],
            os_config=self.os_configs,
            package_config=self.package_configs
        )

    def tearDown(self):
        super(TestGetClusterHostConfig, self).tearDown()

    def test_get_cluster_host_config(self):
        configs = cluster.get_cluster_host_config(
            self.user_object,
            self.cluster_id,
            self.host_id[0]
        )
        package_config = configs['package_config']
        os_config = configs['os_config']
        self.assertItemsEqual(package_config, self.package_configs)
        self.assertItemsEqual(os_config, self.os_configs)


class TestGetClusterhostConfig(ClusterTestCase):
    """Test get clusterhost config."""

    def setUp(self):
        super(TestGetClusterhostConfig, self).setUp()
        cluster.update_clusterhost_config(
            self.user_object,
            self.clusterhost_id[0],
            os_config=self.os_configs,
            package_config=self.package_configs
        )

    def tesrDown(self):
        super(TestGetClusterhostConfig, self).tearDown()

    def test_get_clusterhost_config(self):
        configs = cluster.get_clusterhost_config(
            self.user_object,
            self.clusterhost_id[0]
        )
        package_config = configs['package_config']
        os_config = configs['os_config']
        self.assertItemsEqual(package_config, self.package_configs)
        self.assertItemsEqual(os_config, self.os_configs)


class TestGetClusterHostDeployedConfig(ClusterTestCase):

    def setUp(self):
        super(TestGetClusterHostDeployedConfig, self).setUp()
        cluster.update_cluster_host_config(
            self.user_object,
            self.cluster_id,
            self.host_id[0],
            os_config=self.os_configs,
            package_config=self.package_configs
        )
        cluster.update_cluster_host(
            self.user_object,
            self.cluster_id,
            self.host_id[0],
            roles=['allinone-compute']
        )
        cluster.review_cluster(
            self.user_object,
            self.cluster_id,
            review={
                'hosts': [self.host_id[0]]
            }
        )
        cluster.update_cluster_host_deployed_config(
            self.user_object,
            self.cluster_id,
            self.host_id[0],
            os_config=self.os_configs,
            package_config=self.package_configs
        )

    def tearDown(self):
        super(TestGetClusterHostDeployedConfig, self).tearDown()

    def test_get_cluster_host_deployed_config(self):
        configs = cluster.get_cluster_host_deployed_config(
            self.user_object,
            self.cluster_id,
            self.host_id[0]
        )
        package_config = configs['deployed_package_config']
        os_config = configs['deployed_os_config']
        self.assertItemsEqual(package_config, self.package_configs)
        self.assertItemsEqual(os_config, self.os_configs)


class TestGetClusterhostDeployedConfig(ClusterTestCase):
    """Test get clusterhost deployed config."""

    def setUp(self):
        super(TestGetClusterhostDeployedConfig, self).setUp()
        cluster.update_clusterhost_config(
            self.user_object,
            self.clusterhost_id[0],
            os_config=self.os_configs,
            package_config=self.package_configs
        )
        cluster.update_clusterhost(
            self.user_object,
            self.clusterhost_id[0],
            roles=['allinone-compute']
        )
        cluster.review_cluster(
            self.user_object,
            self.cluster_id,
            review={
                'hosts': [self.host_id[0]]
            }
        )
        cluster.update_clusterhost_deployed_config(
            self.user_object,
            self.clusterhost_id[0],
            os_config=self.os_configs,
            package_config=self.package_configs
        )

    def tearDown(self):
        super(TestGetClusterhostDeployedConfig, self).tearDown()

    def test_get_clusterhost_deployed_config(self):
        configs = cluster.get_clusterhost_deployed_config(
            self.user_object,
            self.clusterhost_id[0]
        )
        package_config = configs['deployed_package_config']
        os_config = configs['deployed_os_config']
        self.assertItemsEqual(package_config, self.package_configs)
        self.assertItemsEqual(os_config, self.os_configs)


class TestUpdateClusterHostConfig(ClusterTestCase):
    """Test update cluster host config."""

    def setUp(self):
        super(TestUpdateClusterHostConfig, self).setUp()

    def tearDown(self):
        super(TestUpdateClusterHostConfig, self).tearDown()

    def test_update_cluster_host_config(self):
        cluster.update_cluster_host_config(
            self.user_object,
            self.cluster_id,
            self.host_id[0],
            os_config=self.os_configs,
            package_config=self.package_configs
        )
        config = cluster.get_cluster_host_config(
            self.user_object,
            self.cluster_id,
            self.host_id[0]
        )
        package_configs = config['package_config']
        os_configs = config['os_config']
        self.assertItemsEqual(package_configs, self.package_configs)
        self.assertItemsEqual(os_configs, self.os_configs)

    def test_is_cluster_editable(self):
        cluster.update_cluster_state(
            self.user_object,
            self.cluster_id,
            state='INSTALLING'
        )
        self.assertRaises(
            exception.Forbidden,
            cluster.update_cluster_host_config,
            self.user_object,
            self.cluster_id,
            self.host_id[0],
            os_config=self.os_configs,
            package_config=self.package_configs
        )


class TestUpdateClusterHostDeployedConfig(ClusterTestCase):
    """Test update cluster host deployed config."""

    def setUp(self):
        super(TestUpdateClusterHostDeployedConfig, self).setUp()
        cluster.update_cluster_host_config(
            self.user_object,
            self.cluster_id,
            self.host_id[0],
            os_config=self.os_configs,
            package_config=self.package_configs
        )
        cluster.update_clusterhost(
            self.user_object,
            self.clusterhost_id[0],
            roles=['allinone-compute']
        )
        cluster.review_cluster(
            self.user_object,
            self.cluster_id,
            review={
                'clusterhosts': [self.clusterhost_id[0]]
            }
        )

    def tearDown(self):
        super(TestUpdateClusterHostDeployedConfig, self).tearDown()

    def test_udpate_cluster_host_deployed_config(self):
        cluster.update_cluster_host_deployed_config(
            self.user_object,
            self.cluster_id,
            self.host_id[0],
            os_config=self.os_configs,
            package_config=self.package_configs
        )
        configs = cluster.get_cluster_host_deployed_config(
            self.user_object,
            self.cluster_id,
            self.host_id[0]
        )
        package_config = configs['deployed_package_config']
        os_config = configs['deployed_os_config']
        self.assertItemsEqual(package_config, self.package_configs)
        self.assertItemsEqual(os_config, self.os_configs)


class TestUpdateClusterhostConfig(ClusterTestCase):
    """Test update clusterhost config."""

    def setUp(self):
        super(TestUpdateClusterhostConfig, self).setUp()

    def tearDown(self):
        super(TestUpdateClusterhostConfig, self).tearDown()

    def test_update_clusterhost_config(self):
        cluster.update_clusterhost_config(
            self.user_object,
            self.clusterhost_id[0],
            os_config=self.os_configs,
            package_config=self.package_configs
        )
        configs = cluster.get_clusterhost_config(
            self.user_object,
            self.clusterhost_id[0]
        )
        package_config = configs['package_config']
        os_config = configs['os_config']
        self.assertItemsEqual(package_config, self.package_configs)
        self.assertItemsEqual(os_config, self.os_configs)

    def test_id_cluster_editable(self):
        cluster.update_cluster_state(
            self.user_object,
            self.cluster_id,
            state='INSTALLING'
        )
        self.assertRaises(
            exception.Forbidden,
            cluster.update_clusterhost_config,
            self.user_object,
            self.clusterhost_id[0],
            os_config=self.os_configs,
            package_config=self.package_configs
        )


class TestUpdateClusterhostDeployedConfig(ClusterTestCase):
    """Test update clusterhost config."""

    def setUp(self):
        super(TestUpdateClusterhostDeployedConfig, self).setUp()
        cluster.update_clusterhost_config(
            self.user_object,
            self.clusterhost_id[0],
            os_config=self.os_configs,
            package_config=self.package_configs
        )
        cluster.update_cluster_host(
            self.user_object,
            self.cluster_id,
            self.host_id[0],
            roles=['allinone-compute']
        )
        cluster.review_cluster(
            self.user_object,
            self.cluster_id,
            review={
                'clusterhosts': [self.clusterhost_id[0]]
            }
        )

    def tearDown(self):
        super(TestUpdateClusterhostDeployedConfig, self).tearDown()

    def test_update_clusterhost_config(self):
        cluster.update_clusterhost_deployed_config(
            self.user_object,
            self.clusterhost_id[0],
            os_config=self.os_configs,
            package_config=self.package_configs
        )
        configs = cluster.get_clusterhost_deployed_config(
            self.user_object,
            self.clusterhost_id[0]
        )
        package_config = configs['deployed_package_config']
        os_config = configs['deployed_os_config']
        self.assertItemsEqual(package_config, self.package_configs)
        self.assertItemsEqual(os_config, self.os_configs)


class TestPatchClusterHostConfig(ClusterTestCase):
    """Test patch cluster host config."""

    def setUp(self):
        super(TestPatchClusterHostConfig, self).setUp()

    def tearDown(self):
        super(TestPatchClusterHostConfig, self).tearDown()

    def test_patch_cluster_host_config(self):
        cluster.patch_cluster_host_config(
            self.user_object,
            self.cluster_id,
            self.host_id[0],
            os_config=self.os_configs,
            package_config=self.package_configs
        )
        configs = cluster.get_cluster_host_config(
            self.user_object,
            self.cluster_id,
            self.host_id[0]
        )
        package_config = configs['package_config']
        os_config = configs['os_config']
        self.assertItemsEqual(package_config, self.package_configs)
        self.assertItemsEqual(os_config, self.os_configs)

    def test_is_cluster_editable(self):
        cluster.update_cluster_state(
            self.user_object,
            self.cluster_id,
            state='INSTALLING'
        )
        self.assertRaises(
            exception.Forbidden,
            cluster.patch_cluster_host_config,
            self.user_object,
            self.cluster_id,
            self.host_id[0],
            os_config=self.os_configs,
            package_config=self.package_configs
        )


class TestPatchClusterhostConfig(ClusterTestCase):
    """Test patch clusterhost config."""

    def setUp(self):
        super(TestPatchClusterhostConfig, self).setUp()

    def tearDown(self):
        super(TestPatchClusterhostConfig, self).tearDown()

    def test_patch_clusterhost_config(self):
        cluster.patch_clusterhost_config(
            self.user_object,
            self.clusterhost_id[0],
            os_config=self.os_configs,
            package_config=self.package_configs
        )
        config = cluster.get_clusterhost_config(
            self.user_object,
            self.clusterhost_id[0]
        )
        package_config = config['package_config']
        os_config = config['os_config']
        self.assertItemsEqual(package_config, self.package_configs)
        self.assertItemsEqual(os_config, self.os_configs)

    def test_is_cluster_editable(self):
        cluster.update_cluster_state(
            self.user_object,
            self.cluster_id,
            state='INSTALLING'
        )
        self.assertRaises(
            exception.Forbidden,
            cluster.patch_clusterhost_config,
            self.user_object,
            self.clusterhost_id[0],
            os_config=self.os_configs,
            package_config=self.package_configs
        )


class TestDeleteClusterHostConfig(ClusterTestCase):
    """Test delete cluster host config."""

    def setUp(self):
        super(TestDeleteClusterHostConfig, self).setUp()
        cluster.update_cluster_host_config(
            self.user_object,
            self.cluster_id,
            self.host_id[0],
            os_config=self.os_configs,
            package_config=self.package_configs
        )

    def tearDown(self):
        super(TestDeleteClusterHostConfig, self).tearDown()

    def test_delete_cluster_host_config(self):
        cluster.delete_cluster_host_config(
            self.user_object,
            self.cluster_id,
            self.host_id[0],
        )
        del_cluster_host_config = cluster.get_cluster_host_config(
            self.user_object,
            self.cluster_id,
            self.host_id[0]
        )
        configs = []
        for k, v in del_cluster_host_config.items():
            if k == 'package_config':
                configs.append(v)
        for config in configs:
            self.assertEqual(config, {})

    def test_is_cluster_editable(self):
        cluster.update_cluster_state(
            self.user_object,
            self.cluster_id,
            state='INSTALLING'
        )
        self.assertRaises(
            exception.Forbidden,
            cluster.delete_cluster_host_config,
            self.user_object,
            self.cluster_id,
            self.host_id[0]
        )


class TestDeleteClusterhostConfig(ClusterTestCase):
    """Test delete clusterhost config."""

    def setUp(self):
        super(TestDeleteClusterhostConfig, self).setUp()
        cluster.update_clusterhost_config(
            self.user_object,
            self.clusterhost_id[0],
            os_config=self.os_configs,
            package_config=self.package_configs
        )

    def tearDown(self):
        super(TestDeleteClusterhostConfig, self).setUp()

    def test_delete_clusterhost_config(self):
        cluster.delete_clusterhost_config(
            self.user_object,
            self.clusterhost_id[0]
        )
        del_clusterhost_config = cluster.get_clusterhost_config(
            self.user_object,
            self.clusterhost_id[0]
        )
        configs = []
        for k, v in del_clusterhost_config.items():
            if k == 'package_config':
                configs.append(v)
        for config in configs:
            self.assertEqual(config, {})

    def test_is_cluster_editable(self):
        cluster.update_cluster_state(
            self.user_object,
            self.cluster_id,
            state='INSTALLING'
        )
        self.assertRaises(
            exception.Forbidden,
            cluster.delete_clusterhost_config,
            self.user_object,
            self.clusterhost_id[0]
        )


class TestUpdateClusterHosts(ClusterTestCase):
    """Test update cluster hosts."""

    def setUp(self):
        super(TestUpdateClusterHosts, self).setUp()
        switch.add_switch_machine(
            self.user_object,
            self.switch_id,
            mac='00:0c:29:5b:ee:eb',
            port='1'
        )
        machines = machine.list_machines(self.user_object)
        self.add_machine_id = None
        for item in machines:
            if item['mac'] == '00:0c:29:5b:ee:eb':
                self.add_machine_id = item['id']

    def tearDown(self):
        super(TestUpdateClusterHosts, self).tearDown()

    def test_update_cluster_hosts(self):
        # remove host
        cluster.update_cluster_hosts(
            self.user_object,
            self.cluster_id,
            remove_hosts={'hosts': self.host_id[0]}
        )
        remove_hosts = cluster.list_cluster_hosts(
            self.user_object,
            self.cluster_id
        )
        result = None
        for item in remove_hosts:
            result = item
        self.assertNotIn(self.host_id[0], result)

        #add host
        cluster.update_cluster_hosts(
            self.user_object,
            self.cluster_id,
            add_hosts={'machines': [{'machine_id': self.add_machine_id}]}
        )
        add_hosts = cluster.list_cluster_hosts(
            self.user_object,
            self.cluster_id
        )
        result = None
        for item in add_hosts:
            if item['machine_id'] == self.add_machine_id:
                result = item['mac']
        self.assertEqual(result, '00:0c:29:5b:ee:eb')


class TestReviewCluster(ClusterTestCase):
    """Test review cluster."""

    def setUp(self):
        super(TestReviewCluster, self).setUp()
        cluster.update_clusterhost_config(
            self.user_object,
            self.clusterhost_id[0],
            os_config=self.os_configs,
            package_config=self.package_configs
        )
        cluster.update_cluster_host(
            self.user_object,
            self.cluster_id,
            self.host_id[0],
            roles=['allinone-compute']
        )

    def tearDown(self):
        super(TestReviewCluster, self).tearDown()

    def test_review_cluster(self):
        review_cluster = cluster.review_cluster(
            self.user_object,
            self.cluster_id,
            review={
                'hosts': [self.host_id[0]]
            }
        )
        cluster_package_config = None
        cluster_os_config = None
        for k, v in review_cluster['cluster'].items():
            if k == 'package_config':
                cluster_package_config = v
            if k == 'os_config':
                cluster_os_config = v
        host_package_config = None
        host_package_config = None
        for item in review_cluster['hosts']:
            for k, v in item.items():
                if k == 'package_config':
                    host_package_config = v
                if k == 'os_config':
                    host_os_config = v
        self.assertItemsEqual(cluster_package_config, self.package_configs)
        self.assertItemsEqual(cluster_os_config, self.os_configs)
        self.assertItemsEqual(host_package_config, self.package_configs)
        self.assertItemsEqual(host_os_config, self.os_configs)


class TestDeployedCluster(ClusterTestCase):
    """Test deployed cluster."""

    def setUp(self):
        super(TestDeployedCluster, self).setUp()
        cluster.update_clusterhost_config(
            self.user_object,
            self.clusterhost_id[0],
            os_config=self.os_configs,
            package_config=self.package_configs
        )
        cluster.update_cluster_host(
            self.user_object,
            self.cluster_id,
            self.host_id[0],
            roles=['allinone-compute']
        )
        cluster.review_cluster(
            self.user_object,
            self.cluster_id,
            review={
                'hosts': [self.host_id[0]],
                'clusterhosts': [self.clusterhost_id[0]]
            }
        )

    def tearDown(self):
        super(TestDeployedCluster, self).tearDown()

    def test_deploy_cluster(self):
        from compass.tasks import client as celery_client
        celery_client.celery.send_task = mock.Mock() 
        deploy_cluster = cluster.deploy_cluster(
            self.user_object,
            self.cluster_id,
            deploy={
                'hosts': [self.host_id[0]],
            }
        )
        cluster_package_config = None
        cluster_os_config = None
        for k, v in deploy_cluster['cluster'].items():
            if k == 'package_config':
                cluster_package_config = v
            if k == 'os_config':
                cluster_os_config = v
        self.assertItemsEqual(cluster_package_config, self.package_configs)
        self.assertItemsEqual(cluster_os_config, self.os_configs)
        expecteds = {
            'clusterhost_id': self.clusterhost_id[0],
            'cluster_id': self.cluster_id,
            'hostname': 'newname1',
            'mac': '28:6e:d4:46:c4:25',
            'clustername': 'test_cluster1'
        }
        result = None
        for item in deploy_cluster['hosts']:
            result = item
        self.assertDictContainsSubset(expecteds, result)


class TestGetClusterState(ClusterTestCase):
    """Test get cluster state."""

    def setUp(self):
        super(TestGetClusterState, self).setUp()

    def tearDown(self):
        super(TestGetClusterState, self).tearDown()

    def test_get_cluster_state(self):
        cluster_state = cluster.get_cluster_state(
            self.user_object,
            self.cluster_id
        )
        self.assertEqual(cluster_state['state'], 'UNINITIALIZED')


class TestGetClusterHostState(ClusterTestCase):
    """Test get cluster host state."""

    def setUp(self):
        super(TestGetClusterHostState, self).setUp()

    def tearDown(self):
        super(TestGetClusterHostState, self).tearDown()

    def test_get_cluster_host_state(self):
        cluster_host_state = cluster.get_cluster_host_state(
            self.user_object,
            self.cluster_id,
            self.host_id[0]
        )
        self.assertEqual(cluster_host_state['state'], 'UNINITIALIZED')


class TestGetClusterHostSelfState(ClusterTestCase):
    """Test get cluster hosts self state."""

    def setUp(self):
        super(TestGetClusterHostSelfState, self).setUp()

    def tearDown(self):
        super(TestGetClusterHostSelfState, self).tearDown()

    def test_get_cluster_host_self_state(self):
        cluster_host_self_state = cluster.get_cluster_host_self_state(
            self.user_object,
            self.cluster_id,
            self.host_id
        )
        self.assertEqual(cluster_host_self_state['state'], 'UNINITIALIZED')


class TestGetClusterhostState(ClusterTestCase):
    """Test get clusterhost state."""

    def setUp(self):
        super(TestGetClusterhostState, self).setUp()

    def tearDown(self):
        super(TestGetClusterhostState, self).tearDown()

    def test_get_clusterhost_state(self):
        clusterhost_state = cluster.get_clusterhost_state(
            self.user_object,
            self.clusterhost_id[0],
        )
        self.assertEqual(clusterhost_state['state'], 'UNINITIALIZED')


class TestGetClusterhostSelfState(ClusterTestCase):
    """Test get clusterhost state."""

    def setUp(self):
        super(TestGetClusterhostSelfState, self).setUp()

    def tearDown(self):
        super(TestGetClusterhostSelfState, self).tearDown()

    def test_get_clusterhost_state(self):
        clusterhost_state = cluster.get_clusterhost_self_state(
            self.user_object,
            self.clusterhost_id[0]
        )
        self.assertEqual(clusterhost_state['state'], 'UNINITIALIZED')


class TestUpdateClusterHostState(ClusterTestCase):
    """Test update cluster host state."""

    def setUp(self):
        super(TestUpdateClusterHostState, self).setUp()

    def tearDown(self):
        super(TestUpdateClusterHostState, self).tearDown()

    def test_update_cluster_host_state(self):
        cluster.update_cluster_host_state(
            self.user_object,
            self.cluster_id,
            self.host_id,
            state='INSTALLING'
        )
        update_state = cluster.get_cluster_host_state(
            self.user_object,
            self.cluster_id,
            self.host_id
        )
        self.assertEqual(update_state['state'], 'INSTALLING')


class TestUpdateClusterhostState(ClusterTestCase):
    """Test update clusterhost state."""

    def setUp(self):
        super(TestUpdateClusterhostState, self).setUp()

    def tearDown(self):
        super(TestUpdateClusterhostState, self).tearDown()

    def test_update_clusterhost_state(self):
        cluster.update_clusterhost_state(
            self.user_object,
            self.clusterhost_id[0],
            state='INSTALLING'
        )
        clusterhost_state = cluster.get_clusterhost_state(
            self.user_object,
            self.clusterhost_id[0]
        )
        self.assertEqual(clusterhost_state['state'], 'INSTALLING')


class TestUpdateClusterState(ClusterTestCase):
    """Test update cluster state."""

    def setUp(self):
        super(TestUpdateClusterState, self).setUp()

    def tearDown(self):
        super(TestUpdateClusterState, self).tearDown()

    def test_update_cluster_state(self):
        cluster.update_cluster_state(
            self.user_object,
            self.cluster_id,
            state='INSTALLING'
        )
        cluster_state = cluster.get_cluster_state(
            self.user_object,
            self.cluster_id
        )
        self.assertEqual(cluster_state['state'], 'INSTALLING')


class TestGetClusterHostLogHistories(ClusterTestCase):
    """Test get cluster host log histories."""

    def setUp(self):
        super(TestGetClusterHostLogHistories, self).setUp()

    def tearDown(self):
        super(TestGetClusterHostLogHistories, self).tearDown()

    def test_get_cluster_host_log_histories(self):
        logs = cluster.get_cluster_host_log_histories(
            self.user_object,
            self.cluster_id,
            self.host_id[0]
        )
        result = []
        for log in logs:
            result.append(log['filename'])
        for item in result:
            self.assertEqual(result, ['log_file1', 'log_file2'])


class TestGetClusterhostLogHistories(ClusterTestCase):
    """Test get clusterhost log histories."""

    def setUp(self):
        super(TestGetClusterhostLogHistories, self).setUp()

    def tearDown(self):
        super(TestGetClusterhostLogHistories, self).tearDown()

    def test_get_clusterhost_log_histories(self):
        logs = cluster.get_clusterhost_log_histories(
            self.user_object,
            self.clusterhost_id[0],
        )
        result = []
        for log in logs:
            result.append(log['filename'])
        for item in result:
            self.assertEqual(result, ['log_file1', 'log_file2'])


class TestGetClusterHostLogHistory(ClusterTestCase):
    """Test get cluster host log history."""

    def setUp(self):
        super(TestGetClusterHostLogHistory, self).setUp()

    def tearDown(self):
        super(TestGetClusterHostLogHistory, self).tearDown()

    def test_get_cluster_host_log_history(self):
        log = cluster.get_cluster_host_log_history(
            self.user_object,
            self.cluster_id,
            self.host_id[0],
            'log_file1'
        )
        self.assertEqual(log['filename'], 'log_file1')


class TestGetClusterhostLogHistory(ClusterTestCase):
    """Test get clusterhost log history."""

    def setUp(self):
        super(TestGetClusterhostLogHistory, self).setUp()

    def tearDown(self):
        super(TestGetClusterhostLogHistory, self).tearDown()

    def test_get_clusterhost_log_history(self):
        log = cluster.get_clusterhost_log_history(
            self.user_object,
            self.clusterhost_id[0],
            'log_file1'
        )
        self.assertEqual(log['filename'], 'log_file1')


class TestUpdateClusterHostLogHistory(ClusterTestCase):
    """Test update cluster host log history."""

    def setUp(self):
        super(TestUpdateClusterHostLogHistory, self).setUp()

    def tearDown(self):
        super(TestUpdateClusterHostLogHistory, self).tearDown()

    def test_update_cluster_host_log_history(self):
        cluster.update_cluster_host_log_history(
            self.user_object,
            self.cluster_id,
            self.host_id[0],
            'log_file1',
            severity='WARNING',
            message='test update cluster host log history.'
        )
        update_log = cluster.get_cluster_host_log_history(
            self.user_object,
            self.cluster_id,
            self.host_id[0],
            'log_file1'
        )
        self.assertEqual(update_log['severity'], 'WARNING')


class TestUpdateClusterhostLogHistory(ClusterTestCase):
    """Test update clusterhost log history."""

    def setUp(self):
        super(TestUpdateClusterhostLogHistory, self).setUp()

    def tearDown(self):
        super(TestUpdateClusterhostLogHistory, self).tearDown()

    def test_update_clusterhost_log_history(self):
        cluster.update_clusterhost_log_history(
            self.user_object,
            self.clusterhost_id[0],
            'log_file1',
            severity='WARNING',
            message='test update clusterhost log history.'
        )
        update_log = cluster.get_clusterhost_log_history(
            self.user_object,
            self.clusterhost_id[0],
            'log_file1'
        )
        self.assertEqual(update_log['severity'], 'WARNING')


class TestAddClusterhostLogHistory(ClusterTestCase):
    """Test add clusterhost log history."""

    def setUp(self):
        super(TestAddClusterhostLogHistory, self).setUp()

    def tearDown(self):
        super(TestAddClusterhostLogHistory, self).tearDown()

    def test_add_clusterhost_log_history(self):
        cluster.add_clusterhost_log_history(
            self.user_object,
            self.clusterhost_id[0],
            filename='add_log_file'

        )
        logs = cluster.get_clusterhost_log_histories(
            self.user_object,
            self.clusterhost_id[0]
        )
        result = []
        for log in logs:
            result.append(log['filename'])
        self.assertIn('add_log_file', result)


class TestAddClusterHostLogHistory(ClusterTestCase):
    """Test add cluster host log history."""

    def setUp(self):
        super(TestAddClusterHostLogHistory, self).setUp()

    def tearDown(self):
        super(TestAddClusterHostLogHistory, self).tearDown()

    def test_add_cluster_host_log_history(self):
        cluster.add_cluster_host_log_history(
            self.user_object,
            self.cluster_id,
            self.host_id[0],
            filename='add_log_file'
        )
        logs = cluster.get_cluster_host_log_histories(
            self.user_object,
            self.cluster_id,
            self.host_id[0]
        )
        result = []
        for log in logs:
            result.append(log['filename'])
        self.assertIn('add_log_file', result)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
