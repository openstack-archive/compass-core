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

from compass.db.api import database
from compass.db.api import permission
from compass.db.api import user as user_api
from compass.db import exception
from compass.utils import flags
from compass.utils import logsetting

os.environ['COMPASS_IGNORE_SETTING'] = 'true'


class BaseTest(unittest2.TestCase):
    """Base Class for unit test."""

    def setUp(self):
        super(BaseTest, self).setUp()
        database.init('sqlite://')
        database.create_db()
        self.user_object = (
            user_api.get_user_object(
                'admin@abc.com'
            )
        )

    def tearDown(self):
        database.drop_db()
        super(BaseTest, self).tearDown()


class TestListPermissions(BaseTest):
    """Test list permissions."""

    def setUp(self):
        super(TestListPermissions, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestListPermissions, self).tearDown()
        database.drop_db()

    def test_list_permissions(self):
        permissions = permission.list_permissions(self.user_object)
        self.assertIsNotNone(permissions)


class TestGetPermission(BaseTest):
    """Test get permission."""

    def setUp(self):
        super(TestGetPermission, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestGetPermission, self).tearDown()
        database.drop_db()

    def test_get_permission(self):
        get_permission = permission.get_permission(self.user_object, 1)
        self.assertIsNotNone(get_permission)

if __name__ == '__main__':
    unittest2.main()
