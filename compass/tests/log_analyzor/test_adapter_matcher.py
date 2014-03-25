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

"""test adapter matcher module"""

import os
import unittest2

os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from compass.db import database
from compass.db.model import Adapter
from compass.db.model import Cluster
from compass.db.model import ClusterHost
from compass.db.model import ClusterState
from compass.db.model import HostState
from compass.db.model import Machine
from compass.db.model import Role
from compass.db.model import Switch

from compass.log_analyzor import adapter_matcher
from compass.log_analyzor.file_matcher import FileMatcher
from compass.log_analyzor.line_matcher import IncrementalProgress
from compass.log_analyzor.line_matcher import LineMatcher
from compass.log_analyzor import progress_calculator

from compass.utils import flags
from compass.utils import logsetting


class TestAdapterItemMatcher(unittest2.TestCase):
    def setUp(self):
        super(TestAdapterItemMatcher, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestAdapterItemMatcher, self).tearDown()

    def test_update_progress(self):
        test_update_progress_range = {
            'min_progress': 0.3,
            'max_progress': 0.7,
        }
        expected = ['sys.log', 0.0, 0.1]
        file_matchers = [
            FileMatcher(
                filename='sys.log',
                min_progress=0.0,
                max_progress=0.1,
                line_matchers={
                    'start': LineMatcher(
                        pattern=r'NOTICE (?P<message>.*)',
                        progress=IncrementalProgress(.1, .9, .1),
                        message_template='%(message)s',
                        unmatch_nextline_next_matcher_name='start',
                        match_nextline_next_matcher_name='exit'
                    ),
                }
            ),
        ]
        matcher = adapter_matcher.AdapterItemMatcher(
            file_matchers=file_matchers)
        matcher.update_progress_range(
            **test_update_progress_range)
        file_matcher = matcher.file_matchers_[0]
        result = []
        result.append(file_matcher.filename_)
        result.append(file_matcher.min_progress_)
        result.append(file_matcher.max_progress_)
        self.assertEqual(expected, result)


class TestOSMatcher(unittest2.TestCase):
    def setUp(self):
        super(TestOSMatcher, self).setUp()
        self.item_matcher = progress_calculator\
            .OS_INSTALLER_CONFIGURATIONS[
                'CentOS'
            ]
        logsetting.init()

    def tearDown(self):
        super(TestOSMatcher, self).tearDown()

    def test_min_larger_than_max(self):
        test_min_larger_than_max = {
            'os_installer_name': 'os_installer',
            'os_pattern': r'.*.',
            'item_matcher': None,
            'min_progress': 1.0,
            'max_progress': 0.0,
        }
        self.assertRaises(
            IndexError,
            adapter_matcher.OSMatcher,
            **test_min_larger_than_max
        )

    def test_progress_exceed_one(self):
        test_progress_exceed_one = {
            'os_installer_name': 'os_installer',
            'os_pattern': r'.*.',
            'item_matcher': None,
            'min_progress': 1.1,
            'max_progress': 1.1,
        }
        self.assertRaises(
            IndexError,
            adapter_matcher.OSMatcher,
            **test_progress_exceed_one
        )

    def test_match(self):
        test_match = {
            'os_installer_name': 'cobbler',
            'os_pattern': r'CentOS.*',
            'item_matcher': self.item_matcher,
            'min_progress': 0.0,
            'max_progress': 0.6,
        }
        matcher = adapter_matcher.OSMatcher(
            **test_match)
        self.assertTrue(matcher.match(
            'cobbler',
            'CentOS6.4'))

    def test_installer_unmatch(self):
        test_installer_unmatch = {
            'os_installer_name': 'razor',
            'os_pattern': r'CentOS.*',
            'item_matcher': self.item_matcher,
            'min_progress': 0.0,
            'max_progress': 0.6,
        }
        matcher = adapter_matcher.OSMatcher(
            **test_installer_unmatch)
        self.assertFalse(matcher.match(
            'cobbler',
            'CentOS6.4'))

    def test_os_unmatch(self):
        test_os_unmatch = {
            'os_installer_name': 'cobbler',
            'os_pattern': r'Ubuntu.*',
            'item_matcher': self.item_matcher,
            'min_progress': 0.0,
            'max_progress': 0.6,
        }
        matcher = adapter_matcher.OSMatcher(
            **test_os_unmatch)
        self.assertFalse(matcher.match(
            'cobbler',
            'CentOS6.4'))

    def test_both_unmatch(self):
        test_both_unmatch = {
            'os_installer_name': 'razor',
            'os_pattern': r'Ubuntu.*',
            'item_matcher': self.item_matcher,
            'min_progress': 0.0,
            'max_progress': 0.6,
        }
        matcher = adapter_matcher.OSMatcher(
            **test_both_unmatch)
        self.assertFalse(matcher.match(
            'cobbler',
            'CentOS6.4'))


class TestPackageMatcher(unittest2.TestCase):
    def setUp(self):
        super(TestPackageMatcher, self).setUp()
        self.item_matcher = progress_calculator\
            .PACKAGE_INSTALLER_CONFIGURATIONS[
                'openstack'
            ]
        logsetting.init()

    def tearDown(self):
        super(TestPackageMatcher, self).tearDown()

    def test_match(self):
        test_match = {
            'package_installer_name': 'chef',
            'target_system': 'openstack',
            'item_matcher': self.item_matcher,
            'min_progress': 0.6,
            'max_progress': 1.0,
        }
        matcher = adapter_matcher.PackageMatcher(
            **test_match)
        self.assertTrue(matcher.match(
            'chef',
            'openstack'))

    def test_installer_unmatch(self):
        test_installer_unmatch = {
            'package_installer_name': 'puppet',
            'target_system': 'openstack',
            'item_matcher': self.item_matcher,
            'min_progress': 0.6,
            'max_progress': 1.0,
        }
        matcher = adapter_matcher.PackageMatcher(
            **test_installer_unmatch)
        self.assertFalse(matcher.match(
            'chef',
            'openstack'))

    def test_target_system_unmatch(self):
        test_target_system_unmatch = {
            'package_installer_name': 'chef',
            'target_system': 'hadoop',
            'item_matcher': self.item_matcher,
            'min_progress': 0.6,
            'max_progress': 1.0,
        }
        matcher = adapter_matcher.PackageMatcher(
            **test_target_system_unmatch)
        self.assertFalse(matcher.match(
            'chef',
            'openstack'))

    def test_both_unmatch(self):
        test_both_unmatch = {
            'package_installer_name': 'puppet',
            'target_system': 'hadoop',
            'item_matcher': self.item_matcher,
            'min_progress': 0.6,
            'max_progress': 1.0,
        }
        matcher = adapter_matcher.PackageMatcher(
            **test_both_unmatch)
        self.assertFalse(matcher.match(
            'chef',
            'openstack'))


class TestAdapterMatcher(unittest2.TestCase):
    def setUp(self):
        super(TestAdapterMatcher, self).setUp()
        self.os_item_matcher = progress_calculator\
            .OS_INSTALLER_CONFIGURATIONS[
                'CentOS'
            ]
        self.package_item_matcher = progress_calculator\
            .PACKAGE_INSTALLER_CONFIGURATIONS[
                'openstack'
            ]
        logsetting.init()
        database.create_db()

    def tearDown(self):
        super(TestAdapterMatcher, self).tearDown()
        database.drop_db()

    def test_match(self):
        test_match = {
            'os_matcher': {
                'os_installer_name': 'cobbler',
                'os_pattern': 'CentOS.*',
                'item_matcher': self.os_item_matcher,
                'min_progress': 0.0,
                'max_progress': 0.6
            },
            'package_matcher': {
                'package_installer_name': 'chef',
                'target_system': 'openstack',
                'item_matcher': self.package_item_matcher,
                'min_progress': 0.6,
                'max_progress': 1.0
            }
        }
        os_matcher = adapter_matcher.OSMatcher(
            **test_match['os_matcher'])
        package_matcher = adapter_matcher.PackageMatcher(
            **test_match['package_matcher'])
        matcher = adapter_matcher.AdapterMatcher(
            os_matcher, package_matcher)

        self.assertTrue(
            matcher.match(
                'cobbler', 'CentOS6.4',
                'chef', 'openstack'))

    def test_os_unmatch(self):
        test_os_unmatch = {
            'os_matcher': {
                'os_installer_name': 'razor',
                'os_pattern': 'CentOS.*',
                'item_matcher': self.os_item_matcher,
                'min_progress': 0.0,
                'max_progress': 0.6
            },
            'package_matcher': {
                'package_installer_name': 'chef',
                'target_system': 'openstack',
                'item_matcher': self.package_item_matcher,
                'min_progress': 0.6,
                'max_progress': 1.0
            }
        }
        os_matcher = adapter_matcher.OSMatcher(
            **test_os_unmatch['os_matcher'])
        package_matcher = adapter_matcher.PackageMatcher(
            **test_os_unmatch['package_matcher'])
        matcher = adapter_matcher.AdapterMatcher(
            os_matcher, package_matcher)

        self.assertFalse(
            matcher.match(
                'cobbler', 'CentOS6.4',
                'chef', 'openstack'))

    def test_package_unmatch(self):
        test_package_unmatch = {
            'os_matcher': {
                'os_installer_name': 'cobbler',
                'os_pattern': 'CentOS.*',
                'item_matcher': self.os_item_matcher,
                'min_progress': 0.0,
                'max_progress': 0.6
            },
            'package_matcher': {
                'package_installer_name': 'puppet',
                'target_system': 'openstack',
                'item_matcher': self.package_item_matcher,
                'min_progress': 0.6,
                'max_progress': 1.0
            }
        }
        os_matcher = adapter_matcher.OSMatcher(
            **test_package_unmatch['os_matcher'])
        package_matcher = adapter_matcher.PackageMatcher(
            **test_package_unmatch['package_matcher'])
        matcher = adapter_matcher.AdapterMatcher(
            os_matcher, package_matcher)

        self.assertFalse(
            matcher.match(
                'cobbler', 'CentOS6.4',
                'chef', 'openstack'))

    def test_both_unmatch(self):
        test_both_unmatch = {
            'os_matcher': {
                'os_installer_name': 'cobbler',
                'os_pattern': 'Ubuntu*',
                'item_matcher': self.os_item_matcher,
                'min_progress': 0.0,
                'max_progress': 0.6
            },
            'package_matcher': {
                'package_installer_name': 'chef',
                'target_system': 'hadoop',
                'item_matcher': self.package_item_matcher,
                'min_progress': 0.6,
                'max_progress': 1.0
            }
        }
        os_matcher = adapter_matcher.OSMatcher(
            **test_both_unmatch['os_matcher'])
        package_matcher = adapter_matcher.PackageMatcher(
            **test_both_unmatch['package_matcher'])
        matcher = adapter_matcher.AdapterMatcher(
            os_matcher, package_matcher)

        self.assertFalse(
            matcher.match(
                'cobbler', 'CentOS6.4',
                'chef', 'openstack'))

    def test_update_progress(self):
        config = {
            'ADAPTERS': [
                {
                    'name': 'CentOS_openstack',
                    'os': 'CentOS',
                    'target_system': 'openstack',
                },
            ],
            'ROLES': [
                {
                    'name': 'os-single-controller',
                    'target_system': 'openstack',
                },
                {
                    'name': 'os-network',
                    'target_system': 'openstack',
                },
                {
                    'name': 'os-compute',
                    'target_system': 'openstack',
                },
            ],
            'SWITCHES': [
                {
                    'ip': '1.2.3.4',
                    'vendor': 'huawei',
                    'credential': {
                        'version': 'v2c',
                        'comunity': 'public',
                    }
                },
            ],
            'MACHINES_BY_SWITCH': {
                '1.2.3.4': [
                    {
                        'mac': '00:00:01:02:03:04',
                        'port': 1,
                        'vlan': 1
                    },
                ],
            },
            'CLUSTERS': [
                {
                    'name': 'cluster1',
                    'adapter': 'CentOS_openstack',
                    'mutable': False,
                    'security': {
                        'server_credentials': {
                            'username': 'root',
                            'password': 'huawei'
                        },
                        'service_credentials': {
                            'username': 'service',
                            'password': 'huawei'
                        },
                        'console_credentials': {
                            'username': 'admin',
                            'password': 'huawei'
                        }
                    },
                    'networking': {
                        'interfaces': {
                            'management': {
                                'nic': 'eth0',
                                'promisc': 0,
                                'netmask': '255.255.255.0',
                                'ip_end': '192.168.20.200',
                                'gateway': '',
                                'ip_start': '192.168.20.100'
                            },
                            'storage': {
                                'nic': 'eth0',
                                'promisc': 0,
                                'netmask': '255.255.254.0',
                                'ip_end': '10.145.88.200',
                                'gateway': '10.145.88.1',
                                'ip_start': '10.145.88.100'
                            },
                            'public': {
                                'nic': 'eth2',
                                'promisc': 1,
                                'netmask': '255.255.254.0',
                                'ip_end': '10.145.88.255',
                                'gateway': '10.145.88.1',
                                'ip_start': '10.145.88.100'
                            },
                            'tenant': {
                                'nic': 'eth0',
                                'promisc': 0,
                                'netmask': '255.255.254.0',
                                'ip_end': '10.145.88.120',
                                'gateway': '10.145.88.1',
                                'ip_start': '10.145.88.100'
                            }
                        },
                        'global': {
                            'nameservers': '192.168.20.254',
                            'proxy': 'http://192.168.20.254:3128',
                            'ntp_server': '192.168.20.254',
                            'search_path': 'ods.com',
                            'gateway': '10.145.88.1'
                        },
                    },
                    'partition': '/home 20%%;/tmp 10%%;/var 30%%;',
                },
            ],
            'HOSTS_BY_CLUSTER': {
                'cluster1': [
                    {
                        'hostname': 'server1',
                        'mac': '00:00:01:02:03:04',
                        'mutable': False,
                        'config': {
                            'networking': {
                                'interfaces': {
                                    'management': {
                                        'ip': '192.168.20.100',
                                    },
                                },
                            },
                            'roles': [
                                "os-single-controller",
                                "os-network",
                                "os-compute"
                            ],
                        },
                    },
                ],
            },
        }
        self._prepare_database(config)
        cluster_hosts = {}
        with database.session() as session:
            clusters = session.query(Cluster).all()
            for cluster in clusters:
                cluster_hosts[cluster.id] = [
                    host.id for host in cluster.hosts]

        test_update_progress = {
            'os_matcher': {
                'os_installer_name': 'cobbler',
                'os_pattern': 'CentOS.*',
                'item_matcher': self.os_item_matcher,
                'min_progress': 0.0,
                'max_progress': 0.6
            },
            'package_matcher': {
                'package_installer_name': 'chef',
                'target_system': 'openstack',
                'item_matcher': self.package_item_matcher,
                'min_progress': 0.6,
                'max_progress': 1.0
            }
        }
        os_matcher = adapter_matcher.OSMatcher(
            **test_update_progress['os_matcher'])
        package_matcher = adapter_matcher.PackageMatcher(
            **test_update_progress['package_matcher'])
        matcher = adapter_matcher.AdapterMatcher(
            os_matcher, package_matcher)
        for cluster_id in cluster_hosts.keys():
            matcher.update_progress(
                cluster_id,
                cluster_hosts[cluster_id])

        expected_cluster_state = {
            'state': 'INSTALLING',
            'progress': 0.0
        }
        cluster = {}
        host = {}
        with database.session():
            cluster_state = session.query(ClusterState).all()
            cluster['state'] = cluster_state[0].state
            cluster['progress'] = cluster_state[0].progress
            self.assertEqual(expected_cluster_state,
                             cluster)

    def _prepare_database(self, config):
        with database.session() as session:
            adapters = {}
            for adapter_config in config['ADAPTERS']:
                adapter = Adapter(**adapter_config)
                session.add(adapter)
                adapters[adapter_config['name']] = adapter

            roles = {}
            for role_config in config['ROLES']:
                role = Role(**role_config)
                session.add(role)
                roles[role_config['name']] = role

            switches = {}
            for switch_config in config['SWITCHES']:
                switch = Switch(**switch_config)
                session.add(switch)
                switches[switch_config['ip']] = switch

            machines = {}
            for switch_ip, machine_configs in (
                config['MACHINES_BY_SWITCH'].items()
            ):
                for machine_config in machine_configs:
                    machine = Machine(**machine_config)
                    machines[machine_config['mac']] = machine
                    machine.switch = switches[switch_ip]
                    session.add(machine)

            clusters = {}
            for cluster_config in config['CLUSTERS']:
                adapter_name = cluster_config['adapter']
                del cluster_config['adapter']
                cluster = Cluster(**cluster_config)
                clusters[cluster_config['name']] = cluster
                cluster.adapter = adapters[adapter_name]
                cluster.state = ClusterState(
                    state="INSTALLING", progress=0.0, message='')
                session.add(cluster)

            hosts = {}
            for cluster_name, host_configs in (
                config['HOSTS_BY_CLUSTER'].items()
            ):
                for host_config in host_configs:
                    mac = host_config['mac']
                    del host_config['mac']
                    host = ClusterHost(**host_config)
                    hosts['%s.%s' % (
                        host_config['hostname'], cluster_name)] = host
                    host.machine = machines[mac]
                    host.cluster = clusters[cluster_name]
                    host.state = HostState(
                        state="INSTALLING", progress=0.0, message='')
                    session.add(host)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
