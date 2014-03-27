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

"""test config merger callbacks module.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import os
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from compass.config_management.utils import config_merger_callbacks
from compass.config_management.utils import config_reference
from compass.utils import flags
from compass.utils import logsetting


class TestAssignRoles(unittest2.TestCase):
    """test assign roles."""

    def setUp(self):
        super(TestAssignRoles, self).setUp()
        logsetting.init()
        self.roles_ = ['control', 'api', 'compute']
        self.maxs_ = {'control': 1, 'api': 1, 'compute': -1}
        self.default_min_ = 1

    def tearDown(self):
        super(TestAssignRoles, self).tearDown()

    def test_assign_roles_allinone_roles_empty(self):
        """test assign roles all in one node."""
        lower_configs = {
            1: {'roles': []},
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        assigned = config_merger_callbacks.assign_roles(
            None, None, lower_refs, 'roles', roles=self.roles_,
            maxs=self.maxs_,
            default_min=self.default_min_)
        self.assertEqual(assigned, {1: ['control', 'api', 'compute']})

    def test_assign_roles_allinone_no_roles(self):
        lower_configs = {
            1: {},
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        assigned = config_merger_callbacks.assign_roles(
            None, None, lower_refs, 'roles', roles=self.roles_,
            maxs=self.maxs_, default_min=self.default_min_)
        self.assertEqual(assigned, {1: ['control', 'api', 'compute']})

    def test_assign_roles_allinone_roles_sorted(self):
        lower_configs = {
            1: {'roles': ['api', 'control', 'compute']},
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        assigned = config_merger_callbacks.assign_roles(
            None, None, lower_refs, 'roles', roles=self.roles_,
            maxs=self.maxs_, default_min=self.default_min_)
        self.assertEqual(assigned, {1: ['control', 'api', 'compute']})

    def test_assign_roles_allinone_roles_set_additional_roles(self):
        lower_configs = {
            1: {'roles': ['control', 'api', 'compute', 'mysql']},
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        assigned = config_merger_callbacks.assign_roles(
            None, None, lower_refs, 'roles', roles=self.roles_,
            maxs=self.maxs_, default_min=self.default_min_)
        self.assertEqual(assigned, {1: ['control', 'api', 'compute', 'mysql']})

    def test_assign_roles_allinone_roles_set_less_roles(self):
        lower_configs = {
            1: {'roles': ['control', 'api']},
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        assigned = config_merger_callbacks.assign_roles(
            None, None, lower_refs, 'roles', roles=self.roles_,
            maxs=self.maxs_, default_min=self.default_min_)
        self.assertEqual(assigned, {1: ['control', 'api']})

    def test_assign_roles_allinone_exclusives(self):
        exclusives = ['control']
        lower_configs = {
            1: {'roles': []},
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        self.assertRaises(
            ValueError, config_merger_callbacks.assign_roles,
            None, None, lower_refs, 'roles', roles=self.roles_,
            maxs=self.maxs_, default_min=self.default_min_,
            exclusives=exclusives)

    def test_assign_roles_allinone_bundles(self):
        lower_configs = {
            1: {'roles': []},
        }
        exclusives = ['control']
        bundles = [['control', 'api', 'compute']]
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)

        assigned = config_merger_callbacks.assign_roles(
            None, None, lower_refs, 'roles', roles=self.roles_,
            maxs=self.maxs_, default_min=self.default_min_,
            exclusives=exclusives, bundles=bundles)
        self.assertEqual(assigned, {1: ['control', 'api', 'compute']})

    def test_assign_roles_allinone_bundles_noenough_hosts(self):
        exclusives = ['control']
        bundles = [['control', 'api']]
        lower_configs = {
            1: {'roles': []},
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        self.assertRaises(
            ValueError, config_merger_callbacks.assign_roles,
            None, None, lower_refs, 'roles', roles=self.roles_,
            maxs=self.maxs_, default_min=self.default_min_,
            exclusives=exclusives, bundles=bundles)

    def test_assign_roles_allinone_maxes_mins_noenough_hosts(self):
        lower_configs = {
            1: {'roles': []},
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        maxs = {'control': 1, 'api': 2, 'compute': -1}
        mins = {'control': 1, 'api': 2}
        default_min = 0
        self.assertRaises(
            ValueError, config_merger_callbacks.assign_roles,
            None, None, lower_refs, 'roles', roles=self.roles_,
            maxs=maxs, mins=mins,
            default_min=default_min)

    def test_assign_roles_allinone_maxes_mins(self):
        lower_configs = {
            1: {'roles': []},
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        maxs = {'control': 1, 'api': 2, 'compute': -1}
        mins = {'control': 1, 'api': 0}
        default_min = 0
        assigned = config_merger_callbacks.assign_roles(
            None, None, lower_refs, 'roles', roles=self.roles_,
            maxs=maxs, mins=mins, default_min=default_min)
        self.assertEqual(assigned, {1: ['control']})

    def test_assign_roles(self):
        """test assign roles."""
        lower_configs = {
            1: {'roles': ['control']},
            2: {'roles': ['api', 'compute']},
            3: {'roles': []},
            4: {},
            5: {},
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        exclusives = ['control']
        assigned = config_merger_callbacks.assign_roles(
            None, None, lower_refs, 'roles', roles=self.roles_,
            maxs=self.maxs_,
            default_min=self.default_min_,
            exclusives=exclusives)
        self.assertEqual(assigned, {1: ['control'],
                                    2: ['api', 'compute'],
                                    3: ['compute'],
                                    4: ['compute'],
                                    5: ['compute']})

    def test_assign_roles_multihosts_one_role(self):
        default_min = 2
        maxs = {'control': 1, 'api': 2, 'compute': 2}
        exclusives = ['control']
        lower_configs = {
            1: {'roles': ['control']},
            2: {'roles': ['api', 'compute']},
            3: {'roles': []},
            4: {},
            5: {},
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        assigned = config_merger_callbacks.assign_roles(
            None, None, lower_refs, 'roles', roles=self.roles_,
            maxs=maxs, default_min=default_min,
            exclusives=exclusives)
        self.assertEqual(assigned, {1: ['control'],
                                    2: ['api', 'compute'],
                                    3: ['control'],
                                    4: ['api'],
                                    5: ['compute']})

    def test_assign_roles_bundles(self):
        roles = ['control', 'api', 'compute', 'mysql']
        maxs = {'control': 1, 'api': 2, 'compute': -1, 'mysql': 2}
        exclusives = ['control']
        bundles = [['control', 'api']]
        lower_configs = {
            1: {},
            2: {},
            3: {},
            4: {},
            5: {},
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        assigned = config_merger_callbacks.assign_roles(
            None, None, lower_refs, 'roles', roles=roles,
            maxs=maxs, default_min=self.default_min_,
            exclusives=exclusives, bundles=bundles)
        self.assertEqual(assigned, {1: ['control', 'api'],
                                    2: ['compute'],
                                    3: ['mysql'],
                                    4: ['mysql'],
                                    5: ['compute']})

    def test_assign_roles_multi_default_roles(self):
        roles = ['control', 'api', 'compute', 'mysql']
        maxs = {'control': 1, 'api': 2, 'compute': -1, 'mysql': -2}
        exclusives = ['control']
        bundles = [['control', 'api']]
        lower_configs = {
            1: {},
            2: {},
            3: {},
            4: {},
            5: {},
            6: {}
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        assigned = config_merger_callbacks.assign_roles(
            None, None, lower_refs, 'roles', roles=roles,
            maxs=maxs, default_min=self.default_min_,
            exclusives=exclusives, bundles=bundles)
        self.assertEqual(assigned, {1: ['control', 'api'],
                                    2: ['compute'],
                                    3: ['mysql'],
                                    4: ['mysql'],
                                    5: ['compute'],
                                    6: ['mysql']})

    def test_assign_roles_hosts_portion_by_default_roles(self):
        roles = ['control', 'api', 'compute', 'mysql']
        maxs = {'control': 1, 'api': 2, 'compute': -1, 'mysql': -1}
        exclusives = ['control']
        bundles = [['control', 'api']]
        lower_configs = {
            1: {},
            2: {},
            3: {},
            4: {},
            5: {},
            6: {}
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        assigned = config_merger_callbacks.assign_roles(
            None, None, lower_refs, 'roles', roles=roles,
            maxs=maxs, default_min=self.default_min_,
            exclusives=exclusives, bundles=bundles)
        self.assertEqual(assigned, {1: ['control', 'api'],
                                    2: ['compute'],
                                    3: ['mysql'],
                                    4: ['compute'],
                                    5: ['mysql'],
                                    6: ['compute']})

    def test_assign_roles_by_host_number_one_host(self):
        lower_configs = {
            1: {}
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        default = {
            'roles': ['control', 'api', 'compute'],
            'maxs': {'control': 1, 'api': 1, 'compute': -1},
            'default_min': 1,
            'exclusives': ['control']
        }
        policy_by_host_numbers = {
            '1': {
                'bundles': [['control', 'api', 'compute']]
            },
            '2': {
                'bundles': [['control', 'api']]
            },
        }
        assigned = config_merger_callbacks.assign_roles_by_host_numbers(
            None, None, lower_refs, 'roles',
            policy_by_host_numbers=policy_by_host_numbers,
            default=default)
        self.assertEqual(assigned, {1: ['control', 'api', 'compute']})

    def test_assign_roles_by_host_number_two_hosts(self):
        lower_configs = {
            1: {},
            2: {}
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        default = {
            'roles': ['control', 'api', 'compute'],
            'maxs': {'control': 1, 'api': 1, 'compute': -1},
            'default_min': 1,
            'exclusives': ['control']
        }
        policy_by_host_numbers = {
            '1': {
                'bundles': [['control', 'api', 'compute']]
            },
            '2': {
                'bundles': [['control', 'api']]
            },
        }
        assigned = config_merger_callbacks.assign_roles_by_host_numbers(
            None, None, lower_refs, 'roles',
            policy_by_host_numbers=policy_by_host_numbers,
            default=default)
        self.assertEqual(assigned, {1: ['control', 'api'], 2: ['compute']})

    def test_assign_roles_by_host_number_host_number_not_found(self):
        lower_configs = {
            1: {},
            2: {},
            3: {}
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        default = {
            'roles': ['control', 'api', 'compute'],
            'maxs': {'control': 1, 'api': 1, 'compute': -1},
            'default_min': 1,
            'exclusives': ['control']
        }
        policy_by_host_numbers = {
            '1': {
                'bundles': [['control', 'api', 'compute']]
            },
            '2': {
                'bundles': [['control', 'api']]
            },
        }
        assigned = config_merger_callbacks.assign_roles_by_host_numbers(
            None, None, lower_refs, 'roles',
            policy_by_host_numbers=policy_by_host_numbers,
            default=default)
        self.assertEqual(
            assigned, {1: ['control'], 2: ['api'], 3: ['compute']})

    def test_assign_roles_by_host_number_host_number_host_number_int(self):
        default = {
            'roles': ['control', 'api', 'compute'],
            'maxs': {'control': 1, 'api': 1, 'compute': -1},
            'default_min': 1,
            'exclusives': ['control']
        }
        policy_by_host_numbers = {
            1: {
                'bundles': [['control', 'api', 'compute']]
            },
            2: {
                'bundles': [['control', 'api']]
            },
        }
        lower_configs = {
            1: {}
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        self.assertRaises(
            ValueError, config_merger_callbacks.assign_roles_by_host_numbers,
            None, None, lower_refs, 'roles',
            policy_by_host_numbers=policy_by_host_numbers,
            default=default)


class TestAssignIPs(unittest2.TestCase):
    """test assign ips."""

    def setUp(self):
        super(TestAssignIPs, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestAssignIPs, self).tearDown()

    def test_assign_ips_validate(self):
        lower_configs = {
            1: {}
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        # ip_start and ip_end param should be the correct format.
        self.assertRaises(
            ValueError, config_merger_callbacks.assign_ips,
            None, None, lower_refs, 'ip',
            ip_start='')
        self.assertRaises(
            ValueError, config_merger_callbacks.assign_ips,
            None, None, lower_refs, 'ip',
            ip_start='100')
        self.assertRaises(
            ValueError, config_merger_callbacks.assign_ips,
            None, None, lower_refs, 'ip',
            ip_end='')
        self.assertRaises(
            ValueError, config_merger_callbacks.assign_ips,
            None, None, lower_refs, 'ip',
            ip_end='100')

    def test_assign_ip_ip_start_ip_end_relation(self):
        lower_configs = {
            1: {}
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        self.assertRaises(
            ValueError, config_merger_callbacks.assign_ips,
            None, None, lower_refs, 'ip',
            ip_start='192.168.100.100', ip_end='192.168.100.99')
        assigned = config_merger_callbacks.assign_ips(
            None, None, lower_refs, 'ip',
            ip_start='192.168.100.100', ip_end='192.168.100.100')
        self.assertEqual(assigned, {1: '192.168.100.100'})

    def test_assign_ips_multi_hosts_noenough_ips(self):
        lower_configs = {
            1: {}, 2: {}
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        self.assertRaises(
            ValueError, config_merger_callbacks.assign_ips,
            None, None, lower_refs, 'ip',
            ip_start='192.168.100.100', ip_end='192.168.100.100')

    def test_assign_ips_multi_hosts(self):
        lower_configs = {
            1: {}, 2: {}
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        assigned = config_merger_callbacks.assign_ips(
            None, None, lower_refs, 'ip',
            ip_start='192.168.100.100', ip_end='192.168.100.101')
        self.assertEqual(
            assigned, {1: '192.168.100.100', 2: '192.168.100.101'})


class TestAssignFromPattern(unittest2.TestCase):
    """test assign value from pattern."""

    def setUp(self):
        super(TestAssignFromPattern, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestAssignFromPattern, self).tearDown()

    def test_pattern(self):
        lower_configs = {
            1: {}
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        assigned = config_merger_callbacks.assign_from_pattern(
            None, None, lower_refs, 'pattern', pattern='hello')
        self.assertEqual(assigned, {1: 'hello'})

    def test_pattern_upper_keys(self):
        lower_configs = {
            1: {}
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        assigned = config_merger_callbacks.assign_from_pattern(
            None, None, lower_refs, 'pattern',
            upper_keys=['clustername'], pattern='%(clustername)s',
            clustername='mycluster')
        self.assertEqual(assigned, {1: 'mycluster'})

    def test_pattern_lower_keys(self):
        lower_configs = {
            1: {}
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        assigned = config_merger_callbacks.assign_from_pattern(
            None, None, lower_refs, 'pattern',
            lower_keys=['hostname'], pattern='%(hostname)s',
            hostname={1: 'myhost'})
        self.assertEqual(assigned, {1: 'myhost'})

    def test_pattern_upper_keys_lower_keys(self):
        lower_configs = {
            1: {}
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        assigned = config_merger_callbacks.assign_from_pattern(
            None, None, lower_refs, 'pattern',
            upper_keys=['clustername'], lower_keys=['hostname'],
            pattern='%(hostname)s.%(clustername)s',
            hostname={1: 'myhost'}, clustername='mycluster')
        self.assertEqual(assigned, {1: 'myhost.mycluster'})

    def test_pattern_upper_keys_lower_keys_overlap(self):
        lower_configs = {
            1: {}
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        self.assertRaises(
            KeyError, config_merger_callbacks.assign_from_pattern,
            None, None, lower_refs, 'pattern',
            upper_keys=['clustername'],
            lower_keys=['clustername', 'hostname'],
            pattern='%(hostname)s.%(clustername)s',
            hostname={1: 'myhost'}, clustername='mycluster')

    def test_pattern_extra_keys(self):
        lower_configs = {
            1: {}
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        self.assertRaises(
            KeyError, config_merger_callbacks.assign_from_pattern,
            None, None, lower_refs, 'pattern',
            upper_keys=['clustername', 'clusterid'],
            lower_keys=['hostname', 'hostid'],
            pattern='%(hostname)s.%(clustername)s',
            hostname={1: 'myhost'}, clustername='mycluster')

    def test_pattern_lower_key_not_dict(self):
        lower_configs = {
            1: {}
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        self.assertRaises(
            KeyError, config_merger_callbacks.assign_from_pattern,
            None, None, lower_refs, 'pattern',
            upper_keys=['clustername'],
            lower_keys=['hostname'],
            pattern='%(hostname)s.%(clustername)s',
            hostname='myhost', clustername='mycluster')

    def test_pattern_extra_kwargs(self):
        lower_configs = {
            1: {}
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        assigned = config_merger_callbacks.assign_from_pattern(
            None, None, lower_refs, 'pattern',
            upper_keys=['clustername'],
            lower_keys=['hostname'],
            pattern='%(hostname)s.%(clustername)s',
            hostname={1: 'myhost'}, clustername='mycluster',
            hostid={1: 'myhost'}, clusterid=1)
        self.assertEqual(assigned, {1: 'myhost.mycluster'})

    def test_pattern_extra_key_in_pattern(self):
        lower_configs = {
            1: {}
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        self.assertRaises(
            KeyError, config_merger_callbacks.assign_from_pattern,
            None, None, lower_refs, 'pattern',
            upper_keys=['clustername'],
            lower_keys=['hostname'],
            pattern='%(hostid)s.%(clusterid)s',
            hostname={1: 'myhost'}, clustername='mycluster')


class TestNoProxy(unittest2.TestCase):
    """test assign noproxy."""

    def setUp(self):
        super(TestNoProxy, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestNoProxy, self).tearDown()

    def test_noproxy(self):
        lower_configs = {
            1: {},
            2: {}
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        assigned = config_merger_callbacks.assign_noproxy(
            None, None, lower_refs, 'noproxy',
            default=['127.0.0.1', 'compass', '10.145.88.3'],
            clusterid=1, noproxy_pattern='%(hostname)s.%(clusterid)s,%(ip)s',
            hostnames={1: 'host1', 2: 'host2'},
            ips={1: '10.145.88.1', 2: '10.145.88.2'})
        self.assertEqual(
            assigned, {
                1: (
                    '127.0.0.1,compass,10.145.88.3,'
                    'host1.1,10.145.88.1,host2.1,10.145.88.2'
                ),
                2: (
                    '127.0.0.1,compass,10.145.88.3,'
                    'host1.1,10.145.88.1,host2.1,10.145.88.2'
                )
            })

    def test_noproxy_noclusterid(self):
        lower_configs = {
            1: {},
            2: {}
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        self.assertRaises(
            KeyError, config_merger_callbacks.assign_noproxy,
            None, None, lower_refs, 'noproxy',
            default=['127.0.0.1', 'compass', '10.145.88.3'],
            noproxy_pattern='%(hostname)s.%(clusterid)s,%(ip)s',
            hostnames={1: 'host1', 2: 'host2'},
            ips={1: '10.145.88.1', 2: '10.145.88.2'})

    def test_noproxy_nohostname_ips(self):
        lower_configs = {
            1: {},
            2: {}
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        self.assertRaises(
            KeyError, config_merger_callbacks.assign_noproxy,
            None, None, lower_refs, 'noproxy',
            default=['127.0.0.1', 'compass', '10.145.88.3'],
            noproxy_pattern='%(hostname)s.%(clusterid)s,%(ip)s',
            clusterid=1, hostnames={1: 'host1'},
            ips={1: '10.145.88.1'})

    def test_noproxy_extra_keys_in_pattern(self):
        lower_configs = {
            1: {},
            2: {}
        }
        lower_refs = {}
        for hostid, config in lower_configs.items():
            lower_refs[hostid] = config_reference.ConfigReference(config)
        self.assertRaises(
            KeyError, config_merger_callbacks.assign_noproxy,
            None, None, lower_refs, 'noproxy',
            default=['127.0.0.1', 'compass', '10.145.88.3'],
            noproxy_pattern='%(hostname)s.%(clustername)s,%(ip)s',
            clusterid=1, hostnames={1: 'host1', 2: 'host2'},
            ips={1: '10.145.88.1', 2: '10.145.88.2'})


class TestOverrideIfEmpty(unittest2.TestCase):
    """test override if empty."""

    def setUp(self):
        super(TestOverrideIfEmpty, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestOverrideIfEmpty, self).tearDown()

    def test_lower_config_none(self):
        lower_config = None
        lower_ref = config_reference.ConfigReference(lower_config)
        override = config_merger_callbacks.override_if_empty(
            None, None, lower_ref, 'override')
        self.assertTrue(override)

    def test_lower_config_empty(self):
        lower_config = ''
        lower_ref = config_reference.ConfigReference(lower_config)
        override = config_merger_callbacks.override_if_empty(
            None, None, lower_ref, 'override')
        self.assertTrue(override)
        lower_config = []
        lower_ref = config_reference.ConfigReference(lower_config)
        override = config_merger_callbacks.override_if_empty(
            None, None, lower_ref, 'override')
        self.assertTrue(override)
        lower_config = {}
        lower_ref = config_reference.ConfigReference(lower_config)
        override = config_merger_callbacks.override_if_empty(
            None, None, lower_ref, 'override')
        self.assertTrue(override)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
