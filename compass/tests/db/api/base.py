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
from compass.db.api import switch
from compass.db.api import user as user_api
from compass.db import exception
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import setting_wrapper as setting

os.environ['COMPASS_IGNORE_SETTING'] = 'true'


reload(setting)


class BaseTest(unittest2.TestCase):
    """Base Class for unit test."""

    def setUp(self):
        super(BaseTest, self).setUp()
        database.init('sqlite://')
        database.create_db()
        self.user_object = (
            user_api.get_user_object(
                setting.COMPASS_ADMIN_EMAIL
            )
        )

    def tearDown(self):
        super(BaseTest, self).setUp()
        database.drop_db()
