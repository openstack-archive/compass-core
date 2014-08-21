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
import simplejson as json
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from compass.api import login_manager
from compass.db.api import adapter_holder as adapter_api
from compass.db.api import cluster as cluster_api
from compass.db.api import database
from compass.db.api import metadata_holder as metadata_api
from compass.db.api import user as user_api
from compass.db.models import User
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import util


class ApiTestCase(unittest2.TestCase):
    """base api test class."""

    CLUSTER_NAME = "Test_CLUSTER"
    SWITCH_IP_ADDRESS1 = '10.10.10.1'
    SWITCH_CREDENTIAL = {'version': 'xxx',
                         'community': 'xxx'}
    USER_CREDENTIALS = {'email': 'admin@huawei.com', 'password': 'admin'}

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

        from compass.api import api as compass_api
        application = compass_api.app
        self.test_client = application.test_client()

        celery.current_app.send_task = mock.Mock()
        url = '/users/token'
        data = self.USER_CREDENTIALS
        request_data = json.dumps(data)
        return_value = self.test_client.post(
            url,
            data=request_data,
        )
        resp = return_value.get_data()
#        print 'resp is :%s ' % resp
        resp = json.loads(resp)
        self.token = resp['token']

    def tearDown(self):
        database.drop_db()
        reload(setting)
        super(ApiTestCase, self).tearDown()


class TestAuth(ApiTestCase):
    """Test user authentication."""

    def setUp(self):
        super(TestAuth, self).setUp()

    def tearDown(self):
        super(TestAuth, self).tearDown()

    def test_login_logout(self):
        # Test login
        url = '/users/token'
        data = self.USER_CREDENTIALS
        request_data = json.dumps(data)
        return_value = self.test_client.post(
            url,
            data=request_data,
            follow_redirects=True
        )
        self.assertEqual(return_value.status_code, 200)
        # Test logout
        url = '/users/logout'
        return_value = self.test_client.post(
            url,
            follow_redirects=True
        )
        self.assertEqual(return_value.status_code, 200)

    def test_login_failed(self):
        url = '/users/token'
        # Wrong credentials
        data_list = [
            {"email": "xxx", "password": "admin"},
            {"email": "admin@huawei.com", "password": "xxx"}
        ]
        for data in data_list:
            return_value = self.test_client.post(
                url,
                data=data,
                follow_redirects=True
            )
            self.assertEqual(return_value.status_code, 400)
            self.assertIn('missing email or password', return_value.get_data())

        # Login without 'remember me'
        User.query.filter_by(
            email="admin@huawei.com"
        ).update({"active": False})
        data = {
            "email": "admin@huawei.com",
            "password": "admin"
        }
        request_data = json.dumps(data)
        return_value = self.test_client.post(
            url,
            data=request_data,
            follow_redirects=True
        )
        self.assertEqual(return_value.status_code, 403)
        self.assertIn("failed to login", return_value.get_data())


class TestUserAPI(ApiTestCase):
    """Test user api."""

    def setUp(self):
        super(TestUserAPI, self).setUp()

    def tearDown(self):
        super(TestUserAPI, self).tearDown()

    def test_list_users(self):
        url = '/users'
        return_value = self.test_client.get(
            url,
            data=self.token
        )
        self.assertEqual(return_value.status_code, 200)


class TestClusterAPI(ApiTestCase):
    """Test cluster api."""

    def setUp(self):
        super(TestClusterAPI, self).setUp()
        # Add a cluster for test cases

        adapter_name = None
        adapter_id = None
        adapter_os_id = None
        adapter_flavor_id = None

        adapters = self.test_client.get(
            '/adapters'
        ).get_data()
        adapters = json.loads(adapters)
        for adapter in adapters:
            if adapter['flavors']:
                adapter_name = adapter['name']
                adapter_id = adapter['id']
                adapter_os_id = adapter['supported_oses'][0]['os_id']
                for flavor in adapter['flavors']:
                    if flavor['display_name'] == 'allinone':
                        adapter_flavor_id = flavor['id']
                        break
        url = '/clusters'
        data = {}
        data['name'] = adapter_name
        data['adapter_id'] = adapter_id
        data['os_id'] = adapter_os_id
        data['flavor_id'] = adapter_flavor_id
        self.test_client.post(
            url,
            data=json.dumps(data)
        )

    def tearDown(self):
        super(TestClusterAPI, self).tearDown()

    def test_list_clusters(self):
        # list clusters successfully

        url = '/clusters'
        return_value = self.test_client.get(url)
        self.assertEqual(return_value.status_code, 200)

        # give a non-existed
        url = '/clusters?name=xx'
        return_value = json.loads(
            self.test_client.get(url).get_data()
        )
        self.assertEqual([], return_value)

    def test_show_cluster(self):
        # get a cluster successfully
        url = '/clusters/1'
        return_value = self.test_client.get(url)
        self.assertEqual(return_value.status_code, 200)
        resp = json.loads(return_value.get_data())
        self.assertEqual(resp['name'], 'openstack_icehouse')

        # get a non-exist cluster
        url = 'clusters/999'
        return_value = self.test_client.get(url)
        self.assertEqual(return_value.status_code, 404)

    def test_add_cluster(self):
        # add a cluster alrady successfully
        url = '/clusters'
        data = {}
        data['name'] = 'test_cluster'
        data['adapter_id'] = 5
        data['os_id'] = 3
        data['flavor_id'] = 1
        return_value = self.test_client.post(
            url,
            data=json.dumps(data)
        )
        resp = json.loads(return_value.get_data())
        self.assertEqual(return_value.status_code, 200)
        self.assertEqual(resp['name'], 'test_cluster')

        # add a duplicated cluster
        data = {}
        data['name'] = 'openstack_icehouse'
        data['adapter_id'] = 5
        data['os_id'] = 3
        data['flavor_id'] = 1
        return_value = self.test_client.post(
            url,
            data=json.dumps(data)
        )
        self.assertEqual(return_value.status_code, 409)

        # add a cluster with a non-existed adapter-id
        data = {}
        data['name'] = 'cluster_invalid'
        data['adapter_id'] = 9
        data['os_id'] = 1
        data['flavor_id'] = 1
        return_value = self.test_client.post(
            url,
            data=json.dumps(data)
        )
        self.assertEqual(return_value.status_code, 400)

    def test_update_cluster(self):
        # update a cluster sucessfully
        url = 'clusters/1'
        data = {
            'name': 'cluster_update'
        }
        return_value = self.test_client.put(
            url,
            data=json.dumps(data)
        )
        self.assertEqual(return_value.status_code, 200)
        self.assertEqual(
            json.loads(return_value.get_data())['name'],
            'cluster_update'
        )

        # update a non-existed cluster
        url = 'clusters/99'
        data = {
            'name': 'cluster_update_non_existed'
        }
        return_value = self.test_client.put(
            url,
            data=json.dumps(data)
        )
        self.assertEqual(return_value.status_code, 404)

        # update a cluster with wrong keyword
        url = 'clusters/1'
        data = {
            'xxx': 'cluster_update_wrong_keyword'
        }
        return_value = self.test_client.put(
            url,
            data=json.dumps(data)
        )
        self.assertEqual(return_value.status_code, 400)

    def test_delete_cluster_not_editable(self):
        # delete a cluster which state is installing
        self.user_object = (
            user_api.get_user_object(
                setting.COMPASS_ADMIN_EMAIL
            )
        )
        cluster_api.update_cluster_state(
            self.user_object,
            1,
            state='INSTALLING'
        )
        url = '/clusters/1'
        return_value = self.test_client.delete(url)
        self.assertEqual(return_value.status_code, 403)

    def test_delete_cluster(self):
        # delete a cluster sucessfully
        url = '/clusters/1'
        return_value = self.test_client.delete(url)
        self.assertEqual(return_value.status_code, 200)


class TestSubnetAPI(ApiTestCase):
    """Test subnet api."""

    def setUp(self):
        super(TestSubnetAPI, self).setUp()
        url = '/subnets'
        data = {
            'subnet': '10.145.89.0/24',
            'name': 'test_subnet'
        }
        self.test_client.post(
            url,
            data=json.dumps(data)
        )

    def tearDown(self):
        super(TestSubnetAPI, self).tearDown()

    def test_list_subnets(self):
        # list subnets successfully
        url = '/subnets'
        return_value = self.test_client.get(url)
        self.assertEqual(return_value.status_code, 200)

        # list subnets with non-exists name
        url = '/subnets?name=test'
        return_value = self.test_client.get(url)
        resp = json.loads(return_value.get_data())
        self.assertEqual(resp, [])

    def test_show_subnet(self):
        # get a subnet successfully
        url = '/subnets/1'
        return_value = self.test_client.get(url)
        resp = json.loads(return_value.get_data())
        self.assertEqual(return_value.status_code, 200)
        self.assertEqual(resp['name'], 'test_subnet')

        # give a non-existed id
        url = '/subnets/99'
        return_value = self.test_client.get(url)
        self.assertEqual(return_value.status_code, 404)

    def test_add_subnet(self):
        # subnet already added in setUp()
        # duplicate subnet
        url = '/subnets'
        data = {
            'subnet': '10.145.89.0/24',
            'name': 'test_subnet'
        }
        return_value = self.test_client.post(
            url,
            data=json.dumps(data)
        )
        self.assertEqual(return_value.status_code, 409)

        # add subnet with invalid subnet
        data = {
            'subnet': 'xxx',
            'name': 'subnet_invalid'
        }
        return_value = self.test_client.post(
            url,
            data=json.dumps(data)
        )
        self.assertEqual(return_value.status_code, 400)

    def test_update_subnet(self):
        # update subnet successfully
        url = '/subnets/1'
        data = {
            'subnet': '192.168.100.0/24',
            'name': 'update_subnet'
        }
        return_value = self.test_client.put(
            url,
            data=json.dumps(data)
        )
        resp = json.loads(return_value.get_data())
        self.assertEqual(return_value.status_code, 200)
        self.assertTrue(item in data.items() for item in resp.items())


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
