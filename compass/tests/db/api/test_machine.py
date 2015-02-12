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
import unittest2

os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from base import BaseTest
from compass.db.api import database
from compass.db.api import machine
from compass.db.api import switch
from compass.db.api import user as user_api
from compass.db import exception
from compass.utils import flags
from compass.utils import logsetting


class TestGetMachine(BaseTest):
    """Test get machine."""

    def setUp(self):
        super(TestGetMachine, self).setUp()

    def tearDown(self):
        super(TestGetMachine, self).tearDown()

    def test_get_machine(self):
        switch.add_switch_machine(
            1,
            mac='28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        get_machine = machine.get_machine(
            1,
            user=self.user_object,
        )
        self.assertIsNotNone(get_machine)
        self.assertEqual(get_machine['mac'], '28:6e:d4:46:c4:25')


class TestListMachines(BaseTest):
    """Test list machines."""

    def setUp(self):
        super(TestListMachines, self).setUp()

    def tearDown(self):
        super(TestListMachines, self).tearDown()

    def test_list_machines(self):
        switch.add_switch_machine(
            1,
            mac='28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        list_machine = machine.list_machines(self.user_object)
        self.assertIsNotNone(list_machine)
        self.assertEqual(list_machine[0]['mac'], '28:6e:d4:46:c4:25')


class TestUpdateMachine(BaseTest):
    """Test update machine."""

    def setUp(self):
        super(TestUpdateMachine, self).setUp()

    def tearDown(self):
        super(TestUpdateMachine, self).tearDown()

    def test_update_machine(self):
        switch.add_switch_machine(
            1,
            mac='28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        machine.update_machine(
            1,
            tag='test',
            user=self.user_object,
        )
        update_machine = machine.list_machines(self.user_object)
        expected = {
            'id': 1,
            'mac': '28:6e:d4:46:c4:25',
            'tag': 'test',
            'switch_ip': '0.0.0.0',
            'port': '1'
        }
        self.assertTrue(
            all(item in update_machine[0].items() for item in expected.items())
        )


class TestPatchMachine(BaseTest):
    """Test patch machine."""

    def setUp(self):
        super(TestPatchMachine, self).setUp()

    def tearDown(self):
        super(TestPatchMachine, self).tearDown()

    def test_patch_machine(self):
        switch.add_switch_machine(
            1,
            mac='28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        machine.patch_machine(
            1,
            user=self.user_object,
            tag={'patched_tag': 'test'}
        )
        patch_machine = machine.list_machines(self.user_object)
        expected = {'tag': {'patched_tag': 'test'}}
        self.assertTrue(
            all(item in patch_machine[0].items() for item in expected.items())
        )


class TestDelMachine(BaseTest):
    """Test delete machine."""

    def setUp(self):
        super(TestDelMachine, self).setUp()

    def tearDown(self):
        super(TestDelMachine, self).tearDown()

    def test_del_machine(self):
        switch.add_switch_machine(
            1,
            mac='28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        machine.del_machine(
            1,
            user=self.user_object,
        )
        del_machine = machine.list_machines(self.user_object)
        self.assertEqual([], del_machine)


class TestPoweronMachine(BaseTest):
    """Test poweron machine."""

    def setUp(self):
        super(TestPoweronMachine, self).setUp()

    def tearDown(self):
        super(TestPoweronMachine, self).tearDown()

    def test_poweron_machine(self):
        switch.add_switch_machine(
            1,
            mac='28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        from compass.tasks import client as celery_client
        celery_client.celery.send_task = mock.Mock()
        poweron_machine = machine.poweron_machine(
            1,
            poweron={'poweron': True},
            user=self.user_object
        )
        expected = {
            'status': 'poweron 28:6e:d4:46:c4:25 action sent',
        }
        self.assertTrue(all(
            item in poweron_machine.items() for item in expected.items())
        )


class TestPoweroffMachine(BaseTest):
    """Test poweroff machine."""

    def setUp(self):
        super(TestPoweroffMachine, self).setUp()

    def tearDown(self):
        super(TestPoweroffMachine, self).tearDown()

    def test_poweroff_machine(self):
        switch.add_switch_machine(
            1,
            mac='28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        from compass.tasks import client as celery_client
        celery_client.celery.send_task = mock.Mock()
        poweroff_machine = machine.poweroff_machine(
            1,
            {'poweroff': True},
            user=self.user_object
        )
        expected = {
            'status': 'poweroff 28:6e:d4:46:c4:25 action sent'
        }
        self.assertTrue(all(
            item in poweroff_machine.items() for item in expected.items())
        )


class TestResetMachine(BaseTest):
    """Test reset machine."""

    def setUp(self):
        super(TestResetMachine, self).setUp()

    def tearDown(self):
        super(TestResetMachine, self).tearDown()

    def test_reset_machine(self):
        switch.add_switch_machine(
            1,
            mac='28:6e:d4:46:c4:25',
            port='1',
            user=self.user_object,
        )
        from compass.tasks import client as celery_client
        celery_client.celery.send_task = mock.Mock()
        reset_machine = machine.reset_machine(
            1,
            {'reset_machine': True},
            user=self.user_object
        )
        expected = {
            'status': 'reset 28:6e:d4:46:c4:25 action sent'
        }
        self.assertTrue(all(
            item in reset_machine.items() for item in expected.items())
        )


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
