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

    def test_host_no_name(self):
        with database.session() as session:
            cluster = model.Cluster()
            cluster.hosts = [model.ClusterHost()]
            session.add(cluster)

        with database.session() as session:
            hosts = session.query(model.ClusterHost).all()
            self.assertEqual(len(hosts), 1)
            self.assertIsNotNone(hosts[0].hostname)
            self.assertFalse(hosts[0].hostname == '')

    def test_host_empty_name(self):
        with database.session() as session:
            cluster = model.Cluster()
            cluster.hosts = [model.ClusterHost(hostname='')]
            session.add(cluster)

        with database.session() as session:
            hosts = session.query(model.ClusterHost).all()
            self.assertEqual(len(hosts), 1)
            self.assertIsNotNone(hosts[0].hostname)
            self.assertFalse(hosts[0].hostname == '')

    def test_host_name_unique(self):
        def _call():
            with database.session() as session:
                cluster = model.Cluster(name='cluster1')
                cluster.hosts = [
                    model.ClusterHost(hostname='host1'),
                    model.ClusterHost(hostname='host1')
                ]
                session.add(cluster)

        self.assertRaises(sqlalchemy.exc.IntegrityError, _call)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
