#!/usr/bin/python
#
# Copyright 2014 Openstack Foundation
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

    def tearDown(self):
        super(TestAssignRoles, self).tearDown()

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
        roles = ['control', 'api', 'compute']
        maxs = {'control': 1, 'api': 2, 'compute': -1}
        default_min = 1
        exclusives = ['control']
        assigned = config_merger_callbacks.assign_roles(
            None, None, lower_refs, 'roles', roles=roles,
            maxs=maxs,
            default_min=default_min,
            exclusives=exclusives)
        self.assertEqual(assigned, {1: ['control'],
                                    2: ['api', 'compute'],
                                    3: ['api'],
                                    4: ['compute'],
                                    5: ['compute']})

        default_min = 2
        maxs = {'control': 1, 'api': 2, 'compute': 2}
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
            None, None, lower_refs, 'roles', roles=roles,
            maxs=maxs, default_min=default_min,
            exclusives=exclusives)
        self.assertEqual(assigned, {1: ['control'],
                                    2: ['api', 'compute'],
                                    3: ['control'],
                                    4: ['api'],
                                    5: ['compute']})

        default_min = 1
        roles = ['control', 'api', 'compute', 'mysql']
        maxs = {'control': 1, 'api': 2, 'compute': -1, 'mysql': 2}
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
            maxs=maxs, default_min=default_min,
            exclusives=exclusives, bundles=bundles)
        self.assertEqual(assigned, {1: ['control', 'api'],
                                    2: ['compute'],
                                    3: ['mysql'],
                                    4: ['mysql'],
                                    5: ['compute']})


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
