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


from compass.utils import setting_wrapper as compass_setting
reload(compass_setting)

import config_data

from compass.deployment.installers.config_manager import BaseConfigManager

from compass.utils import flags
from compass.utils import logsetting

from plugins.chef_installer.implementation.chef_installer import ChefInstaller


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
        test_tmpl_dir = os.path.join(
            os.path.join(config_data.test_plugins_dir,
                         'templates'),
            'openstack_icehouse'
        )
        ChefInstaller.get_tmpl_path.return_value = test_tmpl_dir

        ChefInstaller._get_chef_api = Mock()
        ChefInstaller._get_chef_api.return_value = 'mock_server'
        ChefInstaller.get_all_roles = Mock()
        ChefInstaller.get_all_roles.return_value = []
        ChefInstaller.validate_roles = Mock()
        ChefInstaller.validate_roles.return_value = True
        chef_installer = ChefInstaller(config_manager)
        return chef_installer

    def test_get_tmpl_vars(self):
        pass

    def test_get_node_attributes(self):
        cluster_dict = self.test_chef._get_cluster_tmpl_vars()
        vars_dict = self.test_chef._get_host_tmpl_vars(2, cluster_dict)
        expected_node_attr = {
            "override": {
                "openstack": {
                    "endpoints": {
                        "compute-vnc-bind": {
                            "host": "12.234.32.101"
                        }
                    }
                }
            }
        }
        output = self.test_chef._generate_node_attributes(
            ['os-compute-worker'], vars_dict
        )
        self.maxDiff = None
        self.assertDictEqual(expected_node_attr, output)

    def test_get_env_attributes(self):
        expected_env = {
            "chef_type": "environment",
            "name": "testing",
            "description": "Environment",
            "cookbook_versions": {
            },
            "json_class": "Chef::Environment",
            "override_attributes": {
                "compass": {
                    "cluster_id": "1"
                }
            },
            "default_attributes": {
                "local_repo": "",
                "memcached": {
                    "bind_interface": "vnet0"
                },
                "compute": {
                    "xvpvnc_proxy": {
                        "bind_interface": "eth0"
                    },
                    "syslog": {
                        "use": False
                    },
                    "novnc_proxy": {
                        "bind_interface": "vnet0"
                    },
                    "libvirt": {
                        "bind_interface": "eth0"
                    }
                },
                "network": {
                    "l3": {
                        "external_network_bridge_interface": "eth2"
                    }
                },
                "mysql": {
                    "server_root_password": "root",
                    "server_repl_password": "root",
                    "root_network_acl": "%",
                    "allow_remote_root": True,
                    "server_debian_password": "root"
                },
                "mq": {
                    "vhost": "/nova",
                    "password": "test",
                    "user": "guest",
                    "network": {
                        "service_type": "rabbitmq"
                    }
                },
                "openstack": {
                    "image": {
                        "upload_images": ["cirros"],
                        "syslog": {
                            "use": False
                        },
                        "api": {
                            "bind_interface": "vnet0"
                        },
                        "registry": {
                            "bind_interface": "vnet0"
                        },
                        "debug": True,
                        "upload_image": {
                            "cirros": "http://download.cirros-cloud.net"
                                      "/0.3.2/cirros-0.3.2-x86_64-disk.img"
                        }
                    },
                    "db": {
                        "volume": {
                            "host": "12.234.32.100"
                        },
                        "compute": {
                            "host": "12.234.32.100"
                        },
                        "network": {
                            "host": "12.234.32.100"
                        },
                        "orchestration": {
                            "host": "12.234.32.100"
                        },
                        "bind_interface": "vnet0",
                        "image": {
                            "host": "12.234.32.100"
                        },
                        "telemetry": {
                            "host": "12.234.32.100"
                        },
                        "identity": {
                            "host": "12.234.32.100"
                        },
                        "dashboard": {
                            "host": "12.234.32.100"
                        }
                    },
                    "auth": {
                        "validate_certs": False
                    },
                    "use_databags": False,
                    "developer_mode": True,
                    "block-storage": {
                        "debug": True,
                        "syslog": {
                            "use": False
                        },
                        "api": {
                            "ratelimit": "False"
                        }
                    },
                    "compute": {
                        "xvpvnc_proxy": {
                            "bind_interface": "eth0"
                        },
                        "network": {
                            "service_type": "neutron"
                        },
                        "libvirt": {
                            "bind_interface": "eth0"
                        },
                        "syslog": {
                            "use": False
                        },
                        "ratelimit": {
                            "volume": {
                                "enabled": False
                            },
                            "api": {
                                "enabled": False
                            }
                        },
                        "novnc_proxy": {
                            "bind_interface": "eth0"
                        }
                    },
                    "network": {
                        "verbose": "True",
                        "openvswitch": {
                            "network_vlan_ranges": "",
                            "enable_tunneling": "True",
                            "bind_interface": "eth1",
                            "tenant_network_type": "gre",
                            "bridge_mappings": "",
                            "tunnel_id_ranges": "1:1000"
                        },
                        "ml2": {
                            "type_drivers": "gre",
                            "tenant_network_types": "gre",
                            "enable_security_group": "True",
                            "network_vlan_ranges": "",
                            "tunnel_id_ranges": "1:1000"
                        },
                        "l3": {
                            "external_network_bridge_interface": "eth2"
                        },
                        "debug": "True",
                        "service_plugins": ["router"]
                    },
                    "mq": {
                        "vhost": "/nova",
                        "password": "guest",
                        "user": "guest",
                        "network": {
                            "service_type": "rabbitmq"
                        }
                    },
                    "dashboard": {
                        "use_ssl": "false"
                    },
                    "identity": {
                        "syslog": {
                            "use": False
                        },
                        "token": {
                            "backend": "sql"
                        },
                        "admin_user": "admin",
                        "users": {
                            "admin": {
                                "password": "admin",
                                "default_tenant": "admin",
                                "roles": {
                                    "admin": ["admin"]
                                }
                            },
                            "demo": {
                                "password": "demo",
                                "default_tenant": "demo",
                                "roles": {
                                    "member": ["demo"]
                                }
                            }
                        },
                        "roles": ["admin", "member"],
                        "bind_interface": "vnet0",
                        "debug": True,
                        "tenants": ["admin", "service", "demo"],
                        "catalog": {
                            "backend": "sql"
                        }
                    },
                    "endpoints": {
                        "telemetry-api": {
                            "path": "/v1",
                            "host": "12.234.32.100",
                            "scheme": "http",
                            "port": "8777"
                        },
                        "compute-api": {
                            "path": "/v2/%(tenant_id)s",
                            "host": "12.234.32.100",
                            "scheme": "http",
                            "port": "8774"
                        },
                        "identity-admin": {
                            "path": "/v2.0",
                            "host": "12.234.32.100",
                            "scheme": "http",
                            "port": "35357"
                        },
                        "image-api-bind": {
                            "bind_interface": "vnet0"
                        },
                        "image-registry": {
                            "path": "/v2",
                            "host": "12.234.32.100",
                            "scheme": "http",
                            "port": "9191"
                        },
                        "orchestration-api-cfn": {
                            "path": "/v1",
                            "host": "12.234.32.100",
                            "scheme": "http",
                            "port": "8000"
                        },
                        "vnc_bind": {
                            "bind_interface": "vnet0"
                        },
                        "image-registry-bind": {
                            "bind_interface": "vnet0"
                        },
                        "orchestration-api": {
                            "path": "/v1/%(tenant_id)s",
                            "host": "12.234.32.100",
                            "scheme": "http",
                            "port": "8004"
                        },
                        "block-storage-api-bind": {
                            "bind_interface": "vnet0"
                        },
                        "identity-api": {
                            "path": "/v2.0",
                            "host": "12.234.32.100",
                            "scheme": "http",
                            "port": "5000"
                        },
                        "network-api-bind": {
                            "bind_interface": "eth0"
                        },
                        "block-storage-api": {
                            "path": "/v1/%(tenant_id)s",
                            "host": "12.234.32.100",
                            "scheme": "http",
                            "port": "8776"
                        },
                        "db": {
                            "host": "12.234.32.100"
                        },
                        "compute-api-bind": {
                            "bind_interface": "vnet0"
                        },
                        "compute-novnc": {
                            "path": "/vnc_auto.html",
                            "host": "12.234.32.100",
                            "scheme": "http",
                            "port": "6080"
                        },
                        "image-api": {
                            "path": "/v2",
                            "host": "12.234.32.100",
                            "scheme": "http",
                            "port": "9292"
                        },
                        "compute-vnc-bind": {
                            "bind_interface": "eth0"
                        },
                        "identity-bind": {
                            "bind_interface": "vnet0"
                        },
                        "network-api": {
                            "path": "",
                            "host": "12.234.32.103",
                            "scheme": "http",
                            "port": "9696"
                        },
                        "mq": {
                            "host": "12.234.32.100"
                        },
                        "compute-ec2-admin": {
                            "path": "/services/Admin",
                            "host": "12.234.32.100",
                            "scheme": "http",
                            "port": "8773"
                        },
                        "compute-novnc-bind": {
                            "bind_interface": "vnet0"
                        },
                        "compute-ec2-api": {
                            "path": "/services/Cloud",
                            "host": "12.234.32.100",
                            "scheme": "http",
                            "port": "8773"
                        }
                    }
                },
                "db": {
                    "compute": {
                        "host": "12.234.32.100"
                    },
                    "identity": {
                        "host": "12.234.32.100"
                    },
                    "bind_interface": "vnet0"
                },
                "collectd": {
                    "server": {
                        "host": "metrics",
                        "protocol": "tcp",
                        "port": "4242"
                    }
                }
            }
        }
        vars_dict = self.test_chef._get_cluster_tmpl_vars()
        output = self.test_chef._generate_env_attributes(vars_dict)
        self.maxDiff = None
        self.assertDictEqual(expected_env, output)

    def test_get_databagitem_attributes(self):
        vars_dict = {
            "package_config": {
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
            output = self.test_chef._generate_databagitem_attributes(tmpl_path,
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
                "deployed_package_config": {
                    "service_credentials": {
                        "mq": {
                            "username": "guest",
                            "password": "test"
                        }
                    },
                    "roles_mapping": {
                        "os_controller": [{
                            "hostname": "server01",
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
                        }],
                        "os_compute_worker": [{
                            "hostname": "server02",
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
                        }, {
                            "hostname": "server03",
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
                        }],
                        "os_network": [{
                            "hostname": "server03",
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
                        }]
                    }
                }
            },
            "hosts": {
                1: {
                    "deployed_package_config": {
                        "roles_mapping": {
                            "os_controller": {
                                "hostname": "server01",
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
                            "os_compute_worker": {
                                "hostname": "server02",
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
                                "hostname": "server03",
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
                            "os_compute_worker": {
                                "hostname": "server03",
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
        self.test_chef.upload_environment = Mock()
        self.test_chef.update_databags = Mock()
        self.test_chef.get_create_node = Mock()
        self.test_chef.add_roles = Mock()

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


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
