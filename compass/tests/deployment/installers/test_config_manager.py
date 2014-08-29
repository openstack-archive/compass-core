# Copyright 2014 Huawei Technologies Co. Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test config_manager module."""

import os
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'

from compass.deployment.installers.config_manager import BaseConfigManager
from compass.deployment.utils import constants as const
from compass.tests.deployment.test_data import config_data
from compass.utils import setting_wrapper as compass_setting
reload(compass_setting)


class TestConfigManager(unittest2.TestCase):
    """Test ConfigManager methods."""
    def setUp(self):
        super(TestConfigManager, self).setUp()
        self.adapter_test_info = config_data.adapter_test_config
        self.cluster_test_info = config_data.cluster_test_config
        self.hosts_test_info = config_data.hosts_test_config
        self.test_config_manager = BaseConfigManager(self.adapter_test_info,
                                                     self.cluster_test_info,
                                                     self.hosts_test_info)

    def tearDown(self):
        super(TestConfigManager, self).tearDown()
        del self.test_config_manager

    def test_get_cluster_baseinfo(self):
        expected_output = {
            "id": 1,
            "name": "test",
            "os_name": "Ubuntu-12.04-x86_64"
        }
        output = self.test_config_manager.get_cluster_baseinfo()
        self.maxDiff = None
        self.assertDictEqual(expected_output, output)

    def test_get_host_id_list(self):
        expected_output = [1, 2, 3]
        output = self.test_config_manager.get_host_id_list()
        self.assertEqual(expected_output, output)

    def test_get_cluster_flavor_info(self):
        expected_output = self.cluster_test_info[const.FLAVOR]
        output = self.test_config_manager.get_cluster_flavor_info()
        self.assertDictEqual(expected_output, output)

    def test_get_cluster_roles_mapping(self):
        expected_output = {
            "os_controller": {
                "management": {
                    "interface": "vnet0",
                    "ip": "12.234.32.100",
                    "netmask": "255.255.255.0",
                    "is_mgmt": True,
                    "is_promiscuous": False,
                    "subnet": "12.234.32.0/24"
                },
                "tenant": {
                    "interface": "vnet1",
                    "ip": "172.16.1.1",
                    "netmask": "255.255.255.0",
                    "is_mgmt": False,
                    "is_promiscuous": False,
                    "subnet": "172.16.1.0/24"
                }
            },
            "os_compute": {
                "management": {
                    "interface": "eth0",
                    "ip": "12.234.32.101",
                    "netmask": "255.255.255.0",
                    "is_mgmt": True,
                    "is_promiscuous": False,
                    "subnet": "12.234.32.0/24"
                },
                "tenant": {
                    "interface": "eth1",
                    "ip": "172.16.1.2",
                    "netmask": "255.255.255.0",
                    "is_mgmt": False,
                    "is_promiscuous": False,
                    "subnet": "172.16.1.0/24"
                }
            },
            "os_network": {
                "management": {
                    "interface": "eth0",
                    "ip": "12.234.32.103",
                    "netmask": "255.255.255.0",
                    "is_mgmt": True,
                    "is_promiscuous": False,
                    "subnet": "12.234.32.0/24"
                },
                "tenant": {
                    "interface": "eth1",
                    "ip": "172.16.1.3",
                    "netmask": "255.255.255.0",
                    "is_mgmt": False,
                    "is_promiscuous": False,
                    "subnet": "172.16.1.0/24"
                },
                "public": {
                    "interface": "eth2",
                    "ip": "10.0.0.1",
                    "netmask": "255.255.255.0",
                    "is_mgmt": False,
                    "is_promiscuous": True,
                    "subnet": "10.0.0.0/24"
                }
            }
        }
        self.maxDiff = None
        output = self.test_config_manager.get_cluster_roles_mapping()
        self.assertEqual(expected_output, output)

    def test_get_host_role_mapping(self):
        expected_output = {
            "os_network": {
                "management": {
                    "interface": "eth0",
                    "ip": "12.234.32.103",
                    "netmask": "255.255.255.0",
                    "is_mgmt": True,
                    "is_promiscuous": False,
                    "subnet": "12.234.32.0/24"
                },
                "tenant": {
                    "interface": "eth1",
                    "ip": "172.16.1.3",
                    "netmask": "255.255.255.0",
                    "is_mgmt": False,
                    "is_promiscuous": False,
                    "subnet": "172.16.1.0/24"
                },
                "public": {
                    "interface": "eth2",
                    "ip": "10.0.0.1",
                    "netmask": "255.255.255.0",
                    "is_mgmt": False,
                    "is_promiscuous": True,
                    "subnet": "10.0.0.0/24"
                }
            },
            "os_compute": {
                "management": {
                    "interface": "eth0",
                    "ip": "12.234.32.103",
                    "netmask": "255.255.255.0",
                    "is_mgmt": True,
                    "is_promiscuous": False,
                    "subnet": "12.234.32.0/24"
                },
                "tenant": {
                    "interface": "eth1",
                    "ip": "172.16.1.3",
                    "netmask": "255.255.255.0",
                    "is_mgmt": False,
                    "is_promiscuous": False,
                    "subnet": "172.16.1.0/24"
                },
                "public": {
                    "interface": "eth2",
                    "ip": "10.0.0.1",
                    "netmask": "255.255.255.0",
                    "is_mgmt": False,
                    "is_promiscuous": True,
                    "subnet": "10.0.0.0/24"
                }
            }
        }
        self.maxDiff = None
        output = self.test_config_manager.get_host_roles_mapping(3)
        self.assertEqual(expected_output, output)
