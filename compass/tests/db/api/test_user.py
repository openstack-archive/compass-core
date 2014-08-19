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

from base import BaseTest
from compass.db.api import database
from compass.db.api import user as user_api
from compass.db import exception
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import setting_wrapper as setting
os.environ['COMPASS_IGNORE_SETTING'] = 'true'
reload(setting)


class TestGetUserObject(unittest2.TestCase):
    """Test get user object."""

    def setUp(self):
        super(TestGetUserObject, self).setUp()
        reload(setting)
        setting.CONFIG_DIR = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'data'
        )
        database.init('sqlite://')
        database.create_db()

    def tearDown(self):
        reload(setting)
        database.drop_db()

    def test_get_user_object(self):
        user_object = user_api.get_user_object(setting.COMPASS_ADMIN_EMAIL)
        self.assertIsNotNone(user_object)

    def test_get_user_object_unauthorized(self):
        self.assertRaises(
            exception.Unauthorized,
            user_api.get_user_object,
            'admin@bac.com'
        )


class TestGetRecordCleanToken(BaseTest):
    """Test get user object from token."""
    """Test record user token."""
    """Test clean user token."""

    def setUp(self):
        super(TestGetRecordCleanToken, self).setUp()

    def tearDown(self):
        super(TestGetRecordCleanToken, self).tearDown()

    def test_record_user_token(self):
        token = user_api.record_user_token(
            self.user_object,
            'test_token',
            datetime.datetime.now() + datetime.timedelta(seconds=10000)
        )
        self.assertIsNotNone(token)

    def test_clean_user_token(self):
        token = user_api.clean_user_token(self.user_object, 'test_token')
        self.assertEqual([], token)

    def test_get_user_object_from_token(self):
        token = user_api.record_user_token(
            self.user_object,
            'test_token',
            datetime.datetime.now() + datetime.timedelta(seconds=10000)
        )
        self.assertIsNotNone(token)

    def test_get_user_object_from_token_forbidden(self):
        self.assertRaises(
            exception.Forbidden,
            user_api.get_user_object_from_token,
            'token'
        )


class TestGetUser(BaseTest):
    """Test get user."""

    def setUp(self):
        super(TestGetUser, self).setUp()

    def tearDown(self):
        super(TestGetUser, self).tearDown()

    def test_get_user(self):
        user = user_api.get_user(self.user_object, self.user_object.id)
        self.assertIsNotNone(user)


class TestListUsers(BaseTest):
    """Test list users."""

    def setUp(self):
        super(TestListUsers, self).setUp()

    def tearDown(self):
        super(TestListUsers, self).tearDown()

    def test_list_users(self):
        user = user_api.list_users(self.user_object)
        self.assertIsNotNone(user)


class TestAddUser(BaseTest):
    """Test add user."""

    def setUp(self):
        super(TestAddUser, self).setUp()

    def tearDown(self):
        super(TestAddUser, self).tearDown()

    def test_add_user(self):
        user_objs = user_api.add_user(
            self.user_object,
            email='test@abc.com',
            password='password'
        )
        self.assertEqual('test@abc.com', user_objs['email'])


class TestDelUser(BaseTest):
    """Test delete user."""

    def setUp(self):
        super(TestDelUser, self).setUp()

    def tearDown(self):
        super(TestDelUser, self).tearDown()

    def test_del_user(self):
        user_api.del_user(self.user_object, self.user_object.id)
        del_user = user_api.list_users(self.user_object)
        self.assertEqual([], del_user)


class TestUpdateUser(BaseTest):
    """Test update user."""

    def setUp(self):
        super(TestUpdateUser, self).setUp()

    def tearDown(self):
        super(TestUpdateUser, self).tearDown()

    def test_update_admin(self):
        user_objs = user_api.update_user(
            self.user_object,
            self.user_object.id,
            email=setting.COMPASS_ADMIN_EMAIL,
            firstname='a',
            lastname='b',
            password='ab',
            is_admin=True,
            active=True
        )
        self.assertEqual(setting.COMPASS_ADMIN_EMAIL, user_objs['email'])

    def test_user_id(self):
        user_api.add_user(
            self.user_object,
            email='dummy@abc.com',
            password='dummy'
        )
        user_objs = user_api.update_user(
            self.user_object,
            2,
            is_admin=False,
            active=True
        )
        self.assertEqual(2, user_objs['id'])

    def test_not_admin(self):
        self.assertRaises(
            exception.Forbidden,
            user_api.update_user,
            self.user_object,
            self.user_object.id
        )


class TestGetPermissions(BaseTest):
    """Test get permissions."""

    def setUp(self):
        super(TestGetPermissions, self).setUp()

    def tearDown(self):
        super(TestGetPermissions, self).tearDown()

    def test_get_permissions(self):
        user_permissions = user_api.get_permissions(
            self.user_object,
            self.user_object.id
        )
        self.assertIsNotNone(user_permissions)


class TestAddGetDelUserPermission(BaseTest):
    """Test add user permission."""
    """Test delete user permission."""
    """Test get user permission."""

    def setUp(self):
        super(TestAddGetDelUserPermission, self).setUp()

    def tearDown(self):
        super(TestAddGetDelUserPermission, self).tearDown()

    def test_get_permission(self):
        permission = user_api.get_permission(
            self.user_object,
            self.user_object.id,
            1,
            True
        )
        self.assertIsNotNone(permission)

    def test_add_permission(self):
        permission = user_api.add_permission(
            self.user_object,
            self.user_object.id,
            permission_id=2
        )
        expected = {'permission_id': 2}
        self.assertTrue(
            item in permission[0].items() for item in expected.items()
        )

    def test_del_permission(self):
        user_api.del_permission(
            self.user_object,
            self.user_object.id,
            1
        )
        del_user = user_api.get_permissions(
            self.user_object,
            self.user_object.id
        )
        self.assertEqual([], del_user)


class TestUpdatePermissions(BaseTest):
    """Test update permission."""

    def setUp(self):
        super(TestUpdatePermissions, self).setUp()

    def tearDown(self):
        super(TestUpdatePermissions, self).tearDown()

    def test_remove_permissions(self):
        user_api.update_permissions(
            self.user_object,
            self.user_object.id,
            remove_permissions=1
        )
        del_user_permission = user_api.get_permissions(
            self.user_object,
            self.user_object.id
        )
        self.assertEqual([], del_user_permission)

    def test_add_permissions(self):
        add_permission = user_api.update_permissions(
            self.user_object,
            self.user_object.id,
            add_permissions=2
        )
        expected = {'permission_id': 2}
        self.assertTrue(
            item in add_permission[0].items() for item in expected.items()
        )


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
