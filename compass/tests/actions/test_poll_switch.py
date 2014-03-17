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

"""test poll_switch action module."""
from mock import patch
import os
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from compass.actions import poll_switch
from compass.api import app
from compass.db import database
from compass.db.model import Machine
from compass.db.model import Switch
from compass.db.model import SwitchConfig
from compass.utils import flags
from compass.utils import logsetting


class TestPollSwitch(unittest2.TestCase):
    """base api test class."""

    CLUSTER_NAME = "Test1"
    SWITCH_CREDENTIAL = {'version': '2c',
                         'community': 'public'}
    DATABASE_URL = 'sqlite://'

    def setUp(self):
        super(TestPollSwitch, self).setUp()
        logsetting.init()
        database.init(self.DATABASE_URL)
        database.create_db()
        self.test_client = app.test_client()

        with database.session() as session:
            # Add one switch to DB
            switch = Switch(ip="127.0.0.1",
                            credential=self.SWITCH_CREDENTIAL)
            session.add(switch)
            # Add filter port to SwitchConfig table
            filter_list = [
                SwitchConfig(ip="127.0.0.1", filter_port='6'),
                SwitchConfig(ip="127.0.0.1", filter_port='7')
            ]
            session.add_all(filter_list)

    def tearDown(self):
        database.drop_db()
        super(TestPollSwitch, self).tearDown()

    @patch("compass.hdsdiscovery.hdmanager.HDManager.learn")
    @patch("compass.hdsdiscovery.hdmanager.HDManager.get_vendor")
    def test_poll_switch(self, mock_get_vendor, mock_learn):
        # Incorrect IP address format
        poll_switch.poll_switch("xxx")
        with database.session() as session:
            machines = session.query(Machine).filter_by(switch_id=1).all()
            self.assertEqual([], machines)

        # Switch is unreachable
        mock_get_vendor.return_value = (None, 'unreachable', 'Timeout')
        poll_switch.poll_switch('127.0.0.1')
        with database.session() as session:
            machines = session.query(Machine).filter_by(switch_id=1).all()
            self.assertEqual([], machines)

            switch = session.query(Switch).filter_by(id=1).first()
            self.assertEqual(switch.state, 'unreachable')

        # Successfully retrieve machines from the switch
        mock_get_vendor.return_value = ('xxx', 'Found', "")
        mock_learn.return_value = [
            {'mac': '00:01:02:03:04:05', 'vlan': '1', 'port': '1'},
            {'mac': '00:01:02:03:04:06', 'vlan': '1', 'port': '2'},
            {'mac': '00:01:02:03:04:07', 'vlan': '2', 'port': '3'},
            {'mac': '00:01:02:03:04:08', 'vlan': '2', 'port': '4'},
            {'mac': '00:01:02:03:04:09', 'vlan': '3', 'port': '5'}
        ]
        poll_switch.poll_switch('127.0.0.1')
        with database.session() as session:
            machines = session.query(Machine).filter_by(switch_id=1).all()
            self.assertEqual(5, len(machines))
            # The state and err_msg of the switch should be reset.
            switch = session.query(Switch).filter_by(id=1).first()
            self.assertEqual(switch.state, "under_monitoring")
            self.assertEqual(switch.err_msg, "")

        # Successfully retrieve and filter some machines
        # In the following case, machines with port 6, 7 will be filtered.
        mock_learn.return_value = [
            {'mac': '00:01:02:03:04:10', 'vlan': '3', 'port': '6'},
            {'mac': '00:01:02:03:04:0a', 'vlan': '4', 'port': '7'},
            {'mac': '00:01:02:03:04:0b', 'vlan': '4', 'port': '8'},
            {'mac': '00:01:02:03:04:0c', 'vlan': '5', 'port': '9'},
            {'mac': '00:01:02:03:04:0d', 'vlan': '5', 'port': '10'}
        ]
        poll_switch.poll_switch('127.0.0.1')
        with database.session() as session:
            machines = session.query(Machine).filter_by(switch_id=1).all()
            self.assertEqual(8, len(machines))


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
