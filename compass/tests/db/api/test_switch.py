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

from base import BaseTest
from compass.db.api import database
from compass.db.api import switch
from compass.db.api import user as user_api
from compass.db import exception
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import setting_wrapper as setting


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


reload(setting)


class TestGetSwitch(BaseTest):
    """Test get switch."""

    def setUp(self):
        super(TestGetSwitch, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestGetSwitch, self).tearDown()

    def test_get_switch(self):
        get_switch = switch.get_switch(
            self.user_object,
            1
        )
        self.assertIsNotNone(get_switch)


class TestAddSwitch(BaseTest):
    """Test add switch."""

    def setUp(self):
        super(TestAddSwitch, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestAddSwitch, self).tearDown()

    def test_add_switch(self):
        add_switch = switch.add_switch(
            self.user_object,
            ip='2887583784'
        )
        expected = '172.29.8.40'
        self.assertEqual(expected, add_switch['ip'])


class TestListSwitches(BaseTest):
    """Test list switch."""

    def setUp(self):
        super(TestListSwitches, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestListSwitches, self).tearDown()

    def test_list_switches_ip_int_invalid(self):
        switch.add_switch(
            self.user_object,
            ip='2887583784'
        )
        list_switches = switch.list_switches(
            self.user_object,
            ip_int='test'
        )
        self.assertEqual(list_switches, [])

    def test_list_switches_with_ip_int(self):
        switch.add_switch(
            self.user_object,
            ip='2887583784'
        )
        list_switches = switch.list_switches(
            self.user_object,
            ip_int='2887583784'
        )
        expected = '2887583784'
        self.assertTrue(
            item in expected.items() for item in list_switches[0].items()
        )

    def test_list_switches(self):
        switch.add_switch(
            self.user_object,
            ip='2887583784'
        )
        list_switches = switch.list_switches(
            self.user_object
        )
        self.assertIsNotNone(list_switches)


class TestDelSwitch(BaseTest):
    """Test delete switch."""

    def setUp(self):
        super(TestDelSwitch, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestDelSwitch, self).tearDown()

    def test_del_switch(self):
        switch.del_switch(
            self.user_object,
            1
        )
        del_switch = switch.list_switches(
            self.user_object
        )
        self.assertEqual([], del_switch)


class TestUpdateSwitch(BaseTest):
    """Test update switch."""

    def setUp(self):
        super(TestUpdateSwitch, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestUpdateSwitch, self).tearDown()

    def test_update_switch(self):
        switch.update_switch(
            self.user_object,
            1,
            vendor='test_update'
        )
        update_switch = switch.get_switch(
            self.user_object,
            1
        )
        expected = 'test_update'
        self.assertEqual(expected, update_switch['vendor'])


class TestPatchSwitch(BaseTest):
    """Test patch switch."""

    def setUp(self):
        super(TestPatchSwitch, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestPatchSwitch, self).tearDown()

    def test_patch_switch(self):
        switch.patch_switch(
            self.user_object,
            1,
            patched_credentials={
                'version': '2c',
                'community': 'public'
            }
        )
        patch_switch = switch.get_switch(
            self.user_object,
            1
        )
        expected = {
            'version': '2c',
            'community': 'public'
        }
        self.assertTrue(
            item in expected.items() for item in patch_switch.items()
        )


class TestListSwitchFilters(BaseTest):
    """Test list switch filters."""

    def setUp(self):
        super(TestListSwitchFilters, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestListSwitchFilters, self).tearDown()

    def test_list_switch_filters(self):
        list_switch_filters = switch.list_switch_filters(
            self.user_object
        )
        self.assertIsNotNone(list_switch_filters)


class TestGetSwitchFilters(BaseTest):
    """Test get switch filter."""

    def setUp(self):
        super(TestGetSwitchFilters, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestGetSwitchFilters, self).tearDown()

    def test_get_swtich_filters(self):
        get_switch_filter = switch.get_switch_filters(
            self.user_object,
            1
        )
        self.assertIsNotNone(get_switch_filter)


class TestUpdateSwitchFilters(BaseTest):
    """Test update a switch filter."""

    def setUp(self):
        super(TestUpdateSwitchFilters, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestUpdateSwitchFilters, self).tearDown()

    def test_update_switch_filters(self):
        switch.update_switch_filters(
            self.user_object,
            1,
            filters=[
                {
                    'filter_name': 'test',
                    'filter_type': 'allow'
                }
            ]
        )
        update_switch_filters = switch.get_switch_filters(
            self.user_object,
            1
        )
        expected = {
            'filter_name': 'test',
            'filter_type': 'allow'
        }
        self.assertTrue(
            item in update_switch_filters[0].items()
            for item in expected.items()
        )


class TestPatchSwitchFilter(BaseTest):
    """Test patch a switch filter."""

    def setUp(self):
        super(TestPatchSwitchFilter, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestPatchSwitchFilter, self).tearDown()

    def test_patch_switch_filter(self):
        switch.patch_switch_filter(
            self.user_object,
            1,
            patched_filters=[
                {
                    'filter_name': 'test',
                    'filter_type': 'allow'
                }
            ]
        )
        patch_switch_filter = switch.get_switch_filters(
            self.user_object,
            1
        )
        expected = {
            'filter_name': 'test',
            'filter_type': 'allow'
        }
        self.assertTrue(
            item in patch_switch_filter[0].items() for item in expected.items()
        )


class TestAddSwitchMachine(BaseTest):
    """Test add switch machine."""

    def setUp(self):
        super(TestAddSwitchMachine, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestAddSwitchMachine, self).tearDown()

    def test_add_switch_machine(self):
        add_switch_machine = switch.add_switch_machine(
            self.user_object,
            1,
            mac='28:6e:d4:46:c4:25',
            port=1
        )
        expected = '28:6e:d4:46:c4:25'
        self.assertEqual(expected, add_switch_machine['mac'])


class TestListSwitchMachines(BaseTest):
    """Test get switch machines."""

    def setUp(self):
        super(TestListSwitchMachines, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestListSwitchMachines, self).tearDown()

    def test_list_switch_machines(self):
        switch.add_switch(
            self.user_object,
            ip='2887583784'
        )
        switch.add_switch_machine(
            self.user_object,
            2,
            mac='28:6e:d4:46:c4:25',
            port=1
        )
        list_switch_machines = switch.list_switch_machines(
            self.user_object,
            2
        )
        self.assertIsNotNone(list_switch_machines)


class TestListSwitchmachines(BaseTest):
    """Test list switch machines."""

    def setUp(self):
        super(TestListSwitchmachines, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestListSwitchmachines, self).tearDown()

    def test_list_switch_machines_with_ip_int(self):
        switch.add_switch(
            self.user_object,
            ip='2887583784'
        )
        switch.add_switch_machine(
            self.user_object,
            2,
            mac='28:6e:d4:46:c4:25',
            port=1
        )
        list_switch_machines = switch.list_switchmachines(
            self.user_object,
            switch_ip_int='2887583784'
        )
        expected = '172.29.8.40'
        self.assertTrue(expected for item in list_switch_machines[0].items())

    def test_list_switch_machines_ip_invalid(self):
        switch.add_switch(
            self.user_object,
            ip='2887583784'
        )
        switch.add_switch_machine(
            self.user_object,
            2,
            mac='28:6e:d4:46:c4:25',
            port=1
        )
        list_switch_machines = switch.list_switchmachines(
            self.user_object,
            switch_ip_int='test'
        )
        self.assertEqual(list_switch_machines, [])

    def test_list_switch_machines_without_ip(self):
        switch.add_switch(
            self.user_object,
            ip='2887583784'
        )
        switch.add_switch_machine(
            self.user_object,
            2,
            mac='28:6e:d4:46:c4:25',
            port=1
        )
        list_switch_machines = switch.list_switchmachines(
            self.user_object
        )
        self.assertIsNotNone(list_switch_machines)


class TestListSwitchMachinesHosts(BaseTest):
    """Test get switch machines hosts."""

    def setUp(self):
        super(TestListSwitchMachinesHosts, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestListSwitchMachinesHosts, self).tearDown()

    def test_list_hosts(self):
        switch.add_switch(
            self.user_object,
            ip='2887583784'
        )
        switch.add_switch_machine(
            self.user_object,
            2,
            mac='28:6e:d4:46:c4:25',
            port=1
        )
        list_hosts = switch.list_switch_machines_hosts(
            self.user_object,
            2
        )
        self.assertIsNotNone(list_hosts)


class TestListSwitchmachinesHosts(BaseTest):
    """Test list switch machines hosts."""

    def setUp(self):
        super(TestListSwitchmachinesHosts, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestListSwitchmachinesHosts, self).tearDown()

    def test_list_hosts_with_ip_int(self):
        switch.add_switch(
            self.user_object,
            ip='2887583784'
        )
        switch.add_switch_machine(
            self.user_object,
            2,
            mac='28:6e:d4:46:c4:25',
            port=1
        )
        list_hosts = switch.list_switchmachines_hosts(
            self.user_object,
            switch_ip_int='2887583784'
        )
        expected = '172.29.8.40'
        self.assertTrue(expected for item in list_hosts[0].items())

    def test_list_hosts_ip_invalid(self):
        switch.add_switch(
            self.user_object,
            ip='2887583784'
        )
        switch.add_switch_machine(
            self.user_object,
            2,
            mac='28:6e:d4:46:c4:25',
            port=1
        )
        list_hosts = switch.list_switchmachines_hosts(
            self.user_object,
            switch_ip_int='test'
        )
        self.assertEqual(list_hosts, [])

    def test_list_hosts_without_ip(self):
        switch.add_switch(
            self.user_object,
            ip='2887583784'
        )
        switch.add_switch_machine(
            self.user_object,
            2,
            mac='28:6e:d4:46:c4:25',
            port=1
        )
        list_hosts = switch.list_switchmachines_hosts(
            self.user_object
        )
        self.assertIsNotNone(list_hosts)


class TestPollSwitchMachines(BaseTest):
    """Test poll switch machines."""

    def setUp(self):
        super(TestPollSwitchMachines, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestPollSwitchMachines, self).tearDown()

    def test_poll_switch_machines(self):
        poll_switch_machines = switch.poll_switch_machines(
            self.user_object,
            1,
            find_machines='test'
        )
        self.assertIsNotNone(poll_switch_machines)


class TestGetSwitchMachine(BaseTest):
    """Test get a switch machines."""

    def setUp(self):
        super(TestGetSwitchMachine, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestGetSwitchMachine, self).tearDown()

    def test_get_switch_machine(self):
        switch.add_switch(
            self.user_object,
            ip='2887583784'
        )
        switch.add_switch_machine(
            self.user_object,
            2,
            mac='28:6e:d4:46:c4:25',
            port=1
        )
        get_switch_machine = switch.get_switch_machine(
            self.user_object,
            2,
            1
        )
        self.assertIsNotNone(get_switch_machine)


class TestGetSwitchmachine(BaseTest):
    """Test get a switch machine."""

    def setUp(self):
        super(TestGetSwitchmachine, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestGetSwitchmachine, self).tearDown()

    def test_get_switchmachine(self):
        switch.add_switch_machine(
            self.user_object,
            1,
            mac='28:6e:d4:46:c4:25',
            port=1
        )
        get_switchmachine = switch.get_switchmachine(
            self.user_object,
            1
        )
        self.assertIsNotNone(get_switchmachine)


class TestUpdateSwitchMachine(BaseTest):
    """Test update switch machine."""

    def setUp(self):
        super(TestUpdateSwitchMachine, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestUpdateSwitchMachine, self).tearDown()

    def test_update_switch_machine(self):
        switch.add_switch_machine(
            self.user_object,
            1,
            mac='28:6e:d4:46:c4:25',
            port=1
        )
        switch.update_switch_machine(
            self.user_object,
            1,
            1,
            tag='test_tag'
        )
        update_switch_machine = switch.list_switch_machines(
            self.user_object,
            1
        )
        expected = {'tag': 'test_tag'}
        self.assertTrue(
            item in update_switch_machine[0].items for item in expected.items()
        )


class TestUpdateSwitchmachine(BaseTest):
    """Test update switch machine."""

    def setUp(self):
        super(TestUpdateSwitchmachine, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestUpdateSwitchmachine, self).tearDown()

    def test_update_switchmachine(self):
        switch.add_switch_machine(
            self.user_object,
            1,
            mac='28:6e:d4:46:c4:25',
            port=1
        )
        switch.update_switchmachine(
            self.user_object,
            1,
            location='test_location'
        )
        update_switchmachine = switch.list_switchmachines(
            self.user_object,
        )
        expected = {'location': 'test_location'}
        self.assertTrue(
            item in update_switchmachine[0].items()
            for item in expected.items()
        )


class TestPatchSwitchMachine(BaseTest):
    """Test patch switch machine."""

    def setUp(self):
        super(TestPatchSwitchMachine, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestPatchSwitchMachine, self).tearDown()

    def test_pathc_switch_machine(self):
        switch.add_switch_machine(
            self.user_object,
            1,
            mac='28:6e:d4:46:c4:25',
            port=1
        )
        switch.patch_switch_machine(
            self.user_object,
            1,
            1,
            patched_tag={
                'patched_tag': 'test_patched_tag'
            }
        )
        switch_patch_switch_machine = switch.list_switch_machines(
            self.user_object,
            1
        )
        expected = {'patched_tag': 'test_patched_tag'}
        self.assertTrue(
            item in switch_patch_switch_machine[0].items()
            for item in expected.items()
        )


class TestPatchSwitchmachine(BaseTest):
    """Test patch switch machine."""

    def setUp(self):
        super(TestPatchSwitchmachine, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestPatchSwitchmachine, self).tearDown()

    def test_patch_switchmachine(self):
        switch.add_switch_machine(
            self.user_object,
            1,
            mac='28:6e:d4:46:c4:25',
            port=1
        )
        switch.patch_switchmachine(
            self.user_object,
            1,
            patched_location={
                'patched_location': 'test_location'
            }
        )
        patch_switchmachine = switch.list_switchmachines(
            self.user_object
        )
        expected = {'patched_location': 'test_location'}
        self.assertTrue(
            item in patch_switchmachine[0].items() for item in expected.items()
        )


class TestDelSwitchMachine(BaseTest):
    """Test delete switch machines."""

    def setUp(self):
        super(TestDelSwitchMachine, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestDelSwitchMachine, self).tearDown()

    def test_del_switch_machine(self):
        switch.add_switch_machine(
            self.user_object,
            1,
            mac='28:6e:d4:46:c4:25',
            port=1
        )
        switch.del_switch_machine(
            self.user_object,
            1,
            1
        )
        del_switch_machine = switch.list_switch_machines(
            self.user_object,
            1
        )
        self.assertEqual([], del_switch_machine)


class TestDelSwitchmachine(BaseTest):
    """Test delete switch machines."""

    def setUp(self):
        super(TestDelSwitchmachine, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestDelSwitchmachine, self).tearDown()

    def test_switchmachine(self):
        switch.add_switch_machine(
            self.user_object,
            1,
            mac='28:6e:d4:46:c4:25',
            port=1
        )
        switch.del_switchmachine(
            self.user_object,
            1
        )
        del_switchmachine = switch.list_switchmachines(
            self.user_object
        )
        self.assertEqual([], del_switchmachine)


class TestUpdateSwitchMachines(BaseTest):
    """Test update switch machines."""

    def setUp(self):
        super(TestUpdateSwitchMachines, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestUpdateSwitchMachines, self).tearDown()

    def test_update_switch_machines_remove(self):
        switch.add_switch(
            self.user_object,
            ip='2887583784'
        )
        switch.add_switch_machine(
            self.user_object,
            2,
            mac='28:6e:d4:46:c4:25',
            port=1
        )
        switch.update_switch_machines(
            self.user_object,
            2,
            remove_machines=1
        )
        update_remove = switch.list_switch_machines(
            self.user_object,
            2
        )
        self.assertEqual([], update_remove)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
