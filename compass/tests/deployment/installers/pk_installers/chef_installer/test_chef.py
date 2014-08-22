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

from mock import Mock
import os
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'

from compass.deployment.installers.config_manager import BaseConfigManager
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

    def _get_chef_installer(self):
        adapter_info = config_data.adapter_test_config
        cluster_info = config_data.cluster_test_config
        hosts_info = config_data.hosts_test_config

        config_manager = BaseConfigManager(adapter_info, cluster_info,
                                           hosts_info)

        ChefInstaller.get_tmpl_path = Mock()
        test_tmpl_dir = os.path.join(os.path.join(config_data.test_tmpl_dir,
                                                  'chef_installer'),
                                     'openstack_icehouse')
        ChefInstaller.get_tmpl_path.return_value = test_tmpl_dir

        ChefInstaller._get_chef_api = Mock()
        ChefInstaller._get_chef_api.return_value = 'mock_server'
        chef_installer = ChefInstaller(config_manager)
        return chef_installer

    def test_get_tmpl_vars(self):
        pass

    def test_get_node_attributes(self):
        cluster_dict = self.test_chef._get_cluster_tmpl_vars()
        vars_dict = self.test_chef._get_host_tmpl_vars(2, cluster_dict)
        expected_node_attr = {
            "override_attributes": {
                "openstack": {
                    "endpoints": {
                        "compute-vnc-bind": {
                            "host": "12.234.32.101"
                        }
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
        databags = self.test_chef.get_chef_databag_names()
        for bag in databags:
            tmpl_path = os.path.join(databag_dir, '.'.join((bag, 'tmpl')))
            output = self.test_chef._get_databagitem_attributes(tmpl_path,
                                                                vars_dict)
            self.maxDiff = None
            self.assertDictEqual(expected_output[bag], output)

    def test_clean_log(self):
        host_id = 1
        fullname = self.test_chef.config_manager.get_host_fullname(host_id)
        test_log_dir = os.path.join('/tmp', fullname)
        if not os.path.exists(test_log_dir):
            os.makedirs(test_log_dir)

        self.test_chef._clean_log('/tmp', fullname)
        self.assertFalse(os.path.exists(test_log_dir))

    def test_deploy(self):
        expected_output = {
            "cluster": {
                "id": 1,
                "name": "test",
                "os_name": "Ubuntu-12.04-x86_64",
                "deployed_package_config": {
                    "service_credentials": {
                        "mq": {
                            "username": "guest",
                            "password": "test"
                        }
                    },
                    "roles_mapping": {
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
                }
            },
            "hosts": {
                1: {
                    "deployed_package_config": {
                        "roles_mapping": {
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
                            }
                        },
                        "service_credentials": {
                            "mq": {
                                "username": "guest",
                                "password": "test"
                            }
                        }
                    }
                },
                2: {
                    "deployed_package_config": {
                        "roles_mapping": {
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
                            }
                        },
                        "service_credentials": {
                            "mq": {
                                "username": "guest",
                                "password": "test"
                            }
                        }
                    }
                },
                3: {
                    "deployed_package_config": {
                        "roles_mapping": {
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
                        },
                        "service_credentials": {
                            "mq": {
                                "username": "guest",
                                "password": "test"
                            }
                        }
                    }
                }
            }
        }
        self.test_chef.update_environment = Mock()
        self.test_chef.update_databags = Mock()
        self.test_chef.get_node = Mock()
        self.test_chef.update_node = Mock()

        output = self.test_chef.deploy()
        self.maxDiff = None
        self.assertDictEqual(expected_output, output)

    def test_generate_installer_config(self):
        test_data = [
            {
                "settings": {
                    "chef_url": "https://127.0.0.1",
                    "chef_server_dns": "test_chef",
                    "key_dir": "xxx",
                    "client_name": "xxx",
                    "databags": ["user_passwords", "db_passwords"]
                },
                "excepted_output": {
                    1: {
                        "tool": "chef",
                        "chef_url": "https://127.0.0.1",
                        "chef_node_name": "test_node",
                        "chef_client_name": "test_node",
                        "chef_server_ip": "127.0.0.1",
                        "chef_server_dns": "test_chef"
                    }
                }
            },
            {
                "settings": {
                    "chef_url": "https://test_chef",
                    "chef_server_ip": "127.0.0.1",
                    "key_dir": "xxx",
                    "client_name": "xxx",
                    "databags": ["user_passwords", "db_passwords"]
                },
                "excepted_output": {
                    1: {
                        "tool": "chef",
                        "chef_url": "https://test_chef",
                        "chef_node_name": "test_node",
                        "chef_client_name": "test_node",
                        "chef_server_ip": "127.0.0.1",
                        "chef_server_dns": "test_chef"
                    }
                }
            },
            {
                "settings": {
                    "chef_url": "https://test_chef",
                    "key_dir": "xxx",
                    "client_name": "xxx",
                    "databags": ["user_passwords", "db_passwords"]
                },
                "excepted_output": {
                    1: {
                        "tool": "chef",
                        "chef_url": "https://test_chef",
                        "chef_node_name": "test_node",
                        "chef_client_name": "test_node"
                    }
                }
            }
        ]
        nname = 'test_node'
        self.test_chef.config_manager.get_host_id_list = Mock()
        self.test_chef.config_manager.get_host_id_list.return_value = [1]
        self.test_chef.config_manager.get_host_fullname = Mock()
        self.test_chef.config_manager.get_host_fullname.return_value = nname

        for entry in test_data:
            chef_config = entry["settings"]
            chef_url = chef_config["chef_url"]
            self.test_chef.installer_url = chef_url
            self.test_chef.config_manager.get_pk_installer_settings = Mock()
            self.test_chef.config_manager.get_pk_installer_settings\
                .return_value = chef_config

            output = self.test_chef.generate_installer_config()
            self.maxDiff = None
            self.assertDictEqual(entry["excepted_output"], output)
