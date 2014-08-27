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
    SWITCH_IP_ADDRESS = '10.10.10.1'
    SWITCH_CREDENTIAL = {'version': 'xxx',
                         'community': 'xxx'}
    USER_CREDENTIALS = {
        'email': setting.COMPASS_ADMIN_EMAIL,
        'password': setting.COMPASS_ADMIN_PASSWORD
    }

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
        resp = json.loads(resp)
        self.token = resp['token']

    def get(self, url):
        return self.test_client.get(
            url, headers={
                setting.USER_AUTH_HEADER_NAME: self.token
            }
        )

    def post(self, url, data):
        return self.test_client.post(url, data=json.dumps(data))

    def put(self, url, data):
        return self.test_client.put(url, data=json.dumps(data))

    def delete(self, url):
        return self.test_client.delete(url)

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
        return_value = self.get(url)
        self.assertEqual(return_value.status_code, 200)


class TestClusterAPI(ApiTestCase):
    """Test cluster api."""

    def setUp(self):
        super(TestClusterAPI, self).setUp()
        # Add a cluster for test cases
        adapter_name, adapter_id, os_id, flavor_id = (
            self._get_adapter_info()
        )
        url = '/clusters'
        data = {}
        data['name'] = 'test_cluster1'
        data['adapter_id'] = adapter_id
        data['os_id'] = os_id
        data['flavor_id'] = flavor_id
        self.post(url, data)
        data = {}
        data['name'] = 'test_cluster2'
        data['adapter_id'] = adapter_id
        data['os_id'] = os_id
        data['flavor_id'] = flavor_id
        self.post(url, data)

    def tearDown(self):
        super(TestClusterAPI, self).tearDown()

    def _get_adapter_info(self):
        adapter_name = None
        adapter_id = None
        os_id = None
        flavor_id = None
        adapters = self.get(
            '/adapters'
        ).get_data()
        adapters = json.loads(adapters)
        for adapter in adapters:
            if adapter['flavors']:
                adapter_name = adapter['name']
                adapter_id = adapter['id']
                os_id = adapter['supported_oses'][0]['os_id']
                for flavor in adapter['flavors']:
                    flavor_id = flavor['id']
                    break
        return (adapter_name, adapter_id, os_id, flavor_id)

    def test_list_clusters(self):
        # list clusters successfully

        url = '/clusters'
        return_value = self.test_client.get(url)
        self.assertEqual(return_value.status_code, 200)
        resp = json.loads(return_value.get_data())
        expected = [
            {'name': 'test_cluster1'},
            {'name': 'test_cluster2'}
        ]
        self.assertTrue(item in resp.items() for item in expected[0].items())

        # give a non-existed
        url = '/clusters?name=xx'
        return_value = json.loads(
            self.test_client.get(url).get_data()
        )
        self.assertEqual([], return_value)

    def test_show_cluster(self):
        # get a cluster successfully
        url = '/clusters/1'
        return_value = self.get(url)
        self.assertEqual(return_value.status_code, 200)
        resp = json.loads(return_value.get_data())
        self.assertEqual(resp['name'], 'test_cluster1')

        # get a non-exist cluster
        url = 'clusters/999'
        return_value = self.get(url)
        self.assertEqual(return_value.status_code, 404)

    def test_add_cluster(self):
        # add a cluster successfully
        url = '/clusters'
        adapter_name, adapter_id, os_id, flavor_id = (
            self._get_adapter_info()
        )
        data = {}
        data['name'] = 'test_add_cluster'
        data['adapter_id'] = adapter_id
        data['os_id'] = os_id
        data['flavor_id'] = flavor_id
        return_value = self.post(url, data)
        resp = json.loads(return_value.get_data())
        self.assertEqual(return_value.status_code, 200)
        self.assertEqual(resp['name'], 'test_add_cluster')

        # add a duplicated cluster
        data = {}
        data['name'] = 'test_cluster1'
        data['adapter_id'] = adapter_id
        data['os_id'] = os_id
        data['flavor_id'] = flavor_id
        return_value = self.post(url, data)
        self.assertEqual(return_value.status_code, 409)

        # add a cluster with a non-existed adapter-id
        data = {}
        data['name'] = 'cluster_invalid'
        data['adapter_id'] = 9
        data['os_id'] = 1
        data['flavor_id'] = 1
        return_value = self.post(url, data)
        self.assertEqual(return_value.status_code, 400)

    def test_update_cluster(self):
        # update a cluster sucessfully
        url = 'clusters/1'
        data = {
            'name': 'cluster_update'
        }
        return_value = self.put(url, data)
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
        return_value = self.put(url, data)
        self.assertEqual(return_value.status_code, 404)

        # update a cluster with wrong keyword
        url = 'clusters/1'
        data = {
            'xxx': 'cluster_update_wrong_keyword'
        }
        return_value = self.put(url, data)
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
        return_value = self.delete(url)
        self.assertEqual(return_value.status_code, 403)

    def test_delete_cluster(self):
        # delete a cluster sucessfully
        url = '/clusters/1'
        return_value = self.delete(url)
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
        self.post(url, data)

    def tearDown(self):
        super(TestSubnetAPI, self).tearDown()

    def test_list_subnets(self):
        # list subnets successfully
        url = '/subnets'
        return_value = self.get(url)
        self.assertEqual(return_value.status_code, 200)

        # list subnets with non-exists name
        url = '/subnets?name=test'
        return_value = self.get(url)
        resp = json.loads(return_value.get_data())
        self.assertEqual(resp, [])

    def test_show_subnet(self):
        # get a subnet successfully
        url = '/subnets/1'
        return_value = self.get(url)
        resp = json.loads(return_value.get_data())
        self.assertEqual(return_value.status_code, 200)
        self.assertEqual(resp['name'], 'test_subnet')

        # give a non-existed id
        url = '/subnets/99'
        return_value = self.get(url)
        self.assertEqual(return_value.status_code, 404)

    def test_add_subnet(self):
        # subnet already added in setUp()
        # duplicate subnet
        url = '/subnets'
        data = {
            'subnet': '10.145.89.0/24',
            'name': 'test_subnet'
        }
        return_value = self.post(url, data)
        self.assertEqual(return_value.status_code, 409)

        # add subnet with invalid subnet
        data = {
            'subnet': 'xxx',
            'name': 'subnet_invalid'
        }
        return_value = self.post(url, data)
        self.assertEqual(return_value.status_code, 400)

    def test_update_subnet(self):
        # update subnet successfully
        url = '/subnets/1'
        data = {
            'subnet': '192.168.100.0/24',
            'name': 'update_subnet'
        }
        return_value = self.put(url, data)
        resp = json.loads(return_value.get_data())
        self.assertEqual(return_value.status_code, 200)
        self.assertTrue(item in data.items() for item in resp.items())

         # give a non-existed id
        url = '/subnets/99'
        data = {
            'subnet': '192.168.100.0/24',
            'name': 'subnet_invalid'
        }
        return_value = self.put(url, data)
        self.assertEqual(return_value.status_code, 404)

        # update with wrong filter
        url = '/subnets/1'
        data = {
            'xxx': 'wrong_filter'
        }
        return_value = self.put(url, data)
        self.assertEqual(return_value.status_code, 400)

    def test_delete_subnet(self):
        # delete a subnet successfully
        url = '/subnets/1'
        return_value = self.delete(url)
        self.assertEqual(return_value.status_code, 200)

        # delete a non-existed subnet
        url = '/subnets/99'
        return_value = self.delete(url)
        self.assertEqual(return_value.status_code, 404)


class TestSwitchAPI(ApiTestCase):
    """Test switch api."""

    def setUp(self):
        super(TestSwitchAPI, self).setUp()
        url = '/switches'
        datas = [
            {
                'ip': self.SWITCH_IP_ADDRESS,
                'credentials': {
                    "version": "2c",
                    "community": "public"
                },
                'vendor': 'huawei',
                'state': 'under_monitoring'
            },
            {
                'ip': '172.29.8.40',
                'credentials': {
                    "version": "2c",
                    "community": "public"
                },
                'vendor': 'huawei',
                'state': 'under_monitoring'
            }
        ]
        for data in datas:
            self.post(url, data)

    def tearDown(self):
        super(TestSwitchAPI, self).tearDown()

    def test_list_switches(self):
        url = '/switches'
        return_value = self.get(url)
        self.assertEqual(return_value.status_code, 200)

        # give a ip_int
        url = '/switches?ip_int=172.29.8.40'
        return_value = self.get(url)

        # give a invalid ip_int
        url = '/switches?ip_int=xxx'
        return_value = json.loads(self.get(url).get_data())
        self.assertEqual([], return_value)

    def test_show_switch(self):
        # show switch successfully
        url = '/switches/2'
        return_value = self.get(url)
        resp = json.loads(return_value.get_data())
        self.assertEqual(return_value.status_code, 200)
        self.assertEqual(resp['ip'], self.SWITCH_IP_ADDRESS)

        # give a non-existed id
        url = '/switches/99'
        return_value = self.get(url)
        self.assertEqual(return_value.status_code, 404)

    def test_add_switch(self):
        # add a new switch successfully
        url = '/switches'
        data = {
            'ip': '172.29.8.10',
            'credentials': {
                "version": "2c",
                "community": "public"
            },
            'vendor': 'huawei',
            'state': 'under_monitoring'
        }
        return_value = self.post(url, data)
        resp = json.loads(return_value.get_data())
        self.assertEqual(return_value.status_code, 200)
        self.assertEqual(resp['ip'], '172.29.8.10')

        # add a duplicated switch
        data = {
            'ip': self.SWITCH_IP_ADDRESS,
            'credentials': {
                "version": "2c",
                "community": "public"
            },
            'vendor': 'huawei',
            'state': 'under_monitoring'
        }
        return_value = self.post(url, data)
        self.assertEqual(return_value.status_code, 409)

        # add a invalid swtich
        data = {
            'ip': 'xxx',
            'vendor': 'huawei'
        }
        return_value = self.post(url, data)
        self.assertEqual(return_value.status_code, 400)

    def test_update_switch(self):
        # update a swithc successfully
        url = '/switches/1'
        data = {
            'vendor': 'update_vendor'
        }
        return_value = self.put(url, data)
        resp = json.loads(return_value.get_data())
        self.assertEqual(return_value.status_code, 200)
        self.assertEqual(resp['vendor'], 'update_vendor')

        # update a non-existed switch
        url = '/switches/99'
        return_value = self.put(url, data)
        self.assertEqual(return_value.status_code, 404)

        # update with wrong filter
        url = '/switches/2'
        data = {
            'xxx': 'invlid'
        }
        return_value = self.put(url, data)
        self.assertEqual(return_value.status_code, 400)

    def test_delete_switch(self):
        # delete a switch successfully
        url = '/switches/1'
        return_value = self.delete(url)
        self.assertEqual(return_value.status_code, 200)

        # delete a non-existed switch
        url = '/switches/99'
        return_value = self.delete(url)
        self.assertEqual(return_value.status_code, 404)


class TestAdapterAPI(ApiTestCase):
    """Test adapter api."""

    def setUp(self):
        super(TestAdapterAPI, self).setUp()
        self.adapter_name = None
        self.adapter_id = None
        url = '/adapters'
        adapters = json.loads(self.get(url).get_data())
        for adapter in adapters:
            if adapter['flavors']:
                self.adapter_name = adapter['name']
                self.adapter_id = adapter['id']

    def tearDown(self):
        super(TestAdapterAPI, self).tearDown()

    def test_list_adapters(self):
        # list adapters successfully
        url = '/adapters'
        return_value = self.get(url)
        self.assertEqual(return_value.status_code, 200)

        # give a non-existed filter
        url = '/adapters?name=xx'
        return_value = json.loads(self.get(url).get_data())
        self.assertEqual([], return_value)

    def test_show_adapter(self):
        # show an adapter successfully
        url = '/adapters/%s' % self.adapter_id
        return_value = self.get(url)
        resp = json.loads(return_value.get_data())
        self.assertEqual(return_value.status_code, 200)
        self.assertEqual(resp['name'], self.adapter_name)

        # give a non-existed id
        url = '/adapters/99'
        return_value = self.get(url)
        self.assertEqual(return_value.status_code, 404)

    def test_show_adapter_roles(self):
        # get adapter role successfully
        url = '/adapters/%s/roles' % self.adapter_id
        return_value = self.get(url)
        self.assertEqual(return_value.status_code, 200)

        # give a non-existed id
        url = '/adapters/99/roles'
        return_value = self.get(url)
        self.assertEqual(return_value.status_code, 404)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
