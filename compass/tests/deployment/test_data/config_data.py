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

__author__ = "Grace Yu (grace.yu@huawei.com)"

import os
os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as compass_setting
reload(compass_setting)


curr_dir = os.path.dirname(os.path.realpath(__file__))
test_tmpl_dir = os.path.join(curr_dir, 'templates')

test_chef_url = compass_setting.TEST_CHEF_URL
test_client_key = compass_setting.TEST_CLIENT_KEY_PATH
test_client = compass_setting.TEST_CLIENT_NAME


adapter_test_config = {
    "name": "openstack_icehouse",
    "distributed_system_name": "openstack_icehouse",
    "flavors": [
        {
            "falvor_name": "test_flavor",
            "roles": ["os-controller", "os-compute-worker", "os-network"],
            "template": "multinodes.tmpl"
        }
    ],
    "os_installer": {
        "name": "cobbler",
        "settings": {
            "cobbler_url": "http://127.0.0.1/cobbler_api",
            "credentials": {
                "username": "cobbler",
                "password": "cobbler"
            }
        }
    },
    "package_installer": {
        "name": "chef_installer",
        "settings": {
            "chef_url": "https://127.0.0.1",
            "chef_server_ip": "127.0.0.1",
            "chef_server_dns": "test_chef",
            "key_dir": "xxx",
            "client_name": "xxx",
            "databags": ["user_passwords", "db_passwords"]
        }
    },
    "metadata": {
        "os_config": {
            "_self": {},
            "general": {
                "_self": {"mapping_to": ""},
                "language": {
                    "_self": {
                        "mapping_to": "language",
                    },
                },
                "timezone": {
                    "_self": {
                        "mapping_to": "timezone"
                    }
                },
                "default_gateway": {
                    "_self": {
                        "mapping_to": "gateway"
                    }
                },
                "domain": {
                    "_self": {"mapping_to": ""}
                },
                "http_proxy": {
                    "_self": {
                        "mapping_to": "http_proxy"
                    }
                },
                "ntp_server": {
                    "_self": {"mapping_to": "ntp_server"}
                },
                "dns_servers": {
                    "_self": {"mapping_to": "nameservers"}
                },
                "search_path": {
                    "_self": {"mapping_to": "search_path"}
                },
                "https_proxy": {
                    "_self": {"mapping_to": "https_proxy"}
                }
            },
            "partition": {
                "_self": {
                    "mapping_to": "partition"
                },
                "$path": {
                    "_self": {"mapping_to": ""},
                    "max_size": {
                        "_self": {"mapping_to": "vol_size"}
                    },
                    "size_percentage": {
                        "_self": {"mapping_to": "vol_percentage"}
                    }
                }
            },
            "server_credentials": {
                "_self": {
                    "mapping_to": "server_credentials"
                },
                "username": {
                    "_self": {"mapping_to": "username"}
                },
                "password": {
                    "_self": {"mapping_to": "password"}
                }
            }
        },
        "package_config": {
            "_self": {},
            "security": {
                "_self": {},
                "service_credentials": {
                    "_self": {
                        "mapping_to": "service_credentials"
                    },
                    "rabbit_mq": {
                        "_self": {
                            "mapping_to": "mq"
                        },
                        "username": {
                            "_self": {
                                "mapping_to": "username"
                            }
                        },
                        "password": {
                            "_self": {
                                "mapping_to": "password"
                            }
                        }
                    }
                }
            },
            "network_mapping": {
                "_self": {},
                "management": {
                    "_self": {},
                    "interface": {
                        "_self": {}
                    }
                },
                "public": {
                    "_self": {},
                    "interface": {
                        "_self": {}
                    }
                },
                "tenant": {
                    "_self": {},
                    "interface": {
                        "_self": {}
                    }
                }
            },
            "roles": {
                "_self": {}
            }
        }
    }
}


cluster_test_config = {
    "id": 1,
    "os_name": "Ubuntu-12.04-x86_64",
    "name": "test",
    "flavor": {
        "falvor_name": "test_flavor",
        "roles": ["os-controller", "os-compute-worker", "os-network"],
        "template": "multinodes.tmpl"
    },
    "os_config": {
        "general": {
            "language": "EN",
            "timezone": "UTC",
            "default_gateway": "12.234.32.1",
            "domain": "ods.com",
            "http_proxy": "http://127.0.0.1:3128",
            "https_proxy": "",
            "ntp_server": "127.0.0.1",
            "dns_servers": ["127.0.0.1"],
            "search_path": ["1.ods.com", "ods.com"]
        },
        "partition": {
            "/var": {
                "max_size": 20,
                "size_percentage": 20
            },
            "/home": {
                "max_size": 50,
                "size_percentage": 40
            }
        },
        "server_credentials": {
            "username": "root",
            "password": "huawei"
        }
    },
    "package_config": {
        "security": {
            "service_credentials": {
                "rabbit_mq": {
                    "username": "guest",
                    "password": "test"
                }
            }
        },
        "network_mapping": {
            "management": "eth0",
            "public": "eth2",
            "tenant": "eth1"
        }
    }
}

hosts_test_config = {
    1: {
        "host_id": 1,
        "reinstall_os": True,
        "mac": "00:0c:29:3e:60:e9",
        "name": "server01.test",
        "hostname": "server01",
        "roles": ["os-controller"],
        "networks": {
            "vnet0": {
                "ip": "12.234.32.100",
                "netmask": "255.255.255.0",
                "is_mgmt": True,
                "is_promiscuous": False,
                "subnet": "12.234.32.0/24"
            },
            "vnet1": {
                "ip": "172.16.1.1",
                "netmask": "255.255.255.0",
                "is_mgmt": False,
                "is_promiscuous": False,
                "subnet": "172.16.1.0/24"
            }
        },
        "os_config": {
            "general": {
                "default_gateway": "10.145.88.1",
            },
            "partition": {
                "/var": {
                    "max_size": 30,
                    "size_percentage": 30
                },
                "/test": {
                    "max_size": 10,
                    "size_percentage": 10
                }
            }
        },
        "package_config": {
            "network_mapping": {
                "management": "vnet0",
                "tenant": "vnet1"
            }
        }
    },
    2: {
        "host_id": 2,
        "reinstall_os": True,
        "mac": "00:0c:29:3e:60:a1",
        "name": "server02.test",
        "hostname": "server02",
        "roles": ["os-compute"],
        "networks": {
            "eth0": {
                "ip": "12.234.32.101",
                "netmask": "255.255.255.0",
                "is_mgmt": True,
                "is_promiscuous": False,
                "subnet": "12.234.32.0/24"
            },
            "eth1": {
                "ip": "172.16.1.2",
                "netmask": "255.255.255.0",
                "is_mgmt": False,
                "is_promiscuous": False,
                "subnet": "172.16.1.0/24"
            }
        },
        "os_config": {
            "general": {
                "language": "EN",
                "timezone": "UTC",
                "domain": "ods.com"
            },
            "partition": {
                "/test": {
                    "max_size": 10,
                    "size_percentage": 20
                }
            }
        },
        "package_config": {
        }
    },
    3: {
        "host_id": 10,
        "reinstall_os": False,
        "mac": "00:0c:29:3e:60:a2",
        "name": "server03.test",
        "hostname": "server03",
        "roles": ["os-network", "os-compute"],
        "networks": {
            "eth0": {
                "ip": "12.234.32.103",
                "netmask": "255.255.255.0",
                "is_mgmt": True,
                "is_promiscuous": False,
                "subnet": "12.234.32.0/24"
            },
            "eth1": {
                "ip": "172.16.1.3",
                "netmask": "255.255.255.0",
                "is_mgmt": False,
                "is_promiscuous": False,
                "subnet": "172.16.1.0/24"
            },
            "eth2": {
                "ip": "10.0.0.1",
                "netmask": "255.255.255.0",
                "is_mgmt": False,
                "is_promiscuous": True,
                "subnet": "10.0.0.0/24"
            }
        },
        "ipmi_credentials": {
            "ip": "172.16.100.104",
            "username": "admin",
            "password": "admin"
        },
        "os_config": {
            "general": {
                "language": "EN",
                "timezone": "UTC",
                "default_gateway": "12.234.32.1",
                "domain": "ods.com",
                "http_proxy": "http://10.145.88.211:3128",
                "https_proxy": "",
                "ntp_server": "10.145.88.211",
                "dns_servers": "10.145.88.211",
                "search_path": "1.ods.com ods.com"
            },
            "partition": {
                "/var": {
                    "max_size": 20,
                    "size_percentage": 20
                },
                "/home": {
                    "max_size": 50,
                    "size_percentage": 40
                }
            }
        },
        "package_config": {
        }
    }
}


metadata_test_cases = [
    {
        "metadata": {
            "general": {
                "_self": {},
                "language": {
                    "_self": {"mapping_to": "lan"}
                },
                "timezone": {
                    "_self": {"mapping_to": "timezone"}
                }
            }
        },
        "config": {
            "general": {
                "language": "EN",
                "timezone": "UTC"
            }
        },
        "expected_output": {
            "lan": "EN",
            "timezone": "UTC"
        }
    },
    {
        "metadata": {
            "security": {
                "_self": {"mapping_to": "security"},
                "$credentials": {
                    "_self": {},
                    "$service": {
                        "username": {
                            "_self": {"mapping_to": "user"}
                        },
                        "password": {
                            "_self": {"mapping_to": "pass"}
                        }
                    }
                }
            },
            "test": {
                "_self": {"mapping_to": "test_section"},
                "item1": {
                    "_self": {"mapping_to": "itema"}
                },
                "item2": {
                    "_self": {"mapping_to": "itemb"}
                }
            }
        },
        "config": {
            "security": {
                "service_credentials": {
                    "glance": {"username": "glance", "password": "glance"},
                    "identity": {"username": "keystone",
                                 "password": "keystone"},
                    "dash": {"username": "dash", "password": "dash"}
                },
                "db_credentials": {
                    "mysql": {"username": "root", "password": "root"},
                    "rabbit_mq": {"username": "guest", "password": "guest"}
                }
            },
            "test": {
                "item1": "a",
                "item2": "b"
            }
        },
        "expected_output": {
            "security": {
                "service_credentials": {
                    "glance": {"user": "glance", "pass": "glance"},
                    "identity": {"user": "keystone", "pass": "keystone"},
                    "dash": {"user": "dash", "pass": "dash"}
                },
                "db_credentials": {
                    "mysql": {"user": "root", "pass": "root"},
                    "rabbit_mq": {"user": "guest", "pass": "guest"}
                }
            },
            "test_section": {
                "itema": "a",
                "itemb": "b"
            }
        }
    }
]
