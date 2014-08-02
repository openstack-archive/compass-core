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


"""Test Chef installer module.
"""

from copy import deepcopy
from mock import Mock
import os
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as compass_setting
reload(compass_setting)

from compass.db.api import database
from compass.deployment.installers.pk_installers.chef_installer.chef_installer\
    import ChefInstaller
from compass.tests.deployment.test_data import config_data
from compass.utils import flags
from compass.utils import logsetting

class TestChefInstaller(unittest2.TestCase):
    """Test installer functionality."""
    def setUp(self):
        super(TestChefInstaller, self).setUp()
        logsetting.init()
        database.init('sqlite://')
        self.test_chef = self._get_chef_installer()

    def tearDown(self):
        super(TestChefInstaller, self).tearDown()

    def _get_chef_installer(self):
        adapter_info = deepcopy(config_data.adapter_test_config)
        cluster_info = deepcopy(config_data.cluster_test_config)
        hosts_info = deepcopy(config_data.hosts_test_config)

        ChefInstaller._get_chef_api = Mock()
        ChefInstaller._get_chef_api.return_value = 'mock_server'
        chef_installer = ChefInstaller(adapter_info, cluster_info, hosts_info)
        return chef_installer

    def test_get_tmpl_vars(self):
        pass

    def test_get_node_attributes(self):
        cluster_dict = self.test_chef._get_cluster_tmpl_vars()
        vars_dict = self.test_chef._get_host_tmpl_vars(2, cluster_dict)
        expected_node_attr = {
            "override_attributes": {
                "endpoints": {
                    "compute-vnc-bind": {
                        "host": "12.234.32.101"
                    }
                }
            }
        }
        output = self.test_chef._get_node_attributes(['os-compute'], vars_dict)
        self.maxDiff = None
        self.assertDictEqual(expected_node_attr, output)

    def test_get_env_attributes(self):
        expected_env = {
            "name": "testing",
            "description": "Environment",
            "cookbook_versions": {
            },
            "json_class": "Chef::Environment",
            "chef_type": "environment",
            "default_attributes": {
            },
            "override_attributes": {
                "compute": {
                    "syslog": {
                        "use": False
                    },
                    "libvirt": {
                        "bind_interface": "eth0"
                    },
                    "novnc_proxy": {
                        "bind_interface": "vnet0"
                    },
                    "xvpvnc_proxy": {
                        "bind_interface": "eth0"
                    }
                },
                "db": {
                    "bind_interface": "vnet0",
                    "compute": {
                        "host": "12.234.32.100"
                    },
                    "identity": {
                        "host": "12.234.32.100"
                    }
                },
                "mq": {
                    "user": "guest",
                    "password": "test",
                    "vhost": "/nova",
                    "network": {
                        "service_type": "rabbitmq"
                    }
                }
            }
        }
        vars_dict = self.test_chef._get_cluster_tmpl_vars()
        output = self.test_chef._get_env_attributes(vars_dict)
        self.maxDiff = None
        self.assertDictEqual(expected_env, output)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
