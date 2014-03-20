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

"""test util module.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import os
import sqlalchemy.exc
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from compass.db import database
from compass.db import model
from compass.utils import flags
from compass.utils import logsetting


class TestModel(unittest2.TestCase):
    """Test database model."""

    def setUp(self):
        super(TestModel, self).setUp()
        logsetting.init()
        database.init('sqlite://')
        database.create_db()

    def tearDown(self):
        database.drop_db()
        super(TestModel, self).tearDown()

    def test_switch_config(self):
        with database.session() as session:
            session.add(model.SwitchConfig(
                ip='10.145.88.1', filter_port='123'
            ))

        with database.session() as session:
            switch_configs = session.query(model.SwitchConfig).all()
            self.assertEqual(len(switch_configs), 1)
            self.assertEqual(switch_configs[0].ip, '10.145.88.1')
            self.assertEqual(switch_configs[0].filter_port, '123')

    def test_switch_config_ip_filterport_unique(self):
        def _call():
            with database.session() as session:
                session.add(model.SwitchConfig(
                    ip='10.145.88.1', filter_port='123'))
                session.add(model.SwitchConfig(
                    ip='10.145.88.1', filter_port='123'))

        self.assertRaises(sqlalchemy.exc.IntegrityError, _call)

    def test_switch(self):
        with database.session() as session:
            switch = model.Switch(ip='10.145.88.1')
            switch.credential = {
                'version': 'v2c', 'community': 'public'
            }
            switch.vendor = 'huawei'
            session.add(switch)

        with database.session() as session:
            switches = session.query(model.Switch).all()
            self.assertEqual(len(switches), 1)
            self.assertEqual(switches[0].ip, '10.145.88.1')
            self.assertEqual(
                switches[0].credential, {
                    'version': 'v2c', 'community': 'public'
                }
            )
            self.assertEqual(switches[0].vendor, 'huawei')

    def test_switch_ip_unique(self):
        def _call():
            with database.session() as session:
                session.add(model.Switch(ip='10.145.88.1'))
                session.add(model.Switch(ip='10.145.88.1'))

        self.assertRaises(sqlalchemy.exc.IntegrityError, _call)

    def test_machine_no_switch(self):
        with database.session() as session:
            session.add(model.Machine(
                mac='00:00:00:01:02:03',
                port='123', vlan=100))

        with database.session() as session:
            machines = session.query(model.Machine).all()
            self.assertEqual(len(machines), 1)
            self.assertEqual(machines[0].mac, '00:00:00:01:02:03')
            self.assertEqual(machines[0].port, '123')
            self.assertEqual(machines[0].vlan, 100)
            self.assertIsNone(machines[0].switch)

    def test_machine_with_switch(self):
        with database.session() as session:
            switch = model.Switch(ip='192.168.1.1')
            switch.machines.append(
                model.Machine(
                    mac='00:00:00:01:02:03',
                    port='123', vlan=100)
            )
            session.add(switch)

        with database.session() as session:
            machines = session.query(model.Machine).all()
            self.assertEqual(len(machines), 1)
            self.assertEqual(machines[0].mac, '00:00:00:01:02:03')
            self.assertEqual(machines[0].port, '123')
            self.assertEqual(machines[0].vlan, 100)
            self.assertIsNotNone(machines[0].switch)

    def test_machine_mac_switch_vlan_unique(self):
        def _call():
            with database.session() as session:
                machine1 = model.Machine(
                    mac='00:00:00:01:02:03',
                    port='123',
                    vlan=100
                )
                machine2 = model.Machine(
                    mac='00:00:00:01:02:03',
                    port='123',
                    vlan=100
                )
                switch = model.Switch(ip='192.168.1.1')
                switch.machines = [machine1, machine2]
                session.add(switch)

        self.assertRaises(sqlalchemy.exc.IntegrityError, _call)

    def test_machine_owned_by_one_switch(self):
        with database.session() as session:
            switch1 = model.Switch(ip='192.168.1.1')
            switch2 = model.Switch(ip='192.168.1.2')
            machine = model.Machine(
                mac='00:00:00:01:02:03',
                port='123',
                vlan=100
            )
            switch1.machines = [machine]
            switch2.machines = [machine]
            session.add(switch1)
            session.add(switch2)

        with database.session() as session:
            machine = session.query(model.Machine).first()
            self.assertEqual(machine.switch.ip, '192.168.1.2')

    def test_del_switch(self):
        with database.session() as session:
            switch = model.Switch(ip='192.68.1.1')
            switch.machines = [model.Machine(
                mac='00:00:00:01:02:03',
                port='123',
                vlan=100
            )]
            session.add(switch)

        with database.session() as session:
            session.query(model.Switch).delete()

        with database.session() as session:
            machines = session.query(model.Machine).all()
            self.assertEqual(len(machines), 1)
            self.assertEqual(machines[0].mac, '00:00:00:01:02:03')
            self.assertIsNone(machines[0].switch)

    def test_del_machine(self):
        with database.session() as session:
            switch = model.Switch(ip='192.68.1.1')
            switch.machines = [model.Machine(
                mac='00:00:00:01:02:03',
                port='123',
                vlan=100
            )]
            session.add(switch)

        with database.session() as session:
            session.query(model.Machine).delete()

        with database.session() as session:
            switch = session.query(model.Switch).first()
            self.assertEqual(switch.machines.count(), 0)

    def test_cluster_no_name(self):
        with database.session() as session:
            session.add(model.Cluster())

        with database.session() as session:
            clusters = session.query(model.Cluster).all()
            self.assertEqual(len(clusters), 1)
            self.assertIsNotNone(clusters[0].name)
            self.assertFalse(clusters[0].name == '')

    def test_cluster_empty_name(self):
        with database.session() as session:
            session.add(model.Cluster(name=''))

        with database.session() as session:
            clusters = session.query(model.Cluster).all()
            self.assertEqual(len(clusters), 1)
            self.assertIsNotNone(clusters[0].name)
            self.assertFalse(clusters[0].name == '')

    def test_cluster_name_unique(self):
        def _call():
            with database.session() as session:
                session.add(model.Cluster(name='cluster1'))
                session.add(model.Cluster(name='cluster1'))

        self.assertRaises(sqlalchemy.exc.IntegrityError, _call)

    def test_adapter(self):
        with database.session() as session:
            session.add(model.Adapter(
                name='CentOS_openstack',
                os='CentOS', target_system='Openstack'))

        with database.session() as session:
            adapters = session.query(model.Adapter).all()
            self.assertEqual(len(adapters), 1)
            self.assertEqual(adapters[0].name, 'CentOS_openstack')
            self.assertEqual(adapters[0].os, 'CentOS')
            self.assertEqual(adapters[0].target_system, 'Openstack')

    def test_adapter_name_unique(self):
        def _call():
            with database.session() as session:
                session.add(model.Adapter(
                    name='CentOS_openstack',
                    os='CentOS6.4', target_system='Openstack1'))
                session.add(model.Adapter(
                    name='CentOS_openstack',
                    os='CentOSi6.5', target_system='Openstack2'))

        self.assertRaises(sqlalchemy.exc.IntegrityError, _call)

    def test_adapter_os_target_system_unique(self):
        def _call():
            with database.session() as session:
                session.add(model.Adapter(
                    name='CentOS_openstack1',
                    os='CentOS', target_system='Openstack'))
                session.add(model.Adapter(
                    name='CentOS_openstack2',
                    os='CentOS', target_system='Openstack'))

        self.assertRaises(sqlalchemy.exc.IntegrityError, _call)

    def test_cluster_adapter(self):
        with database.session() as session:
            adapter = model.Adapter(
                name='CentOS_openstack',
                os='CentOS',
                target_system='openstack')
            cluster = model.Cluster(
                name='cluster1')
            cluster.adapter = adapter
            session.add(cluster)

        with database.session() as session:
            adapter = session.query(model.Adapter).first()
            self.assertEqual(adapter.clusters.count(), 1)

    def test_cluster_del(self):
        with database.session() as session:
            adapter = model.Adapter(
                name='CentOS_openstack',
                os='CentOS',
                target_system='openstack')
            cluster = model.Cluster(
                name='cluster1')
            cluster.adapter = adapter
            session.add(cluster)

        with database.session() as session:
            session.query(model.Cluster).delete()

        with database.session() as session:
            adapters = session.query(model.Adapter).all()
            self.assertEqual(len(adapters), 1)

    def test_adapter_del(self):
        with database.session() as session:
            adapter = model.Adapter(
                name='CentOS_openstack',
                os='CentOS',
                target_system='openstack')
            cluster = model.Cluster(
                name='cluster1')
            cluster.adapter = adapter
            session.add(cluster)

        with database.session() as session:
            session.query(model.Adapter).delete()

        with database.session() as session:
            cluster = session.query(model.Cluster).first()
            self.assertIsNone(cluster.adapter)

    def test_cluster_config(self):
        with database.session() as session:
            cluster = model.Cluster(name='cluster1')
            cluster.security = {
                'user': 'abc',
                'password': '123'
            }
            cluster.networking = {
                'interface': 'eth0',
            }
            cluster.partition = '/tmp 20%'
            session.add(cluster)

        with database.session() as session:
            cluster = session.query(model.Cluster).first()
            self.assertDictContainsSubset(
                {
                    'clustername': 'cluster1',
                    'security': {'user': 'abc', 'password': '123'},
                    'networking': {'interface': 'eth0'},
                    'partition': '/tmp 20%'
                }, cluster.config)

    def test_cluster_config_set(self):
        with database.session() as session:
            cluster = model.Cluster(name='cluster1')
            cluster.config = {
                'security': {
                    'user': 'abc',
                    'password': '123'
                },
                'networking': {
                    'interface': 'eth0',
                },
                'partition': '/tmp 20%'
            }
            session.add(cluster)

        with database.session() as session:
            cluster = session.query(model.Cluster).first()
            self.assertEqual(
                cluster.security,
                {'user': 'abc', 'password': '123'})
            self.assertEqual(
                cluster.networking,
                {'interface': 'eth0'})
            self.assertEqual(
                cluster.partition,
                '/tmp 20%')

    def test_clusterhost(self):
        with database.session() as session:
            host = model.ClusterHost(
                hostname='host1')
            host.cluster = model.Cluster(
                name='cluster1')
            host.machine = model.Machine(
                mac='00:00:00:01:02:03',
                port='123',
                vlan=100)
            host.machine.switch = model.Switch(
                ip='192.168.1.1')
            session.add(host)

        with database.session() as session:
            host = session.query(model.ClusterHost).first()
            self.assertEqual(host.cluster.name, 'cluster1')
            self.assertEqual(host.machine.mac, '00:00:00:01:02:03')
            self.assertEqual(host.machine.switch.ip, '192.168.1.1')

    def test_no_hostname(self):
        with database.session() as session:
            cluster = model.Cluster()
            cluster.hosts = [model.ClusterHost()]
            session.add(cluster)

        with database.session() as session:
            hosts = session.query(model.ClusterHost).all()
            self.assertEqual(len(hosts), 1)
            self.assertIsNotNone(hosts[0].hostname)
            self.assertFalse(hosts[0].hostname == '')

    def test_hostname_empty(self):
        with database.session() as session:
            cluster = model.Cluster()
            cluster.hosts = [model.ClusterHost(hostname='')]
            session.add(cluster)

        with database.session() as session:
            hosts = session.query(model.ClusterHost).all()
            self.assertEqual(len(hosts), 1)
            self.assertIsNotNone(hosts[0].hostname)
            self.assertFalse(hosts[0].hostname == '')

    def test_hostname_cluster_unique(self):
        def _call():
            with database.session() as session:
                cluster = model.Cluster(name='cluster1')
                cluster.hosts = [
                    model.ClusterHost(hostname='host1'),
                    model.ClusterHost(hostname='host1')
                ]
                session.add(cluster)

        self.assertRaises(sqlalchemy.exc.IntegrityError, _call)

    def test_clusterhost_delete_cluster(self):
        with database.session() as session:
            cluster = model.Cluster(name='cluster1')
            cluster.hosts = [
                model.ClusterHost(hostname='host1')
            ]
            session.add(cluster)

        with database.session() as session:
            session.query(model.Cluster).delete()

        with database.session() as session:
            host = session.query(model.ClusterHost).first()
            self.assertIsNone(host.cluster)

    def test_clusterhost_delete_machine(self):
        with database.session() as session:
            host = model.ClusterHost(hostname='host1')
            host.machine = model.Machine(
                mac='00:00:00:01:02:03',
                port='123',
                vlan=100)
            session.add(host)

        with database.session() as session:
            session.query(model.Machine).delete()

        with database.session() as session:
            host = session.query(model.ClusterHost).first()
            self.assertIsNone(host.machine)

    def test_clusterhost_delete_host(self):
        with database.session() as session:
            cluster = model.Cluster(name='cluster1')
            host = model.ClusterHost(hostname='host1')
            cluster.hosts = [host]
            host.machine = model.Machine(
                mac='00:00:00:01:02:03',
                port='123',
                vlan=100)
            session.add(cluster)

        with database.session() as session:
            session.query(model.ClusterHost).delete()

        with database.session() as session:
            cluster = session.query(model.Cluster).first()
            self.assertEqual(cluster.hosts.count(), 0)
            machine = session.query(model.Machine).first()
            self.assertIsNone(machine.host)

    def test_host_config(self):
        with database.session() as session:
            cluster = model.Cluster(name='cluster1')
            host = model.ClusterHost(
                hostname='host1')
            host.machine = model.Machine(
                mac='00:00:00:01:02:03',
                port='123',
                vlan=100)
            host.machine.switch = model.Switch(
                ip='192.168.1.1')
            cluster.hosts = [host]
            host.config = {
                'networking': {
                    'interfaces': {
                        'management': {'ip': '192.168.1.100'}
                    }
                }
            }
            session.add(cluster)

        with database.session() as session:
            host = session.query(model.ClusterHost).first()
            self.assertDictContainsSubset(
                {
                    'hostname': 'host1',
                    'clustername': 'cluster1',
                    'networking': {
                        'interfaces': {
                            'management': {
                                'mac': '00:00:00:01:02:03',
                                'ip': '192.168.1.100'
                            }
                        }
                    },
                    'switch_port': '123',
                    'vlan': 100,
                    'switch_ip': '192.168.1.1'
                }, host.config)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
