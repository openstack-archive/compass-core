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


curr_dir = os.path.dirname(os.path.realpath(__file__))
test_tmpl_dir = os.path.join(curr_dir, 'templates')


adapter_test_config = {
    "name": "openstack_icehouse",
    "distributed_system_name": "openstack_icehouse",
    "roles": ["os-controller", "os-compute-worker", "os-network"],
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
    "pk_installer": {
        "name": "chef_installer",
        "settings": {
            "chef_url": "https://127.0.0.1",
            "key_dir": "xxx",
            "client_name": "xxx"
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
            "management": {
                "interface": "eth0"
            },
            "public": {
                "interface": "eth2"
            },
            "tenant": {
                "interface": "eth1"
            }
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
                "management": {
                    "interface": "vnet0"
                },
                "tenant": {
                    "interface": "vnet1"
                }
            },
            "roles": ["os-controller"]
        }
    },
    2: {
        "host_id": 2,
        "reinstall_os": True,
        "mac": "00:0c:29:3e:60:a1",
        "name": "server02.test",
        "hostname": "server02",
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
            "roles": ["os-compute"]
        }
    },
    3: {
        "host_id": 10,
        "reinstall_os": False,
        "mac_address": "00:0c:29:3e:60:a2",
        "name": "server03.test",
        "hostname": "server03",
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
            "roles": ["os-network"]
        }
    }
}
