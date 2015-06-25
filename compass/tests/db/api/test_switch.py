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
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from base import BaseTest
from compass.db.api import database
from compass.db.api import switch
from compass.db.api import user as user_api
from compass.db import exception
from compass.utils import flags
from compass.utils import logsetting


class TestGetSwitch(BaseTest):
    """Test get switch."""

    def setUp(self):
        super(TestGetSwitch, self).setUp()

    def tearDown(self):
        super(TestGetSwitch, self).tearDown()

    def test_get_switch(self):
        get_switch = switch.get_switch(
            1,
            user=self.user_object,
        )
        self.assertIsNotNone(get_switch)
        self.assertEqual(get_switch['ip'], '0.0.0.0')


class TestAddSwitch(BaseTest):
    """Test add switch."""

    def setUp(self):
        super(TestAddSwitch, self).setUp()

    def tearDown(self):
        super(TestAddSwitch, self).tearDown()

    def test_add_switch(self):
        add_switch = switch.add_switch(
            ip='2887583784',
            user=self.user_object,
        )
        expected = '172.29.8.40'
        self.assertEqual(expected, add_switch['ip'])

    def test_add_switch_position_args(self):
        add_switch = switch.add_switch(
            True,
            '2887583784',
            user=self.user_object,
        )
        expected = '172.29.8.40'
        self.assertEqual(expected, add_switch['ip'])

    def test_add_switch_session(self):
        with database.session() as session:
            add_switch = switch.add_switch(
                ip='2887583784',
                user=self.user_object,
                session=session
            )
        expected = '172.29.8.40'
        self.assertEqual(expected, add_switch['ip'])


class TestAddSwitches(BaseTest):
    """Test add switches."""

    def setUp(self):
        super(TestAddSwitches, self).setUp()

    def tearDown(self):
        super(TestAddSwitches, self).tearDown()

    def test_add_switches(self):
        data = [
            {
                'ip': '172.29.8.30',
                'vendor': 'Huawei',
                'credentials': {
                    "version": "2c",
                    "community": "public"
                }
            }, {
                'ip': '172.29.8.40'
            }, {
                'ip': '172.29.8.40'
            }
        ]
        switches = switch.add_switches(
            data=data,
            user=self.user_object
        )
        ip = []
        for item in switches['switches']:
            ip.append(item['ip'])
        fail_ip = []
        for item in switches['fail_switches']:
            fail_ip.append(item['ip'])
        expected = ['172.29.8.30', '172.29.8.40']
        expected_fail = ['172.29.8.40']
        for expect in expected:
            self.assertIn(expect, ip)
        for expect_fail in expected_fail:
            self.assertIn(expect_fail, fail_ip)


class TestListSwitches(BaseTest):
    """Test list switch."""

    def setUp(self):
        super(TestListSwitches, self).setUp()

    def tearDown(self):
        super(TestListSwitches, self).tearDown()

    def test_list_switches_ip_int_invalid(self):
        switch.add_switch(
            ip='2887583784',
            user=self.user_object,
        )
        list_switches = switch.list_switches(
            ip_int='test',
            user=self.user_object,
        )
        self.assertEqual(list_switches, [])

    def test_list_switches_with_ip_int(self):
        switch.add_switch(
            ip='2887583784',
            user=self.user_object,
        )
        list_switches = switch.list_switches(
            ip_int='2887583784',
            user=self.user_object,
        )
        expected = '172.29.8.40'
        self.assertIsNotNone(list_switches)
        self.assertEqual(expected, list_switches[0]['ip'])

    def test_list_switches(self):
        switch.add_switch(
            ip='2887583784',
            user=self.user_object,
        )
        list_switches = switch.list_switches(
            user=self.user_object
        )
        expected = '172.29.8.40'
        self.assertIsNotNone(list_switches)
        self.assertEqual(expected, list_switches[0]['ip'])


class TestDelSwitch(BaseTest):
    """Test delete switch."""

    def setUp(self):
        super(TestDelSwitch, self).setUp()

    def tearDown(self):
        super(TestDelSwitch, self).tearDown()

    def test_del_switch(self):
        switch.del_switch(
            1,
            user=self.user_object,
        )
        del_switch = switch.list_switches(
            user=self.user_object
        )
        self.assertEqual([], del_switch)


class TestUpdateSwitch(BaseTest):
    """Test update switch."""

    def setUp(self):
        super(TestUpdateSwitch, self).setUp()

    def tearDown(self):
        super(TestUpdateSwitch, self).tearDown()

    def test_update_switch(self):
        switch.update_switch(
            1,
            user=self.user_object,
            vendor='test_update'
        )
        update_switch = switch.get_switch(
            1,
            user=self.user_object,
        )
        expected = 'test_update'
        self.assertEqual(expected, update_switch['vendor'])


class TestPatchSwitch(BaseTest):
    """Test patch switch."""

    def setUp(self):
        super(TestPatchSwitch, self).setUp()

    def tearDown(self):
        super(TestPatchSwitch, self).tearDown()

    def test_patch_switch(self):
        switch.patch_switch(
            1,
            user=self.user_object,
            credentials={
                'version': '2c',
                'community': 'public'
            }
        )
        patch_switch = switch.get_switch(
            1,
            user=self.user_object,
        )
        expected = {
            'credentials': {
                'version': '2c',
                'community': 'public'
            }
        }
        self.assertTrue(
            all(item in patch_switch.items() for item in expected.items())
        )


class TestListSwitchFilters(BaseTest):
    """Test list switch filters."""

    def setUp(self):
        super(TestListSwitchFilters, self).setUp()

    def tearDown(self):
        super(TestListSwitchFilters, self).tearDown()

    def test_list_switch_filters(self):
        list_switch_filters = switch.list_switch_filters(
            user=self.user_object
        )
        expected = {
            'ip': '0.0.0.0',
            'id': 1,
            'filters': 'allow ports all',
        }
        self.assertIsNotNone(list_switch_filters)
        self.assertTrue(
            all(item in list_switch_filters[0].items()
                for item in expected.items()))


class TestGetSwitchFilters(BaseTest):
    """Test get switch filter."""

    def setUp(self):
        super(TestGetSwitchFilters, self).setUp()

    def tearDown(self):
        super(TestGetSwitchFilters, self).tearDown()

    def test_get_swtich_filters(self):
        get_switch_filter = switch.get_switch_filters(
            1,
            user=self.user_object,
        )
        expected = {
            'ip': '0.0.0.0',
            'id': 1,
            'filters': 'allow ports all',
        }
        self.assertIsNotNone(get_switch_filter)
        self.assertTrue(
            all(item in get_switch_filter.items()
                for item in expected.items()))


class TestUpdateSwitchFilters(BaseTest):
    """Test update a switch filter."""

    def setUp(self):
        super(TestUpdateSwitchFilters, self).setUp()

    def tearDown(self):
        super(TestUpdateSwitchFilters, self).tearDown()

    def test_update_switch_filters(self):
        switch.update_switch_filters(
            1,
            user=self.user_object,
            machine_filters=[
                {
                    'filter_type': 'allow'
                }
            ]
        )
        update_switch_filters = switch.get_switch_filters(
            1,
            user=self.user_object,
        )
        expected = {
            'filters': 'allow'
        }
        self.assertTrue(
            all(item in update_switch_filters.items()
                for item in expected.items())
        )


class TestPatchSwitchFilter(BaseTest):
    """Test patch a switch filter."""

    def setUp(self):
        super(TestPatchSwitchFilter, self).setUp()

    def tearDown(self):
        super(TestPatchSwitchFilter, self).tearDown()

    def test_patch_switch_filter(self):
        switch.add_switch(
            ip='2887583784',
            user=self.user_object,
        )
        switch.patch_switch_filter(
            2,
            user=self.user_object,
            machine_filters=[
                {
                    'filter_type': 'allow'
                }
            ]
        )
        patch_switch_filter = switch.get_switch_filters(
            2,
            user=self.user_object,
        )
        expected = {
            'filters': 'allow'
        }
        self.assertTrue(
            all(item in patch_switch_filter.items()
                for item in expected.items())
        )


class TestAddSwitchMachine(BaseTest):
    """Test add switch machine."""

    def setUp(self):
        super(TestAddSwitchMachine, self).setUp()

    def tearDown(self):
        super(TestAddSwitchMachine, self).tearDown()

    def test_add_switch_machine(self):
        add_switch_machine = switch.add_switch_machine(
            1,
            mac='28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        expected = '28:6e:d4:46:c4:25'
        self.assertEqual(expected, add_switch_machine['mac'])

    def test_add_switch_machine_position_args(self):
        add_switch_machine = switch.add_switch_machine(
            1,
            True,
            '28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        expected = '28:6e:d4:46:c4:25'
        self.assertEqual(expected, add_switch_machine['mac'])

    def test_add_switch_machine_session(self):
        with database.session() as session:
            add_switch_machine = switch.add_switch_machine(
                1,
                mac='28:6e:d4:46:c4:25',
                user=self.user_object,
                session=session,
                port='1'
            )
        expected = '28:6e:d4:46:c4:25'
        self.assertEqual(expected, add_switch_machine['mac'])


class TestAddSwitchMachines(BaseTest):
    """Test add switch machines."""
    def setUp(self):
        super(TestAddSwitchMachines, self).setUp()

    def tearDown(self):
        super(TestAddSwitchMachines, self).tearDown()

    def test_add_switch_machines(self):
        data = [{
            'switch_ip': '0.0.0.0',
            'mac': '1a:2b:3c:4d:5e:6f',
            'port': '100'
        }, {
            'switch_ip': '0.0.0.0',
            'mac': 'a1:b2:c3:d4:e5:f6',
            'port': '101'
        }, {
            'switch_ip': '0.0.0.0',
            'mac': 'a1:b2:c3:d4:e5:f6',
            'port': '103'
        }, {
            'switch_ip': '0.0.0.0',
            'mac': 'a1:b2:c3:d4:e5:f6',
            'port': '101'
        }]
        add_switch_machines = switch.add_switch_machines(
            data=data, user=self.user_object
        )
        mac = []
        failed_mac = []
        for switch_machine in add_switch_machines['switches_machines']:
            mac.append(switch_machine['mac'])
        for failed_switch in add_switch_machines['fail_switches_machines']:
            failed_mac.append(failed_switch['mac'])
        expect = ['1a:2b:3c:4d:5e:6f', 'a1:b2:c3:d4:e5:f6']
        expect_fail = ['a1:b2:c3:d4:e5:f6']
        for item in expect:
            self.assertIn(item, mac)
        for item in expect_fail:
            self.assertIn(item, failed_mac)


class TestListSwitchMachines(BaseTest):
    """Test get switch machines."""

    def setUp(self):
        super(TestListSwitchMachines, self).setUp()

    def tearDown(self):
        super(TestListSwitchMachines, self).tearDown()

    def test_list_switch_machines(self):
        switch.add_switch(
            ip='2887583784',
            user=self.user_object,
        )
        switch.add_switch_machine(
            2,
            mac='28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        list_switch_machines = switch.list_switch_machines(
            2,
            user=self.user_object,
        )
        expected = {
            'switch_id': 2,
            'id': 1,
            'mac': '28:6e:d4:46:c4:25',
            'switch_ip': '172.29.8.40',
            'machine_id': 1,
            'port': '1',
            'switch_machine_id': 1
        }
        self.assertIsNotNone(list_switch_machines)
        self.assertTrue(
            all(item in list_switch_machines[0].items()
                for item in expected.items()))


class TestListSwitchmachines(BaseTest):
    """Test list switch machines."""

    def setUp(self):
        super(TestListSwitchmachines, self).setUp()

    def tearDown(self):
        super(TestListSwitchmachines, self).tearDown()

    def test_list_switch_machines_with_ip_int(self):
        switch.add_switch(
            ip='2887583784',
            user=self.user_object,
        )
        switch.add_switch_machine(
            2,
            mac='28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        list_switch_machines = switch.list_switchmachines(
            switch_ip_int='2887583784',
            user=self.user_object,
        )
        expected = {'switch_ip': '172.29.8.40'}
        self.assertTrue(
            all(item in list_switch_machines[0].items()
                for item in expected.items()))

    def test_list_switch_machines_ip_invalid(self):
        switch.add_switch(
            ip='2887583784',
            user=self.user_object,
        )
        switch.add_switch_machine(
            2,
            mac='28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        list_switch_machines = switch.list_switchmachines(
            switch_ip_int='test',
            user=self.user_object,
        )
        self.assertEqual(list_switch_machines, [])

    def test_list_switch_machines_without_ip(self):
        switch.add_switch(
            ip='2887583784',
            user=self.user_object,
        )
        switch.add_switch_machine(
            2,
            mac='28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        list_switch_machines = switch.list_switchmachines(
            user=self.user_object
        )
        expected = {'switch_ip': '172.29.8.40'}
        self.assertTrue(
            all(item in list_switch_machines[0].items()
                for item in expected.items()))


class TestListSwitchMachinesHosts(BaseTest):
    """Test get switch machines hosts."""

    def setUp(self):
        super(TestListSwitchMachinesHosts, self).setUp()

    def tearDown(self):
        super(TestListSwitchMachinesHosts, self).tearDown()

    def test_list_hosts(self):
        switch.add_switch(
            ip='2887583784',
            user=self.user_object,
        )
        switch.add_switch_machine(
            2,
            mac='28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        list_hosts = switch.list_switch_machines_hosts(
            2,
            user=self.user_object,
        )
        expected = {
            'switch_id': 2,
            'id': 1,
            'mac': '28:6e:d4:46:c4:25',
            'switch_ip': '172.29.8.40',
            'machine_id': 1,
            'port': '1',
            'switch_machine_id': 1
        }
        self.assertTrue(
            all(item in list_hosts[0].items()
                for item in expected.items()))


class TestListSwitchmachinesHosts(BaseTest):
    """Test list switch machines hosts."""

    def setUp(self):
        super(TestListSwitchmachinesHosts, self).setUp()

    def tearDown(self):
        super(TestListSwitchmachinesHosts, self).tearDown()

    def test_list_hosts_with_ip_int(self):
        switch.add_switch(
            ip='2887583784',
            user=self.user_object,
        )
        switch.add_switch_machine(
            2,
            mac='28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        list_hosts = switch.list_switchmachines_hosts(
            switch_ip_int='2887583784',
            user=self.user_object,
        )
        expected = {'switch_ip': '172.29.8.40'}
        self.assertTrue(
            all(item in list_hosts[0].items()
                for item in expected.items()))

    def test_list_hosts_ip_invalid(self):
        switch.add_switch(
            ip='2887583784',
            user=self.user_object,
        )
        switch.add_switch_machine(
            2,
            mac='28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        list_hosts = switch.list_switchmachines_hosts(
            switch_ip_int='test',
            user=self.user_object,
        )
        self.assertEqual(list_hosts, [])

    def test_list_hosts_without_ip(self):
        switch.add_switch(
            ip='2887583784',
            user=self.user_object,
        )
        switch.add_switch_machine(
            2,
            mac='28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        list_hosts = switch.list_switchmachines_hosts(
            user=self.user_object
        )
        expected = {'switch_ip': '172.29.8.40'}
        self.assertTrue(
            all(item in list_hosts[0].items()
                for item in expected.items()))
        self.assertIsNotNone(list_hosts)


class TestGetSwitchMachine(BaseTest):
    """Test get a switch machines."""

    def setUp(self):
        super(TestGetSwitchMachine, self).setUp()

    def tearDown(self):
        super(TestGetSwitchMachine, self).tearDown()

    def test_get_switch_machine(self):
        switch.add_switch(
            ip='2887583784',
            user=self.user_object,
        )
        switch.add_switch_machine(
            2,
            mac='28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        get_switch_machine = switch.get_switch_machine(
            2,
            1,
            user=self.user_object,
        )
        self.assertIsNotNone(get_switch_machine)
        self.assertEqual(get_switch_machine['mac'], '28:6e:d4:46:c4:25')


class TestGetSwitchmachine(BaseTest):
    """Test get a switch machine."""

    def setUp(self):
        super(TestGetSwitchmachine, self).setUp()

    def tearDown(self):
        super(TestGetSwitchmachine, self).tearDown()

    def test_get_switchmachine(self):
        switch.add_switch_machine(
            1,
            mac='28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        get_switchmachine = switch.get_switchmachine(
            1,
            user=self.user_object,
        )
        self.assertIsNotNone(get_switchmachine)
        self.assertEqual(get_switchmachine['mac'], '28:6e:d4:46:c4:25')


class TestUpdateSwitchMachine(BaseTest):
    """Test update switch machine."""

    def setUp(self):
        super(TestUpdateSwitchMachine, self).setUp()

    def tearDown(self):
        super(TestUpdateSwitchMachine, self).tearDown()

    def test_update_switch_machine(self):
        switch.add_switch_machine(
            1,
            mac='28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        switch.update_switch_machine(
            1,
            1,
            tag='test_tag',
            user=self.user_object,
        )
        update_switch_machine = switch.list_switch_machines(
            1,
            user=self.user_object,
        )
        expected = {
            'switch_id': 1,
            'id': 1,
            'mac': '28:6e:d4:46:c4:25',
            'tag': 'test_tag',
            'switch_ip': '0.0.0.0',
            'machine_id': 1,
            'port': '1',
            'switch_machine_id': 1
        }
        self.assertTrue(
            all(item in update_switch_machine[0].items()
                for item in expected.items())
        )


class TestUpdateSwitchmachine(BaseTest):
    """Test update switch machine."""

    def setUp(self):
        super(TestUpdateSwitchmachine, self).setUp()

    def tearDown(self):
        super(TestUpdateSwitchmachine, self).tearDown()

    def test_update_switchmachine(self):
        switch.add_switch_machine(
            1,
            mac='28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        switch.update_switchmachine(
            1,
            location='test_location',
            user=self.user_object,
        )
        update_switchmachine = switch.list_switchmachines(
            user=self.user_object,
        )
        expected = {
            'switch_id': 1,
            'id': 1,
            'mac': '28:6e:d4:46:c4:25',
            'location': 'test_location',
            'switch_ip': '0.0.0.0',
            'machine_id': 1,
            'port': '1',
            'switch_machine_id': 1
        }
        self.assertTrue(
            all(item in update_switchmachine[0].items()
                for item in expected.items())
        )


class TestPatchSwitchMachine(BaseTest):
    """Test patch switch machine."""

    def setUp(self):
        super(TestPatchSwitchMachine, self).setUp()

    def tearDown(self):
        super(TestPatchSwitchMachine, self).tearDown()

    def test_patch_switch_machine(self):
        switch.add_switch_machine(
            1,
            mac='28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        switch.patch_switch_machine(
            1,
            1,
            user=self.user_object,
            tag={
                'patched_tag': 'test_patched_tag'
            }
        )
        switch_patch_switch_machine = switch.list_switch_machines(
            1,
            user=self.user_object,
        )
        expected = {'tag': {
            'patched_tag': 'test_patched_tag'}
        }
        self.assertTrue(
            all(item in switch_patch_switch_machine[0].items()
                for item in expected.items())
        )


class TestPatchSwitchmachine(BaseTest):
    """Test patch switch machine."""

    def setUp(self):
        super(TestPatchSwitchmachine, self).setUp()

    def tearDown(self):
        super(TestPatchSwitchmachine, self).tearDown()

    def test_patch_switchmachine(self):
        switch.add_switch_machine(
            1,
            mac='28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        switch.patch_switchmachine(
            1,
            user=self.user_object,
            location={
                'patched_location': 'test_location'
            }
        )
        patch_switchmachine = switch.list_switchmachines(
            user=self.user_object
        )
        expected = {'location': {
            'patched_location': 'test_location'}
        }
        self.assertTrue(
            all(item in patch_switchmachine[0].items()
                for item in expected.items())
        )


class TestDelSwitchMachine(BaseTest):
    """Test delete switch machines."""

    def setUp(self):
        super(TestDelSwitchMachine, self).setUp()

    def tearDown(self):
        super(TestDelSwitchMachine, self).tearDown()

    def test_del_switch_machine(self):
        switch.add_switch_machine(
            1,
            mac='28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        switch.del_switch_machine(
            1,
            1,
            user=self.user_object,
        )
        del_switch_machine = switch.list_switch_machines(
            1,
            user=self.user_object,
        )
        self.assertEqual([], del_switch_machine)


class TestDelSwitchmachine(BaseTest):
    """Test delete switch machines."""

    def setUp(self):
        super(TestDelSwitchmachine, self).setUp()

    def tearDown(self):
        super(TestDelSwitchmachine, self).tearDown()

    def test_switchmachine(self):
        switch.add_switch_machine(
            1,
            mac='28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        switch.del_switchmachine(
            1,
            user=self.user_object,
        )
        del_switchmachine = switch.list_switchmachines(
            user=self.user_object
        )
        self.assertEqual([], del_switchmachine)


class TestUpdateSwitchMachines(BaseTest):
    """Test update switch machines."""

    def setUp(self):
        super(TestUpdateSwitchMachines, self).setUp()

    def tearDown(self):
        super(TestUpdateSwitchMachines, self).tearDown()

    def test_update_switch_machines_remove(self):
        switch.add_switch(
            ip='2887583784',
            user=self.user_object,
        )
        switch.add_switch_machine(
            2,
            mac='28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        switch.update_switch_machines(
            2,
            remove_machines=1,
            user=self.user_object,
        )
        update_remove = switch.list_switch_machines(
            2,
            user=self.user_object,
        )
        self.assertEqual([], update_remove)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
