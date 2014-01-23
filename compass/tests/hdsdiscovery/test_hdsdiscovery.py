import unittest2
from mock import patch

from compass.hdsdiscovery.hdmanager import HDManager
from compass.hdsdiscovery.vendors.huawei.huawei import Huawei
from compass.hdsdiscovery.vendors.huawei.plugins.mac import Mac


class HuaweiTest(unittest2.TestCase):

    def setUp(self):
        self.huawei = Huawei()
        self.correct_host = '12.23.1.1'
        self.correct_credentials = {'version': 'v2c', 'community': 'public'}
        self.sys_info = 'Huawei Technologies'

    def tearDown(self):
        del self.huawei

    def test_is_this_vendor(self):
        #Credential's keyword is incorrect
        self.assertFalse(
            self.huawei.is_this_vendor(self.correct_host,
                                       {'username': 'root',
                                        'password': 'root'},
                                       self.sys_info))

        #Incorrect version
        self.assertFalse(
            self.huawei.is_this_vendor(self.correct_host,
                                       {'version': 'v1',
                                        'community': 'public'},
                                       self.sys_info))

        #Correct vendor
        self.assertTrue(
            self.huawei.is_this_vendor(self.correct_host,
                                       self.correct_credentials,
                                       self.sys_info))


class HuaweiMacTest(unittest2.TestCase):
    def setUp(self):
        host = '12.23.1.1'
        credential = {'version': 'v2c', 'community': 'public'}
        self.mac_plugin = Mac(host, credential)

    def tearDown(self):
        del self.mac_plugin

    def test_ProcessData_Operation(self):
        # GET operation haven't been implemeneted.
        self.assertIsNone(self.mac_plugin.process_data('GET'))


from compass.hdsdiscovery.vendors.ovswitch.plugins.mac import Mac as OVSMac


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


class HDManagerTest(unittest2.TestCase):

    def setUp(self):
        self.manager = HDManager()
        self.correct_host = '12.23.1.1'
        self.correct_credential = {'version': 'v2c', 'community': 'public'}

    def tearDown(self):
        del self.manager

    @patch('compass.hdsdiscovery.hdmanager.HDManager.get_sys_info')
    def test_get_vendor(self, sys_info_mock):
        # Incorrect ip
        self.assertIsNone(self.manager.get_vendor('1234.1.1.1',
                                                  self.correct_credential)[0])

        # Incorrect credential
        self.assertIsNone(
            self.manager.get_vendor(self.correct_host,
                                    {'version': '1v',
                                     'community': 'private'})[0])

        # SNMP get system description Timeout
        excepted_err_msg = 'Timeout: No Response from 12.23.1.1.'
        sys_info_mock.return_value = (None, excepted_err_msg)
        result, state, err = self.manager.get_vendor(self.correct_host,
                                                     self.correct_credential)
        self.assertIsNone(result)
        self.assertEqual(state, 'unreachable')
        self.assertEqual(err, excepted_err_msg)

        # No vendor plugin supported
        excepted_err_msg = 'Not supported switch vendor!'
        sys_info_mock.return_value = ('xxxxxx', excepted_err_msg)
        result, state, err = self.manager.get_vendor(self.correct_host,
                                                     self.correct_credential)
        self.assertIsNone(result)
        self.assertEqual(state, 'notsupported')
        self.assertEqual(err, excepted_err_msg)

        # Found the correct vendor
        sys_info = ['Huawei Versatile Routing Platform Software',
                    'ProCurve J9089A Switch 2610-48-PWR, revision R.11.25',
                    'Pica8 XorPlus Platform Software']
        expected_vendor_names = ['huawei', 'hp', 'pica8']
        for info, expected_vendor in zip(sys_info, expected_vendor_names):
            sys_info_mock.return_value = (info, '')
            result, state, err = self.manager\
                                     .get_vendor(self.correct_host,
                                                 self.correct_credential)
            self.assertEqual(result, expected_vendor)

    @patch('compass.hdsdiscovery.hdmanager.HDManager.get_sys_info')
    def test_is_valid_vendor(self, sys_info_mock):

        #non-exsiting vendor
        self.assertFalse(self.manager.is_valid_vendor(self.correct_host,
                                                      self.correct_credential,
                                                      'xxxx'))
        #No system description retrieved
        sys_info_mock.return_value = (None, 'TIMEOUT')
        self.assertFalse(self.manager.is_valid_vendor(self.correct_host,
                                                      self.correct_credential,
                                                      'pica8'))
        #Incorrect vendor name
        sys_info = 'Pica8 XorPlus Platform Software'
        sys_info_mock.return_value = (sys_info, '')
        self.assertFalse(self.manager.is_valid_vendor(self.correct_host,
                                                      self.correct_credential,
                                                      'huawei'))

        #Correct vendor name
        self.assertTrue(self.manager.is_valid_vendor(self.correct_host,
                                                     self.correct_credential,
                                                     'pica8'))

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
