import functools
import unittest2

from compass.config_management.utils import config_merger
from compass.config_management.utils import config_merger_callbacks
from compass.config_management.utils import config_reference


class TestConfigMerger(unittest2.TestCase):
    def test_merge(self):
        upper_config = {
            'networking': {
                'interfaces': {
                    'management': {
                        'ip_start': '192.168.1.1',
                        'ip_end': '192.168.1.100',
                        'netmask': '255.255.255.0',
                        'dns_pattern': '%(hostname)s.%(clustername)s.%(search_path)s',
                    },
                    'floating': {
                        'ip_start': '172.16.0.1',
                        'ip_end': '172.16.0.100',
                        'netmask': '0.0.0.0',
                        'dns_pattern': 'public-%(hostname)s.%(clustername)s.%(search_path)s', 
                    },
                },
                'global': {
                    'search_path': 'ods.com',
                    'default_no_proxy': ['127.0.0.1', 'localhost'],
                },
            },
            'clustername': 'cluster1',
            'dashboard_roles': ['os-single-controller'],
            'role_assign_policy': {
                'policy_by_host_numbers': {},
                'default': {
                    'roles': ['os-single-controller', 'os-network',
                              'os-compute-worker'],
                    'default_min': 1,
                },
            },
        }
        lower_configs = {
            1: {
                'hostname': 'host1',
            },
            2: {
                'hostname': 'host2',
                'networking': {
                    'interfaces': {
                        'management': {
                            'ip': '192.168.1.50',
                        },
                    },
                },
                'roles': ['os-single-controller', 'os-network'],
            }
        }
        expected_lower_configs = {
            1: {
                'networking': {
                    'interfaces': {
                        'floating': {
                            'ip': '172.16.0.1',
                            'netmask': '0.0.0.0',
                            'dns_alias': 'public-host1.cluster1.ods.com'
                        },
                        'management': {
                            'ip': '192.168.1.1',
                            'netmask': '255.255.255.0',
                            'dns_alias': 'host1.cluster1.ods.com'
                        }
                    },
                    'global': {
                        'search_path': 'ods.com',
                        'default_no_proxy': ['127.0.0.1', 'localhost'],
                        'ignore_proxy': '127.0.0.1,localhost,host1,192.168.1.1,host2,192.168.1.50'
                    }
                },
                'hostname': 'host1',
                'has_dashboard_roles': False,
                'roles': ['os-compute-worker']
            },
            2: {
                'networking': {
                    'interfaces': {
                        'floating': {
                            'ip': '172.16.0.2',
                            'netmask': '0.0.0.0',
                            'dns_alias': 'public-host2.cluster1.ods.com'
                        },
                        'management': {
                            'ip': '192.168.1.50',
                            'netmask': '255.255.255.0',
                            'dns_alias': 'host2.cluster1.ods.com'
                        }
                    },
                    'global': {
                        'search_path': 'ods.com',
                        'default_no_proxy': ['127.0.0.1', 'localhost'],
                        'ignore_proxy': '127.0.0.1,localhost,host1,192.168.1.1,host2,192.168.1.50'
                    }
                },
                'hostname': 'host2',
                'has_dashboard_roles': True,
                'roles': ['os-single-controller', 'os-network']
            }
        }
        mappings=[
            config_merger.ConfigMapping(
                path_list=['/networking/interfaces/*'],
                from_upper_keys={'ip_start': 'ip_start', 'ip_end': 'ip_end'},
                to_key='ip',
                value=config_merger_callbacks.assign_ips
            ),
            config_merger.ConfigMapping(
                path_list=['/role_assign_policy'],
                from_upper_keys={
                    'policy_by_host_numbers': 'policy_by_host_numbers',
                    'default': 'default'},
                to_key='/roles',
                value=config_merger_callbacks.assign_roles_by_host_numbers
            ),
            config_merger.ConfigMapping(
                path_list=['/dashboard_roles'],
                from_lower_keys={'lower_values': '/roles'},
                to_key='/has_dashboard_roles',
                value=config_merger_callbacks.has_intersection
            ),
            config_merger.ConfigMapping(
                path_list=[
                    '/networking/global',
                    '/networking/interfaces/*/netmask',
                    '/networking/interfaces/*/nic',
                    '/networking/interfaces/*/promisc',
                    '/security/*',
                    '/partition',
                ]
            ),
            config_merger.ConfigMapping(
                path_list=['/networking/interfaces/*'],
                from_upper_keys={'pattern': 'dns_pattern',
                                 'clustername': '/clustername',
                                 'search_path': '/networking/global/search_path'},
                from_lower_keys={'hostname': '/hostname'},
                to_key='dns_alias',
                value=functools.partial(config_merger_callbacks.assign_from_pattern,
                                        upper_keys=['search_path', 'clustername'],
                                        lower_keys=['hostname'])
            ),
            config_merger.ConfigMapping(
                path_list=['/networking/global'],
                from_upper_keys={'default': 'default_no_proxy',
                                 'clusterid': '/clusterid'},
                from_lower_keys={'hostnames': '/hostname',
                                 'ips': '/networking/interfaces/management/ip'},
                to_key='ignore_proxy',
                value=config_merger_callbacks.assign_noproxy
            )
        ]
        merger = config_merger.ConfigMerger(mappings)
        merger.merge(upper_config, lower_configs)
        self.assertEqual(lower_configs, expected_lower_configs)


if __name__ == '__main__':
    unittest2.main()
