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

"""test os installer module.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import os
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from compass.config_management.installers import os_installer
from compass.utils import flags
from compass.utils import logsetting


class DummyInstaller(os_installer.Installer):
    """dummy installer."""

    NAME = 'dummy'

    def __init__(self):
        super(DummyInstaller, self).__init__()


class Dummy2Installer(os_installer.Installer):
    """another dummy installer."""

    NAME = 'dummy'

    def __init__(self):
        super(Dummy2Installer, self).__init__()


class TestInstallerFunctions(unittest2.TestCase):
    """test installer functions."""

    def setUp(self):
        super(TestInstallerFunctions, self).setUp()
        logsetting.init()
        self.installers_backup_ = os_installer.INSTALLERS
        os_installer.INSTALLERS = {}

    def tearDown(self):
        os_installer.INSTALLERS = self.installers_backup_
        super(TestInstallerFunctions, self).tearDown()

    def test_found_installer(self):
        """test found installer."""
        os_installer.register(DummyInstaller)
        intaller = os_installer.get_installer_by_name(DummyInstaller.NAME)
        self.assertIsInstance(intaller, DummyInstaller)

    def test_notfound_unregistered_installer(self):
        """test not found unregistered installer."""
        self.assertRaises(KeyError, os_installer.get_installer_by_name,
                          DummyInstaller.NAME)

    def test_multi_registered_installer(self):
        """test register multi installers with the same name."""
        os_installer.register(DummyInstaller)
        self.assertRaises(KeyError, os_installer.register, Dummy2Installer)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
