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

"""Unit Test for Health Check Moudle"""
import commands
import compass
import logging
import mock
import os
import pwd
import socket
import unittest2
import urllib2
import xmlrpclib
import yum


os.environ['COMPASS_IGNORE_SETTING'] = 'true'

from compass.actions.health_check import base
from compass.actions.health_check import check
from compass.actions.health_check import check_apache
from compass.actions.health_check import check_celery
from compass.actions.health_check import check_dhcp
from compass.actions.health_check import check_dns
from compass.actions.health_check import check_hds
from compass.actions.health_check import check_misc
from compass.actions.health_check import check_os_installer
from compass.actions.health_check import check_package_installer
from compass.actions.health_check import check_squid
from compass.actions.health_check import check_tftp
from compass.actions.health_check import utils as health_check_utils

from compass.utils import flags
from compass.utils import logsetting
from compass.utils import setting_wrapper as setting
reload(setting)


class DummyTest:
    def __init__(self):
        self.rpmdb = self.InnerDummy()
        self.st_mode = 0
        self.pw_name = "dummy"
        self.st_uid = 23
        self.st_gid = 23
        return

    def geturl(self):
        return "dummyurl"

    def get_settings(self):
        dummy_setting = {
            "manage_dhcp": 0,
            "manage_dns": 0,
            "manage_tftp": 0,
        }
        return dummy_setting

    def get_distros(self):
        return []

    def get_repos(self):
        return []

    def get_profiles(self):
        return []

    def check_chef_data(self, data_type, data_type_url):
        return (data_type, [None])

    def login(self, *kwargs):
        return "dummy"

    def check(self, token):
        return ""

    class InnerDummy:
        def __init__(in_self):
            return

        def searchNevra(in_self, name):
            return []


class TestHealthCheck(unittest2.TestCase):

    def setUp(self):
        super(TestHealthCheck, self).setUp()
        logsetting.init()
        self.data_path = '%s/data/test' % os.path.dirname(
            os.path.abspath(__file__))
        self.global_data = {}
        execfile(self.data_path, self.global_data)
        self.dummy = DummyTest()

    def tearDown(self):
        super(TestHealthCheck, self).tearDown()

    def _mock_run(self, service, test_case, expected_code=0):
        if service in ["os_installer", "package_installer"]:
            class_name = service.title().replace("_", "") + "Check"
        else:
            class_name = service.title() + "Check"
        module = eval("check_" + service)
        checker = getattr(module, class_name)()
        code, messages = checker.run()
        contains = False
        for message in messages:
            if all(kw in
                   message for kw in
                   self.global_data[service][test_case][
                       'expected']['keywords']):
                contains = True
                break
        self.assertEqual(code, expected_code)
        self.assertTrue(contains)

    def _test(self, service, test_case):
        data = self.global_data[service]
        module = data[test_case]["mock_module"]
        func = data[test_case]["mock_func"]
        ret = data[test_case]["mock_return"]
        if ret == "self.dummy":
            ret = eval(ret)
        with mock.patch(module + '.' + func) as mock_func:
            logging.info("mocking: %s",
                         str(mock_func))
            setattr(eval(module), func, mock.MagicMock(return_value=ret))
            self._mock_run(service, test_case)

    def test_health_check(self):
        self.global_data.pop("__builtins__", None)
        for service in self.global_data.keys():
            for case in self.global_data[service]:
                self._test(service, case)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
