#!/usr/bin/python
#
# Copyright 2014 Huawei Technologies Co. Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""test api module."""
import simplejson as json
import unittest2

from compass.api import app
from compass.api.exception import ItemNotFound
from compass.db.api import database


app.config['TESTING'] = True


class ApiTestCase(unittest2.TestCase):
    """base api test class."""

    DATABASE_URL = 'sqlite://'

    def setUp(self):
        super(ApiTestCase, self).setUp()
        database.init(self.DATABASE_URL)
        database.create_db()

        self.test_client = app.test_client()

    def tearDown(self):
        database.drop_db()
        super(ApiTestCase, self).tearDown()

    def test_get_user(self):
        url = "/v1.0/users/1"
        return_value = self.test_client.get(url)
        data = json.loads(return_value.get_data())
        excepted_code = 200
        self.assertEqual(return_value.status_code, excepted_code)

        self.assertEqual(1, data['id'])
        self.assertEqual("admin@abc.com", data['email'])

        url = "/v1.0/users/2"
        return_value = self.test_client.get(url)
        excepted_code = 404
        self.assertEqual(return_value.status_code, excepted_code)
