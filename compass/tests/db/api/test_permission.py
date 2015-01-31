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
import os
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from base import BaseTest
from compass.db.api import database
from compass.db.api import permission
from compass.db.api import user as user_api
from compass.db import exception
from compass.utils import flags
from compass.utils import logsetting


class TestListPermissions(BaseTest):
    """Test list permissions."""

    def setUp(self):
        super(TestListPermissions, self).setUp()

    def tearDown(self):
        super(TestListPermissions, self).tearDown()

    def test_list_permissions(self):
        permissions = permission.list_permissions(user=self.user_object)
        self.assertIsNotNone(permissions)
        self.assertEqual(54, len(permissions))


class TestGetPermission(BaseTest):
    """Test get permission."""

    def setUp(self):
        super(TestGetPermission, self).setUp()

    def tearDown(self):
        super(TestGetPermission, self).tearDown()

    def test_get_permission(self):
        get_permission = permission.get_permission(
            1,
            user=self.user_object)
        self.assertIsNotNone(get_permission)
        expected = {
            'alias': 'list permissions',
            'description': 'list all permissions',
            'id': 1,
            'name': 'list_permissions'
        }
        self.assertDictEqual(get_permission, expected)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
