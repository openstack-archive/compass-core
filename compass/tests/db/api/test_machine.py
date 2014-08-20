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
from compass.db.api import machine
from compass.db.api import switch
from compass.db.api import user as user_api
from compass.db import exception
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import setting_wrapper as setting

os.environ['COMPASS_IGNORE_SETTING'] = 'true'


class TestGetMachine(BaseTest):
    """Test get machine."""

    def setUp(self):
        super(TestGetMachine, self).setUp()

    def tearDown(self):
        super(TestGetMachine, self).tearDown()

    def test_get_machine(self):
        switch.add_switch_machine(
            self.user_object,
            1,
            mac='28:6e:d4:46:c4:25',
            port='1'
        )
        get_machine = machine.get_machine(
            self.user_object,
            1
        )
        self.assertIsNotNone(get_machine)


class TestListMachines(BaseTest):
    """Test list machines."""

    def setUp(self):
        super(TestListMachines, self).setUp()

    def tearDown(self):
        super(TestListMachines, self).tearDown()

    def test_list_machines(self):
        switch.add_switch_machine(
            self.user_object,
            1,
            mac='28:6e:d4:46:c4:25',
            port='1'
        )
        list_machine = machine.list_machines(self.user_object)
        self.assertIsNotNone(list_machine)


class TestUpdateMachine(BaseTest):
    """Test update machine."""

    def setUp(self):
        super(TestUpdateMachine, self).setUp()

    def tearDown(self):
        super(TestUpdateMachine, self).tearDown()

    def test_update_machine(self):
        switch.add_switch_machine(
            self.user_object,
            1,
            mac='28:6e:d4:46:c4:25',
            port='1'
        )
        machine.update_machine(
            self.user_object,
            1,
            tag='test'
        )
        update_machine = machine.list_machines(self.user_object)
        expected = {'tag': 'test'}
        self.assertTrue(
            item in update_machine[0].items() for item in expected.items()
        )


class TestPatchMachine(BaseTest):
    """Test patch machine."""

    def setUp(self):
        super(TestPatchMachine, self).setUp()

    def tearDown(self):
        super(TestPatchMachine, self).tearDown()

    def test_patch_machine(self):
        switch.add_switch_machine(
            self.user_object,
            1,
            mac='28:6e:d4:46:c4:25',
            port='1'
        )
        machine.patch_machine(
            self.user_object,
            1,
            tag={'patched_tag': 'test'}
        )
        patch_machine = machine.list_machines(self.user_object)
        expected = {'patched_tag': 'test'}
        self.assertTrue(
            item in patch_machine[0].items() for item in expected.items()
        )


class TestDelMachine(BaseTest):
    """Test delete machine."""

    def setUp(self):
        super(TestDelMachine, self).setUp()

    def tearDown(self):
        super(TestDelMachine, self).tearDown()

    def test_del_machine(self):
        switch.add_switch_machine(
            self.user_object,
            1,
            mac='28:6e:d4:46:c4:25',
            port='1'
        )
        machine.del_machine(
            self.user_object,
            1
        )
        del_machine = machine.list_machines(self.user_object)
        self.assertEqual([], del_machine)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
