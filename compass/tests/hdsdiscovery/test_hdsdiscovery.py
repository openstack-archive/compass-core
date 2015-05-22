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

"""test hdsdiscovery module."""
import os
import unittest2

from mock import Mock
from mock import patch

os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from compass.hdsdiscovery.hdmanager import HDManager
from compass.hdsdiscovery.vendors.huawei.huawei import Huawei
from compass.hdsdiscovery.vendors.huawei.plugins.mac import Mac
from compass.hdsdiscovery.vendors.ovswitch.plugins.mac import Mac as OVSMac
from compass.utils import flags
from compass.utils import logsetting


SNMP_V2_CREDENTIALS = {'version': '2c',
                       'community': 'public'}


class HuaweiTest(unittest2.TestCase):
    """test huawei switch snmp get."""

    def setUp(self):
        super(HuaweiTest, self).setUp()
        logsetting.init()
        self.huawei = Huawei()
        self.sys_info = 'Huawei Technologies'

    def tearDown(self):
        del self.huawei
        super(HuaweiTest, self).tearDown()

    def test_is_this_vendor(self):
        """test device vendor is haiwei."""
        # Incorrect system information
        incorrect_sys_info = "xxx"
        self.assertFalse(
            self.huawei.is_this_vendor(incorrect_sys_info))

        # Correct vendor
        self.assertTrue(
            self.huawei.is_this_vendor(self.sys_info))


class HuaweiMacTest(unittest2.TestCase):
    """test get mac from huawei device."""

    def setUp(self):
        super(HuaweiMacTest, self).setUp()
        logsetting.init()
        host = '192.168.1.1'
        credential = {'version': '2c', 'community': 'public'}
        self.mac_plugin = Mac(host, credential)

    def tearDown(self):
        del self.mac_plugin
        super(HuaweiMacTest, self).tearDown()

    @patch("compass.hdsdiscovery.utils.snmpwalk_by_cl")
    def test_process_data(self, mock_snmpwalk):
        """get progress data function."""
        # GET operation haven't been implemeneted.
        self.assertIsNone(self.mac_plugin.process_data('GET'))

        # SNMP Walk Timeout
        # utils.snmpwalk_by_cl = Mock(return_value=None)
        mock_snmpwalk.return_value = None
        self.assertIsNone(self.mac_plugin.process_data())

        # Successfully get MAC addresses from the switch
        mock_snmp_walk_result = [
            {"iid": "40.110.212.77.198.190.88.1.48", "value": "10"},
            {"iid": "40.110.212.100.199.74.88.1.48", "value": "11"},
            {"iid": "0.12.41.53.220.2.88.1.48", "value": "12"}
        ]
        expected_mac_info = [
            {"mac": "28:6e:d4:4d:c6:be", "port": "1", "vlan": "88"},
            {"mac": "28:6e:d4:64:c7:4a", "port": "2", "vlan": "88"},
            {"mac": "00:0c:29:35:dc:02", "port": "3", "vlan": "88"}
        ]
        # utils.snmpwalk_by_cl = Mock(return_value=mock_snmp_walk_result)
        mock_snmpwalk.return_value = mock_snmp_walk_result
        self.mac_plugin.get_port = Mock()
        self.mac_plugin.get_port.side_effect = ["1", "2", "3"]
        result = self.mac_plugin.process_data()
        self.assertEqual(expected_mac_info, result)


class OVSMacTest(unittest2.TestCase):
    """ovs switch test."""

    def setUp(self):
        super(OVSMacTest, self).setUp()
        logsetting.init()
        self.host = '10.145.88.160'
        self.credential = {'username': 'root', 'password': 'huawei'}

    @patch('compass.hdsdiscovery.utils.ssh_remote_execute')
    def test_scan(self, ovs_mock):
        """test scan ovs switch."""
        ovs_mock.return_value = []
        mac_instance = OVSMac(self.host, self.credential)
        self.assertIsNone(mac_instance.scan())
        del mac_instance

        ovs_mock.return_value = ['\n', '\n', '\n']
        mac_instance = OVSMac(self.host, self.credential)
        self.assertEqual([], mac_instance.scan())
        del mac_instance


class HDManagerTest(unittest2.TestCase):
    """test HDManager."""

    def setUp(self):
        super(HDManagerTest, self).setUp()
        logsetting.init()
        self.manager = HDManager()
        self.correct_host = '33.33.33.1'
        self.correct_host_2 = '127.0.0.1'
        self.correct_credential = {'version': '2c', 'community': 'public'}

    def tearDown(self):
        del self.manager
        super(HDManagerTest, self).tearDown()

    @patch('compass.hdsdiscovery.hdmanager.HDManager.get_sys_info')
    def test_get_vendor(self, sys_info_mock):
        """test get_vendor."""
        # Incorrect ip
        vendor, state, err = self.manager.get_vendor('1234.1.1.1',
                                                     self.correct_credential)
        self.assertIsNone(vendor)
        self.assertEqual('error', state)

        # Incorrect credential
        incorr_cred = {'version': '1v', 'community': 'private'}
        vendor, state, err = self.manager.get_vendor(self.correct_host,
                                                     incorr_cred)
        self.assertIsNone(vendor)
        self.assertEqual('error', state)

        # SNMP get system description Timeout
        excepted_err_msg = 'Timeout: No Response from 127.0.0.1.'
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
        expected_vendor_names = ['huawei', 'hp', 'pica8', 'appliance']
        for info, expected_vendor in zip(sys_info, expected_vendor_names):
            sys_info_mock.return_value = (info, '')
            # the result is a tuple ($vendor, $state, $error_message)
            result = self.manager.get_vendor(self.correct_host,
                                             self.correct_credential)
            self.assertEqual(result[0], expected_vendor)

    @patch('compass.hdsdiscovery.hdmanager.HDManager.get_sys_info')
    def test_is_valid_vendor(self, sys_info_mock):
        """test is_valid_vendor."""
        # non-exsiting vendor under vendors directory
        self.assertFalse(
            self.manager.is_valid_vendor(self.correct_host,
                                         self.correct_credential,
                                         'xxxx')
        )

        # No system description retrieved
        sys_info_mock.return_value = (None, 'TIMEOUT')
        self.assertFalse(
            self.manager.is_valid_vendor(self.correct_host,
                                         self.correct_credential,
                                         'pica8')
        )

        # Incorrect vendor name
        sys_info = 'Pica8 XorPlus Platform Software'
        sys_info_mock.return_value = (sys_info, '')
        self.assertFalse(
            self.manager.is_valid_vendor(self.correct_host,
                                         self.correct_credential,
                                         'huawei')
        )

        # Correct vendor name
        self.assertTrue(
            self.manager.is_valid_vendor(self.correct_host,
                                         self.correct_credential,
                                         'pica8')
        )

    def test_learn(self):
        """test learn."""
        # non-exsiting plugin
        self.assertIsNone(self.manager.learn(self.correct_host,
                                             self.correct_credential,
                                             'huawei', 'xxx'))

        # non-existing vendor
        self.assertIsNone(self.manager.learn(self.correct_host,
                                             self.correct_credential,
                                             'xxxx', 'mac'))


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
