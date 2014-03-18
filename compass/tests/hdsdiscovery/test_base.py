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

"""test hdsdiscovery base module."""
import os
import unittest2

from mock import patch


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from compass.hdsdiscovery.base import BaseSnmpMacPlugin
from compass.hdsdiscovery.base import BaseSnmpVendor
from compass.hdsdiscovery.error import TimeoutError
from compass.utils import flags
from compass.utils import logsetting


class MockSnmpVendor(BaseSnmpVendor):
    """snmp vendor mock class."""

    def __init__(self):
        BaseSnmpVendor.__init__(self, ["MockVendor", "FakeVendor"])


class TestBaseSnmpMacPlugin(unittest2.TestCase):
    """teset base snmp plugin class."""

    def setUp(self):
        super(TestBaseSnmpMacPlugin, self).setUp()
        logsetting.init()
        self.test_plugin = BaseSnmpMacPlugin('127.0.0.1',
                                             {'version': '2c',
                                              'community': 'public'})

    def tearDown(self):
        del self.test_plugin
        super(TestBaseSnmpMacPlugin, self).tearDown()

    @patch('compass.hdsdiscovery.utils.snmpget_by_cl')
    def test_get_port(self, mock_snmpget):
        """test snmp get port."""
        # Successfully get port number
        mock_snmpget.return_value = 'IF-MIB::ifName.4 = STRING: ge-1/1/4'
        result = self.test_plugin.get_port('4')
        self.assertEqual('4', result)

        # Failed to get port number, switch is timeout
        mock_snmpget.side_effect = TimeoutError("Timeout")
        result = self.test_plugin.get_port('4')
        self.assertIsNone(result)

    @patch('compass.hdsdiscovery.utils.snmpget_by_cl')
    def test_get_vlan_id(self, mock_snmpget):
        """test snmp get vlan."""
        # Port is None
        self.assertIsNone(self.test_plugin.get_vlan_id(None))

        # Port is not None
        mock_snmpget.return_value = 'Q-BRIDGE-MIB::dot1qPvid.4 = Gauge32: 100'
        result = self.test_plugin.get_vlan_id('4')
        self.assertEqual('100', result)

        # Faild to query switch due to timeout
        mock_snmpget.side_effect = TimeoutError("Timeout")
        result = self.test_plugin.get_vlan_id('4')
        self.assertIsNone(result)

    def test_get_mac_address(self):
        """tet snmp get mac address."""
        # Correct input for mac numbers
        mac_numbers = '0.224.129.230.57.173'.split('.')
        mac = self.test_plugin.get_mac_address(mac_numbers)
        self.assertEqual('00:e0:81:e6:39:ad', mac)

        # Incorrct input for mac numbers
        mac_numbers = '0.224.129.230.57'.split('.')
        mac = self.test_plugin.get_mac_address(mac_numbers)
        self.assertIsNone(mac)


class BaseTest(unittest2.TestCase):
    """base test class."""

    def setUp(self):
        super(BaseTest, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(BaseTest, self).tearDown()

    def test_base_snmp_vendor(self):
        """test base snmp vendor."""
        fake = MockSnmpVendor()

        is_vendor = fake.is_this_vendor("FakeVendor 1.1")

        self.assertTrue(is_vendor)

        # check case-insensitive match
        self.assertFalse(fake.is_this_vendor("fakevendor1.1"))

        # breaks word-boudary match
        self.assertFalse(fake.is_this_vendor("FakeVendor1.1"))


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
