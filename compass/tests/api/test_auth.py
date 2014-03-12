import simplejson as json
import unittest2
import os

os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)

from compass.api import app
from compass.api import login_manager
from compass.api import auth
from compass.utils import logsetting
from compass.utils import flags
from compass.db import database
from compass.db.model import User

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
        max_age = app.config['REMEMBER_COOKIE_DURATION'].total_seconds()
        user_id, passowrd = auth.get_user_info_from_token(token, max_age)
        self.assertEqual(1, user_id)
        self.assertIsNotNone(passowrd)

        # Get None user from the incorrect token
        result = auth.get_user_info_from_token("xxx", max_age)
        self.assertIsNone(result)


if __name__ == '__main__':
    flags.init()
    flags.OPTIONS.logfile = '/var/log/compass/test.log'
    logsetting.init()
    unittest2.main()
