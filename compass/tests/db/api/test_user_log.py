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
from compass.db.api import user as user_api
from compass.db.api import user_log
from compass.db import exception
from compass.utils import flags
from compass.utils import logsetting


class TestListUserActions(BaseTest):
    """Test user actions."""

    def setUp(self):
        super(TestListUserActions, self).setUp()

    def tearDown(self):
        super(TestListUserActions, self).tearDown()

    def test_list_user_actions(self):
        user_log.log_user_action(
            self.user_object.id,
            action='/testaction'
        )
        user_action = user_log.list_user_actions(
            self.user_object,
            self.user_object.id
        )
        self.assertEqual(
            1,
            user_action['user_id']
        )

    def test_list_none_user_actions(self):
        user_log.log_user_action(
            self.user_object.id,
            action='/testaction'
        )
        user_action = user_log.list_user_actions(
            self.user_object,
            2
        )
        self.assertEqual([], user_action['logs'])


class TestListActions(BaseTest):
    """Test list actions."""

    def setUp(self):
        super(TestListActions, self).setUp()

    def tearDown(self):
        super(TestListActions, self).tearDown()

    def test_list_actions(self):
        user_log.log_user_action(
            self.user_object.id,
            action='/testaction'
        )
        action = user_log.list_actions(self.user_object)
        self.assertIsNotNone(action)


class TestDelUserActions(BaseTest):
    """Test delete user actions."""

    def setUp(self):
        super(TestDelUserActions, self).setUp()

    def tearDown(self):
        super(TestDelUserActions, self).tearDown()

    def test_del_user_actions(self):
        user_log.log_user_action(
            self.user_object.id,
            action='/testaction'
        )
        user_log.del_user_actions(
            self.user_object,
            self.user_object.id
        )
        del_user_action = user_log.list_user_actions(
            self.user_object,
            self.user_object.id
        )
        self.assertEqual([], del_user_action['logs'])


class TestDelActions(BaseTest):
    """Test delete actions."""

    def setUp(self):
        super(TestDelActions, self).setUp()

    def tearDown(self):
        super(TestDelActions, self).setUp()

    def test_del_actions(self):
        user_log.log_user_action(
            self.user_object.id,
            action='/testaction'
        )
        user_log.del_actions(
            self.user_object
        )
        del_action = user_log.list_actions(
            self.user_object
        )
        self.assertEqual([], del_action)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
