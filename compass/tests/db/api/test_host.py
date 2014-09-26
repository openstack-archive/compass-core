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


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
