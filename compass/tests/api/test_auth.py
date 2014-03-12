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

import os
import simplejson as json
import time
import unittest2

os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)

from compass.api import app
from compass.api import auth
from compass.api import login_manager

from compass.db import database
from compass.db.model import User

from compass.utils import flags
from compass.utils import logsetting


login_manager.init_app(app)


class AuthTestCase(unittest2.TestCase):
    DATABASE_URL = 'sqlite://'
    USER_CREDENTIALS = {"email": "admin@abc.com", "password": "admin"}

    def setUp(self):
        super(AuthTestCase, self).setUp()
        logsetting.init()
        database.init(self.DATABASE_URL)
        database.create_db()

        self.test_client = app.test_client()

    def tearDown(self):
        database.drop_db()
        super(AuthTestCase, self).tearDown()

    def test_login_logout(self):
        url = '/login'
        # a. successfully login
        data = self.USER_CREDENTIALS
        return_value = self.test_client.post(url, data=data,
                                             follow_redirects=True)

        self.assertIn("Logged in successfully!", return_value.get_data())

        url = '/logout'
        return_value = self.test_client.get(url, follow_redirects=True)
        self.assertIn("You have logged out!", return_value.get_data())

    def test_login_failed(self):

        url = '/login'
        # a. Failed to login with incorrect user info
        data_list = [{"email": "xxx", "password": "admin"},
                     {"email": "admin@abc.com", "password": "xxx"}]
        for data in data_list:
            return_value = self.test_client.post(url, data=data,
                                                 follow_redirects=True)
            self.assertIn("Wrong username or password!",
                          return_value.get_data())

        # b. Inactive user
        User.query.filter_by(email="admin@abc.com").update({"active": False})

        data = {"email": "admin@abc.com", "password": "admin"}
        return_value = self.test_client.post(url, data=data,
                                             follow_redirects=True)
        self.assertIn("This username is disabled!", return_value.get_data())

    def test_get_token(self):
        url = '/token'

        # a. Failed to get token by posting incorrect user email
        req_data = json.dumps({"email": "xxx", "password": "admin"})
        return_value = self.test_client.post(url, data=req_data)
        self.assertEqual(401, return_value.status_code)

        # b. Success to get token
        req_data = json.dumps(self.USER_CREDENTIALS)
        return_value = self.test_client.post(url, data=req_data)
        resp = json.loads(return_value.get_data())
        self.assertIsNotNone(resp['token'])

    def test_header_loader(self):
        # Get Token
        url = '/token'
        req_data = json.dumps(self.USER_CREDENTIALS)
        return_value = self.test_client.post(url, data=req_data)
        token = json.loads(return_value.get_data())['token']
        user_id = auth.get_user_info_from_token(token, 50)
        self.assertEqual(1, user_id)

        # Test on token expiration.
        # Sleep 5 seconds but only allow token lifetime of 2 seconds
        time.sleep(5)
        user_id = auth.get_user_info_from_token(token, 2)
        self.assertIsNone(user_id)

        # Get None user from the incorrect token
        result = auth.get_user_info_from_token("xxx", 50)
        self.assertIsNone(result)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
