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

__author__ = "Grace Yu (grace.yu@huawei.com)"


"""Test deploy_manager module."""

from mock import Mock
import os
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
from copy import deepcopy
reload(setting)


from compass.deployment.deploy_manager import DeployManager
from compass.tests.deployment.test_data import config_data
from compass.utils import flags
from compass.utils import logsetting


class TestDeployManager(unittest2.TestCase):
    """Test DeployManager methods."""
    def setUp(self):
        super(TestDeployManager, self).setUp()

    def tearDown(self):
        super(TestDeployManager, self).tearDown()

    def test_init_DeployManager(self):
        adapter_info = deepcopy(config_data.adapter_test_config)
        cluster_info = deepcopy(config_data.cluster_test_config)
        hosts_info = deepcopy(config_data.hosts_test_config)

        DeployManager._get_installer = Mock()
        DeployManager._get_installer.return_value = "mock_installer"

        test_manager = DeployManager(adapter_info, cluster_info, hosts_info)
        self.assertIsNotNone(test_manager)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
