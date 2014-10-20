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


import datetime
import logging
import mock
import os
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from base import BaseTest
from compass.db.api import adapter as adapter_api
from compass.db.api import adapter_holder as adapter
from compass.db.api import database
from compass.db.api import metadata as metadata_api
from compass.db.api import metadata_holder as metadata
from compass.db.api import user as user_api
from compass.db import exception
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import util


class AdapterTestCase(unittest2.TestCase):
    """Adapter base test case."""

    def setUp(self):
        super(AdapterTestCase, self).setUp()
        reload(setting)
        setting.CONFIG_DIR = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'data'
        )
        database.init('sqlite://')
        database.create_db()
        self.user_object = (
            user_api.get_user_object(
                setting.COMPASS_ADMIN_EMAIL
            )
        )

        mock_config = mock.Mock()
        self.backup_adapter_configs = util.load_configs
        util.load_configs = mock_config
        configs = [{
            'NAME': 'openstack_test',
            'DISLAY_NAME': 'Test OpenStack Icehouse',
            'PACKAGE_INSTALLER': 'chef_installer',
            'OS_INSTALLER': 'cobbler',
            'SUPPORTED_OS_PATTERNS': ['(?i)centos.*', '(?i)ubuntu.*'],
            'DEPLOYABLE': True
        }]
        util.load_configs.return_value = configs
        with database.session() as session:
            adapter_api.add_adapters_internal(session)
        adapter.load_adapters()
        self.adapter_object = adapter.list_adapters(self.user_object)
        for adapter_obj in self.adapter_object:
            if adapter_obj['name'] == 'openstack_icehouse':
                self.adapter_id = adapter_obj['id']
                break

    def tearDown(self):
        super(AdapterTestCase, self).tearDown()
        util.load_configs = self.backup_adapter_configs
        reload(setting)
        database.drop_db()


class TestListAdapters(AdapterTestCase):
    """Test list adapters."""

    def setUp(self):
        super(TestListAdapters, self).setUp()

    def tearDown(self):
        super(TestListAdapters, self).tearDown()

    def test_list_adapters(self):
        adapters = adapter.list_adapters(
            self.user_object
        )
        result = []
        for item in adapters:
            result.append(item['name'])
        expects = [
            'openstack_icehouse',
            'os_only',
            'ceph(chef)',
            'openstack_test'
        ]
        self.assertIsNotNone(adapters)
        for expect in expects:
            self.assertIn(expect, result)


class TestGetAdapter(AdapterTestCase):
    """Test get adapter."""

    def setUp(self):
        super(TestGetAdapter, self).setUp()

    def tearDown(self):
        super(TestGetAdapter, self).tearDown()

    def test_get_adapter(self):
        get_adapter = adapter.get_adapter(
            self.user_object,
            self.adapter_id
        )
        name = None
        for k, v in get_adapter.items():
            if k == 'name':
                name = v
        self.assertIsNotNone(get_adapter)
        self.assertEqual(name, 'openstack_icehouse')

    def test_adapter_not_exist(self):
        self.assertRaises(
            exception.RecordNotExists,
            adapter.get_adapter,
            self.user_object,
            99
        )


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
