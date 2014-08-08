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


"""Test Chef installer functionalities regarding to chef server side.
"""

from copy import deepcopy
from mock import Mock
import os
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'

from compass.tests.deployment.test_data import config_data
from compass.utils import setting_wrapper as compass_setting
reload(compass_setting)


from compass.deployment.installers.pk_installers.chef_installer.chef_installer\
    import ChefInstaller


class TestChefInstaller(unittest2.TestCase):
    """Test installer functionality."""
    def setUp(self):
        super(TestChefInstaller, self).setUp()
        self.test_chef = self._get_chef_installer()

    def tearDown(self):
        super(TestChefInstaller, self).tearDown()
        del self.test_chef

    def _get_testchefapi(self):
        import chef
        url = 'https://api.opscode.com/organizations/compasscheftest'
        return chef.ChefAPI(url, config_data.test_client_key, 'graceyu')

    def _get_chef_installer(self):
        adapter_info = deepcopy(config_data.adapter_test_config)
        cluster_info = deepcopy(config_data.cluster_test_config)
        hosts_info = deepcopy(config_data.hosts_test_config)

        ChefInstaller.get_tmpl_path = Mock()
        test_tmpl_dir = os.path.join(os.path.join(config_data.test_tmpl_dir,
                                                  'chef_installer'),
                                     'openstack_icehouse')
        ChefInstaller.get_tmpl_path.return_value = test_tmpl_dir

        ChefInstaller._get_chef_api = Mock()
        ChefInstaller._get_chef_api.return_value = self._get_testchefapi()
        chef_installer = ChefInstaller(adapter_info, cluster_info, hosts_info)
        return chef_installer

    def test_get_tmpl_vars(self):
        pass

    """
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

    def test_get_databagitem_attributes(self):
        vars_dict = {
            "cluster": {
                "deployed_package_config": {
                    "service_credentials": {
                        "nova": {
                            "username": "nova",
                            "password": "compute"
                        }
                    },
                    "users_credentials": {
                        "ksadmin": {
                            "username": "ksadmin",
                            "password": "ksadmin"
                        },
                        "demo": {
                            "username": "demo",
                            "password": "demo"
                        }
                    }
                }
            }
        }
        expected_output = {
            "user_passwords": {
                "admin": {
                    "admin": "admin",
                },
                "ksadmin": {
                    "ksadmin": "ksadmin"
                },
                "demo": {
                    "demo": "demo"
                }
            },
            "db_passwords": {
                "nova": {
                    "nova": "compute",
                },
                "horizon": {
                    "horizon": "horizon"
                },
                "keystone": {
                    "keystone": "keystone"
                }
            }
        }
        databag_dir = os.path.join(self.test_chef.get_tmpl_path(), 'databags')
        databags = self.test_chef.config_manager.get_chef_databag_names()
        for bag in databags:
            tmpl_path = os.path.join(databag_dir, '.'.join((bag, 'tmpl')))
            output = self.test_chef._get_databagitem_attributes(tmpl_path,
                                                                vars_dict)
            self.maxDiff = None
            self.assertDictEqual(expected_output[bag], output)
    """
