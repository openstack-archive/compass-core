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

"""test hdsdiscovery.utils module."""
from mock import Mock
from mock import patch
import os
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from compass.hdsdiscovery.error import TimeoutError
from compass.hdsdiscovery import utils
from compass.utils import flags
from compass.utils import logsetting


SNMP_V2_CREDENTIALS = {'version': '2c',
                       'community': 'public'}


class UtilsTest(unittest2.TestCase):
    """test huawei switch snmp get."""

    def setUp(self):
        super(UtilsTest, self).setUp()
        logsetting.init()
        self.host = "127.0.0.1"
        self.credentials = SNMP_V2_CREDENTIALS

    def tearDown(self):
        super(UtilsTest, self).tearDown()

    def test_load_module(self):
        """get load_module function."""
        # Successfully load HUAWEI module
        huawei_vendor_path = "/".join(
            (os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.realpath(__file__)))),
             "hdsdiscovery/vendors/huawei")
        )

        # No module found
        self.assertIsNone(utils.load_module("xxx", huawei_vendor_path))

    @patch("compass.hdsdiscovery.utils.exec_command")
    def test_snmpget_by_cl(self, mock_exec_command):
        oid = "sysDescr.0"
        # Incorrect credentials
        incorr_credentials = {"version": "1v", "community": "public"}
        self.assertIsNone(utils.snmpget_by_cl(self.host,
                                              incorr_credentials,
                                              oid))
        # Switch timeout, failed to execute SNMPGET
        mock_exec_command.return_value = (None, "Timeout")
        with self.assertRaises(TimeoutError):
            utils.snmpget_by_cl(self.host, self.credentials, oid)

        # Successfully get system information
        mock_exec_command.return_value = ("Huawei Technologies", None)
        result = utils.snmpget_by_cl(self.host, self.credentials, oid)
        self.assertEqual("Huawei Technologies", result)

    def test_snmpwalk_by_cl(self):
        oid = "BRIDGE-MIB::dot1dTpFdbPort"
        # the result of SNMPWALK is None
        utils.exec_command = Mock(return_value=(None, None))
        result = utils.snmpwalk_by_cl(self.host, self.credentials, oid)
        self.assertEqual([], result)

        # Successfully execute SNMPWALK
        return_value = ("xxx.0.12.41.112.143.193 = INTEGER: 47\n"
                        "xxx.0.12.41.139.17.124 = INTEGER: 47\n")
        expected_result = [
            {"iid": "0.12.41.112.143.193", "value": "47"},
            {"iid": "0.12.41.139.17.124", "value": "47"}
        ]
        utils.exec_command = Mock(return_value=(return_value, None))
        result = utils.snmpwalk_by_cl(self.host, self.credentials, oid)
        self.assertEqual(expected_result, result)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
