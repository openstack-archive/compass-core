#!/usr/bin/python
#
# Copyright 2014 Openstack Foundation
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
"""test config provider module.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import os
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from compass.config_management.providers import config_provider
from compass.utils import flags
from compass.utils import logsetting


class DummyProvider(config_provider.ConfigProvider):
    """Dummy provider."""

    NAME = 'dummy'

    def __init__(self):
        super(DummyProvider, self).__init__()


class Dummy2Provider(config_provider.ConfigProvider):
    """another dummy provider."""

    NAME = 'dummy'

    def __init__(self):
        super(Dummy2Provider, self).__init__()


class TestProviderRegisterFunctions(unittest2.TestCase):
    """test provider register."""

    def setUp(self):
        super(TestProviderRegisterFunctions, self).setUp()
        logsetting.init()
        self.config_provider_backup_ = config_provider.PROVIDERS
        config_provider.PROVIDERS = {}

    def tearDown(self):
        config_provider.PROVIDERS = self.config_provider_backup_
        super(TestProviderRegisterFunctions, self).tearDown()

    def test_found_provider(self):
        """test found provider."""
        config_provider.register_provider(DummyProvider)
        provider = config_provider.get_provider_by_name(
            DummyProvider.NAME)
        self.assertIsInstance(provider, DummyProvider)

    def test_notfound_unregistered_provider(self):
        """test notfound unregistered provider."""
        self.assertRaises(KeyError, config_provider.get_provider_by_name,
                          DummyProvider.NAME)

    def test_multi_registered_provider(self):
        """tst register multi provider with the same name."""
        config_provider.register_provider(DummyProvider)
        self.assertRaises(KeyError, config_provider.register_provider,
                          Dummy2Provider)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
