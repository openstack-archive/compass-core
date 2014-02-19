"""test hdsdiscovery base module"""
import os
import unittest2
from mock import patch


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from compass.hdsdiscovery.base import BaseSnmpVendor
from compass.hdsdiscovery.base import BaseSnmpMacPlugin
from compass.utils import flags
from compass.utils import logsetting


class MockSnmpVendor(BaseSnmpVendor):
    """snmp vendor mock class"""

    def __init__(self):
        BaseSnmpVendor.__init__(self, ["MockVendor", "FakeVendor"])


class TestBaseSnmpMacPlugin(unittest2.TestCase):
    """teset base snmp plugin class"""

    def setUp(self):
        self.test_plugin = BaseSnmpMacPlugin('12.0.0.1',
                                             {'version': '2c',
                                              'community': 'public'})

    def tearDown(self):
        del self.test_plugin

    @patch('compass.hdsdiscovery.utils.snmpget_by_cl')
    def test_get_port(self, mock_snmpget):
        """test snmp get port"""
        mock_snmpget.return_value = 'IF-MIB::ifName.4 = STRING: ge-1/1/4'
        result = self.test_plugin.get_port('4')
        self.assertEqual('4', result)

    @patch('compass.hdsdiscovery.utils.snmpget_by_cl')
    def test_get_vlan_id(self, mock_snmpget):
        """test snmp get vlan"""
        # Port is None
        self.assertIsNone(self.test_plugin.get_vlan_id(None))

        # Port is not None
        mock_snmpget.return_value = 'Q-BRIDGE-MIB::dot1qPvid.4 = Gauge32: 100'
        result = self.test_plugin.get_vlan_id('4')
        self.assertEqual('100', result)

    def test_get_mac_address(self):
        """tet snmp get mac address"""
        # Correct input for mac numbers
        mac_numbers = '0.224.129.230.57.173'.split('.')
        mac = self.test_plugin.get_mac_address(mac_numbers)
        self.assertEqual('00:e0:81:e6:39:ad', mac)

        # Incorrct input for mac numbers
        mac_numbers = '0.224.129.230.57'.split('.')
        mac = self.test_plugin.get_mac_address(mac_numbers)
        self.assertIsNone(mac)


class BaseTest(unittest2.TestCase):
    """base test class"""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_base_snmp_vendor(self):
        """test base snmp vendor"""
        fake = MockSnmpVendor()

        credential = {"version": "2c",
                      "community": "public"}
        is_vendor = fake.is_this_vendor("12.0.0.1", credential,
                                        "FakeVendor 1.1")

        self.assertTrue(is_vendor)

        # check case-insensitive match

        self.assertFalse(fake.is_this_vendor("12.0.0.1", credential,
                         "fakevendor1.1"))

        # breaks word-boudary match
        self.assertFalse(fake.is_this_vendor("12.0.0.1", credential,
                         "FakeVendor1.1"))

        # Not SNMP credentials
        self.assertFalse(fake.is_this_vendor("12.0.0.1",
                                             {"username": "root",
                                              "password": "test123"},
                                             "fakevendor1.1"))

        # Not SNMP v2 credentials
        self.assertFalse(fake.is_this_vendor("12.0.0.1",
                                             {"version": "v1",
                                              "community": "public"},
                                             "fakevendor1.1"))


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
