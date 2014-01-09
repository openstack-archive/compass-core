import unittest2
from mock import patch

from compass.hdsdiscovery.vendors.huawei.huawei import Huawei


class HuaweiTest(unittest2.TestCase):

    def setUp(self):
        self.huawei = Huawei()
        self.correct_host = '172.29.8.40'
        self.correct_credentials = {'Version': 'v2c', 'Community': 'public'}

    def tearDown(self):
        del self.huawei

    @patch('compass.hdsdiscovery.utils.snmp_get')
    def test_IsThisVendor_WithIncorrectIPFormat(self, snmp_get_mock):
        snmp_get_mock.return_value = None

        #host is incorrest IP address format
        self.assertFalse(self.huawei.is_this_vendor('500.10.1.2000',
                                                    self.correct_credentials))

    @patch('compass.hdsdiscovery.utils.snmp_get')
    def test_IsThisVendor_WithWrongCredential(self, snmp_get_mock):
        snmp_get_mock.return_value = None

        #Credential's keyword is incorrect
        self.assertFalse(
            self.huawei.is_this_vendor(self.correct_host,
                                       {'username': 'root',
                                        'Community': 'public'}))

        #Incorrect Version
        self.assertFalse(
            self.huawei.is_this_vendor(self.correct_host,
                                       {'Version': 'v1',
                                        'Community': 'public'}))

        #Incorrect Community
        self.assertFalse(
            self.huawei.is_this_vendor(self.correct_host,
                                       {'Version': 'v2c',
                                        'Community': 'private'}))

    @patch('compass.hdsdiscovery.utils.snmp_get')
    def test_IsThisVendor_WithCorrectInput(self, snmp_get_mock):
        snmp_get_mock.return_value = "Huawei"
        self.assertTrue(self.huawei.is_this_vendor(self.correct_host,
                                                   self.correct_credentials))

    @patch('compass.hdsdiscovery.utils.snmp_get')
    def test_IsThisVendor_WithIncorrectVendor(self, snmp_get_mock):

        snmp_get_mock.return_value = None
        self.assertFalse(
            self.huawei.is_this_vendor('1.1.1.1',
                                       {'Version': 'v1',
                                        'Community': 'private'}))


from compass.hdsdiscovery.vendors.huawei.plugins.mac import Mac


class HuaweiMacTest(unittest2.TestCase):
    def setUp(self):
        host = '172.29.8.40'
        credential = {'Version': 'v2c', 'Community': 'public'}
        self.mac = Mac(host, credential)

    def tearDown(self):
        del self.mac

    def test_ProcessData_Operation(self):
        # GET operation haven't been implemeneted.
        self.assertIsNone(self.mac.process_data('GET'))


from compass.hdsdiscovery.vendors.ovswitch.ovswitch import OVSwitch
from compass.hdsdiscovery.vendors.ovswitch.plugins.mac import Mac as OVSMac


class OVSTest(unittest2.TestCase):
    def setUp(self):
        self.host = '10.145.88.160'
        self.credential = {'username': 'root', 'password': 'huawei'}
        self.ovswitch = OVSwitch()

    def tearDown(self):
        del self.ovswitch

    @patch('compass.hdsdiscovery.utils.ssh_remote_execute')
    def test_isThisVendor_withIncorrectInput(self, ovs_mock):
        ovs_mock.return_value = []
        # Incorrect host ip
        self.assertFalse(self.ovswitch.is_this_vendor('1.1.1.1',
                                                      self.credential))

        # Incorrect credential
        self.assertFalse(
            self.ovswitch.is_this_vendor(self.host,
                                         {'username': 'xxx',
                                          'password': 'xxx'}))
        # not Open vSwitch
        self.assertFalse(
            self.ovswitch.is_this_vendor(self.host,
                                         {'Version': 'xxx',
                                          'Community': 'xxx'}))
        # not Open vSwitch, snmpv3
        self.assertFalse(
            self.ovswitch.is_this_vendor(self.host,
                                         {'Version': 'xxx',
                                          'Community': 'xxx',
                                          'username': 'xxx',
                                          'password': 'xxx'}))


class OVSMacTest(unittest2.TestCase):
    def setUp(self):
        self.host = '10.145.88.160'
        self.credential = {'username': 'root', 'password': 'huawei'}

    @patch('compass.hdsdiscovery.utils.ssh_remote_execute')
    def test_scan(self, ovs_mock):
        ovs_mock.return_value = []
        mac_instance = OVSMac(self.host, self.credential)
        self.assertIsNone(mac_instance.scan())
        del mac_instance

        ovs_mock.return_value = ['\n', '\n', '\n']
        mac_instance = OVSMac(self.host, self.credential)
        self.assertEqual([], mac_instance.scan())
        del mac_instance


from compass.hdsdiscovery.vendors.hp.hp import Hp


class HpTest(unittest2.TestCase):
    def setUp(self):
        self.host = '10.145.88.140'
        self.credential = {'Version': 'v2c', 'Community': 'public'}
        self.hpSwitch = Hp()

    def tearDown(self):
        del self.hpSwitch

    @patch('compass.hdsdiscovery.utils.snmp_get')
    def test_IsThisVendor(self, snmpget_mock):
        snmpget_mock.return_value = "ProCurve J9089A Switch 2610-48-PWR"
        self.assertTrue(self.hpSwitch.is_this_vendor(self.host,
                                                     self.credential))

        snmpget_mock.return_value = None
        self.assertFalse(self.hpSwitch.is_this_vendor(self.host,
                                                      self.credential))

        snmpget_mock.return_value = "xxxxxxxxxxx"
        self.assertFalse(self.hpSwitch.is_this_vendor(self.host,
                                                      self.credential))


from compass.hdsdiscovery.hdmanager import HDManager


class HDManagerTest(unittest2.TestCase):

    def setUp(self):
        self.manager = HDManager()
        self.correct_host = '172.29.8.40'
        self.correct_credential = {'Version': 'v2c', 'Community': 'public'}

        self.ovs_host = '10.145.88.160'
        self.ovs_credential = {'username': 'root', 'password': 'huawei'}

    def tearDown(self):
        del self.manager

    @patch('compass.hdsdiscovery.utils.ssh_remote_execute')
    @patch('compass.hdsdiscovery.utils.snmp_get')
    def test_GetVendor_WithIncorrectInput(self, snmp_get_mock, ovs_mock):
        snmp_get_mock.return_value = None
        ovs_mock.return_value = []

        # Incorrect ip
        self.assertIsNone(self.manager.get_vendor('1.1.1.1',
                                                  self.correct_credential))
        self.assertIsNone(self.manager.get_vendor('1.1.1.1',
                                                  self.ovs_credential))

        # Incorrect credential
        self.assertIsNone(
            self.manager.get_vendor(self.correct_host,
                                    {'Version': '1v', 'Community': 'private'}))
        self.assertIsNone(
            self.manager.get_vendor(self.ovs_host,
                                    {'username': 'xxxxx', 'password': 'xxxx'}))

    def test_ValidVendor(self):
        #non-exsiting vendor
        self.assertFalse(self.manager.is_valid_vendor(self.correct_host,
                                                      self.correct_credential,
                                                      'xxxx'))

    def test_Learn(self):
        #non-exsiting plugin
        self.assertIsNone(self.manager.learn(self.correct_host,
                                             self.correct_credential,
                                             'huawei', 'xxx'))

        #non-existing vendor
        self.assertIsNone(self.manager.learn(self.correct_host,
                                             self.correct_credential,
                                             'xxxx', 'mac'))


from compass.hdsdiscovery import utils


class UtilsTest(unittest2.TestCase):
    def test_LoadModule(self):
        self.assertIsNone(utils.load_module('xxx', 'fake/path/to/module'))


if __name__ == '__main__':
    unittest2.main()
