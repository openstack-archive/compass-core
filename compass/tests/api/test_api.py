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

"""test api module."""
import celery
import copy
import mock
import os
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


# from compass.api import app
from compass.db.api import adapter_holder as adapter_api
from compass.db.api import database
from compass.db.api import metadata_holder as metadata_api
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import util


class ApiTestCase(unittest2.TestCase):
    """base api test class."""

    def setUp(self):
        super(ApiTestCase, self).setUp()
        reload(setting)
        setting.CONFIG_DIR = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'data'
        )
        database.init('sqlite://')
        database.create_db()
        adapter_api.load_adapters()
        metadata_api.load_metadatas()

    def tearDown(self):
        database.drop_db()
        reload(setting)
        super(ApiTestCase, self).tearDown()

    def test_login(self):
        pass


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
