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
from compass.db.api import host as host_api
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
        os.environ['COMPASS_IGNORE_SETTING'] = 'true'
        os.environ['COMPASS_CONFIG_DIR'] = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'data'
        )
        reload(setting)
        database.init('sqlite://')
        database.create_db()
        adapter_api.load_adapters(force_reload=True)
        metadata_api.load_metadatas(force_reload=True)
        adapter_api.load_flavors(force_reload=True)

        from compass.api import api as compass_api
        application = compass_api.app
        self.test_client = application.test_client()

        celery.current_app.send_task = mock.Mock()
        from compass.tasks import client as celery_client
        celery_client.celery.send_task = mock.Mock()
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

        # create a cluster
        adapter_name, adapter_id, os_id, flavor_id = (
            self._get_adapter_info()
        )
        url = '/clusters'
        data = {}
        data['name'] = 'test_cluster1'
        data['adapter_id'] = adapter_id
        data['os_id'] = os_id
        self.os_id = os_id
        data['flavor_id'] = flavor_id
        self.post(url, data)
        data = {}
        data['name'] = 'test_cluster2'
        data['adapter_id'] = adapter_id
        data['os_id'] = os_id
        self.flavor_id = flavor_id
        data['flavor_id'] = flavor_id
        self.post(url, data)

        # create a switch
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
        if not adapter_name:
            raise Exception('adapter name not found')
        if not adapter_id:
            raise Exception('adapter id not found')
        if not os_id:
            raise Exception('os id not found')
        if not flavor_id:
            raise Exception('flavor id not found')
        return (adapter_name, adapter_id, os_id, flavor_id)


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

        # disable user
        User.query.filter_by(
            email="admin@huawei.com"
        ).update({"active": False})

        request_data = json.dumps(self.USER_CREDENTIALS)
        return_value = self.test_client.post(
            url,
            data=request_data,
            follow_redirects=True
        )
        # TODO(weidong):
        # self.assertEqual(return_value.status_code, 403)
        # self.assertIn("failed to login", return_value.get_data())


class TestUserAPI(ApiTestCase):
    """Test user api."""

    def setUp(self):
        super(TestUserAPI, self).setUp()

    def tearDown(self):
        super(TestUserAPI, self).tearDown()

    def test_list_users(self):
        url = '/users'
        return_value = self.get(url)
        resp = json.loads(return_value.get_data())
        count = len(resp)
        self.assertEqual(count, 1)
        self.assertEqual(return_value.status_code, 200)


class TestClusterAPI(ApiTestCase):
    """Test cluster api."""

    def setUp(self):
        super(TestClusterAPI, self).setUp()
        # add a machine
        url = '/switches/2/machines'
        data = {
            'mac': '28:6e:d4:46:c4:25',
            'port': '1',
            'vlans': [88]
        }
        self.post(url, data)
        url = '/clusters/1/hosts'
        data = {
            'name': 'test_cluster_host',
            'reinstall_os': True,
            'machine_id': 1
        }
        self.post(url, data)

    def tearDown(self):
        super(TestClusterAPI, self).tearDown()

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
        for i, v in enumerate(resp):
            self.assertTrue(
                all(item in resp[i].items() for item in expected[i].items())
            )

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
        return_value = self.post(url, data)
        self.assertEqual(return_value.status_code, 409)

        # add a cluster with a non-existed adapter-id
        data = {}
        data['name'] = 'cluster_invalid'
        data['adapter_id'] = 9
        data['os_id'] = 1
        data['flavor_id'] = flavor_id
        return_value = self.post(url, data)
        self.assertEqual(return_value.status_code, 404)

        # add a cluster with a non-existed flavor-id
        data = {}
        data['name'] = 'cluster_invalid'
        data['adapter_id'] = adapter_id
        data['os_id'] = 1
        data['flavor_id'] = 1
        return_value = self.post(url, data)
        self.assertEqual(return_value.status_code, 404)

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
            1,
            state='INSTALLING',
            user=self.user_object,
        )
        url = '/clusters/1'
        return_value = self.delete(url)
        self.assertEqual(return_value.status_code, 403)

    def test_delete_cluster(self):
        # delete a cluster sucessfully
        url = '/clusters/1'
        return_value = self.delete(url)
        self.assertEqual(return_value.status_code, 200)

    def test_list_cluster_hosts(self):
        # list cluster_hosts successfully
        url = '/clusters/1/hosts'
        return_value = self.get(url)
        resp = json.loads(return_value.get_data())
        count = len(resp)
        self.assertEqual(count, 1)
        self.assertEqual(return_value.status_code, 200)

        # give a non-existed cluster_id
        url = '/clusters/99/hosts'
        return_value = self.get(url)
        self.assertEqual(return_value.status_code, 404)

    def test_show_cluster_host(self):
        # show a cluster_host successfully
        url = '/clusters/1/hosts/1'
        return_value = self.get(url)
        resp = json.loads(return_value.get_data())
        self.assertEqual(resp['hostname'], 'test_cluster_host')

        # give a non-existed host_id
        url = '/clusters/1/hosts/99'
        return_value = self.get(url)
        self.assertEqual(return_value.status_code, 404)

    def test_add_cluster_host(self):
        # add a cluster_host successfully
        url = '/clusters/2/hosts'
        data = {
            'name': 'add_cluster_host',
            'reinstall_os': True,
            'machine_id': 1
        }
        return_value = self.post(url, data)
        resp = json.loads(return_value.get_data())
        self.assertEqual(return_value.status_code, 200)
        self.assertEqual(resp['hostname'], 'add_cluster_host')

        # add a duplicate cluster_host
        data = {
            'name': 'duplicate_cluster_host',
            'reinstall_os': True,
            'machine_id': 1
        }
        return_value = self.post(url, data)
        self.assertEqual(return_value.status_code, 409)

    def test_update_cluster_host(self):
        # update cluster_host successfully
        url = '/clusters/1/hosts/1'
        data = {
            'roles': [
                'allinone-compute'
            ]
        }
        return_value = self.put(url, data)
        self.assertEqual(return_value.status_code, 200)

    def test_delete_cluster_host(self):
        # delete a cluster_host successfully
        url = '/clusters/1/hosts/1'
        return_value = self.delete(url)
        self.assertEqual(return_value.status_code, 200)

        # give a non-existed cluster_id
        url = '/clusters/99/hosts/1'
        return_value = self.delete(url)
        self.assertEqual(return_value.status_code, 404)


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
        resp = json.loads(return_value.get_data())
        count = len(resp)
        self.assertEqual(count, 1)
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

    def tearDown(self):
        super(TestSwitchAPI, self).tearDown()

    def test_list_switches(self):
        url = '/switches'
        return_value = self.get(url)
        resp = json.loads(return_value.get_data())
        count = len(resp)
        self.assertEqual(count, 2)
        self.assertEqual(return_value.status_code, 200)

        # give a ip_int
        url = '/switches?ip_int=172.29.8.40'
        return_value = self.get(url)
        self.assertEqual(return_value.status_code, 200)

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

    def test_add_switches(self):
        # add switches
        url = '/switchesbatch'
        data = [
            {
                'ip': '172.29.8.30',
                'vendor': 'Huawei',
                'credentials': {
                    "version": "2c",
                    "community": "public"
                }
            }, {
                'ip': '172.29.8.40'
            }
        ]
        return_value = self.post(url, data)
        resp = json.loads(return_value.get_data())
        success = []
        fail = []
        for item in resp['switches']:
            success.append(item['ip'])
        for item in resp['fail_switches']:
            fail.append(item['ip'])
        self.assertEqual(return_value.status_code, 200)
        self.assertIn('172.29.8.30', success)
        self.assertIn('172.29.8.40', fail)

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
        resp = json.loads(return_value.get_data())
        count = len(resp)
        self.assertEqual(count, 3)
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


class TestHostAPI(ApiTestCase):
    """Test host api."""

    def setUp(self):
        super(TestHostAPI, self).setUp()
        # add a machine to get the machine_id
        url = 'switches/1/machines'
        datas = [
            {
                'mac': '28:6e:d4:46:c4:25',
                'port': '1',
                'location': 'test_location1'
            },
            {
                'mac': '00:0c:29:bf:eb:1d',
                'port': '1',
                'location': 'test_location2'
            }
        ]
        machine_id = {}
        for i, data in enumerate(datas):
            return_value = self.post(url, data)
            resp = json.loads(return_value.get_data())
            machine_id[i] = resp['machine_id']

        # add a host
        url = '/clusters/1/hosts'
        datas = [
            {
                'machine_id': machine_id[0],
                'name': 'test_host1',
                'reinstall_os': True
            },
            {
                'machine_id': machine_id[1],
                'name': 'test_hosts2',
                'reinstall_os': True
            }
        ]
        for data in datas:
            self.post(url, data)

        # add host_network
        url = '/subnets'
        data = {
            'subnet': '10.172.20.0/24',
            'name': 'test_subnet'
        }
        self.post(url, data)
        url = '/hosts/1/networks'
        datas = [
            {
                'interface': 'eth0',
                'ip': '10.172.20.91',
                'subnet_id': 1,
                'is_mgmt': False,
                'is_promiscuous': False
            },
            {
                'interface': 'eth1',
                'ip': '10.172.20.110',
                'subnet_id': 1,
                'is_mgmt': False,
                'is_promiscuous': False
            }
        ]
        for data in datas:
            self.post(url, data)

    def tearDown(self):
        super(TestHostAPI, self).tearDown()

    def test_list_hosts(self):
        # list hosts successfully
        url = '/hosts'
        return_value = self.get(url)
        resp = json.loads(return_value.get_data())
        count = len(resp)
        self.assertEqual(count, 2)
        self.assertEqual(return_value.status_code, 200)

        # give a non-existed name
        url = '/hosts?name=xx'
        return_value = self.get(url)
        resp = json.loads(return_value.get_data())
        self.assertEqual([], resp)

    def test_show_host(self):
        # show a host successfully
        url = '/hosts/1'
        return_value = self.get(url)
        resp = json.loads(return_value.get_data())
        self.assertEqual(return_value.status_code, 200)
        self.assertEqual(resp['name'], 'test_host1')

        # give a non-existed id
        url = '/hosts/99'
        return_value = self.get(url)
        self.assertEqual(return_value.status_code, 404)

    def test_list_machines_or_hosts(self):
        url = '/machines-hosts'
        return_value = self.get(url)
        self.assertEqual(return_value.status_code, 200)

    def test_show_machine_or_host(self):
        url = '/machines-hosts/1'
        return_value = self.get(url)
        self.assertEqual(return_value.status_code, 200)

    def test_update_host(self):
        # update a host successfully
        url = '/hosts/1'
        data = {
            'name': 'update_host'
        }
        return_value = self.put(url, data)
        resp = json.loads(return_value.get_data())
        self.assertEqual(return_value.status_code, 200)
        self.assertEqual(resp['name'], 'update_host')

        # give a wrong filter
        data = {
            'location': 'update_location'
        }
        return_value = self.put(url, data)
        self.assertEqual(return_value.status_code, 400)
        self.assertIn('are not supported', return_value.get_data())

        # give a non-existed id
        url = '/hosts/99'
        data = {
            'name': 'host'
        }
        return_value = self.put(url, data)
        self.assertEqual(return_value.status_code, 404)

    def test_delete_host(self):
        # delete a host successfully
        url = '/hosts/2'
        return_value = self.delete(url)
        self.assertEqual(return_value.status_code, 200)

        # give a non-existed id
        url = '/hosts/99'
        return_value = self.delete(url)
        self.assertEqual(return_value.status_code, 404)

    def test_list_host_networks(self):
        url = '/hosts/1/networks'
        return_value = self.get(url)
        resp = json.loads(return_value.get_data())
        count = len(resp)
        self.assertEqual(count, 2)
        self.assertEqual(return_value.status_code, 200)

    def test_show_host_network(self):
        url = '/hosts/1/networks/1'
        return_value = self.get(url)
        resp = json.loads(return_value.get_data())
        self.assertEqual(return_value.status_code, 200)
        self.assertEqual(resp['ip'], '10.172.20.91')


class TestSwitchMachines(ApiTestCase):

    def setUp(self):
        super(TestSwitchMachines, self).setUp()
        url = '/switches/2/machines'
        datas = [
            {
                'mac': '28:6e:d4:46:c4:25',
                'port': '1',
                'vlans': [88]
            },
            {
                'mac': '00:0c:29:bf:eb:1d',
                'port': '1',
                'vlans': [1]
            }
        ]
        for data in datas:
            self.post(url, data)

    def tearDown(self):
        super(TestSwitchMachines, self).tearDown()

    def test_list_switch_machines(self):
        # list switch machines successfully
        url = '/switches/2/machines'
        return_value = self.get(url)
        resp = json.loads(return_value.get_data())
        count = len(resp)
        self.assertEqual(count, 2)
        self.assertEqual(return_value.status_code, 200)

        # give a non-existed switch_id
        url = '/switches/99/machines'
        return_value = self.get(url)
        self.assertEqual(return_value.status_code, 404)

    def test_add_switch_machine(self):
        # add a switch machine successfully
        url = '/switches/2/machines'
        data = {
            'mac': '00:0c:29:5b:ee:eb',
            'port': '1',
            'vlans': [10]
        }
        return_value = self.post(url, data)
        resp = json.loads(return_value.get_data())
        self.assertEqual(return_value.status_code, 200)
        self.assertEqual(resp['mac'], '00:0c:29:5b:ee:eb')

        # add a dulicated switch machine
        url = '/switches/2/machines'
        data = {
            'mac': '28:6e:d4:46:c4:25',
            'port': '1',
            'vlans': [88]
        }
        return_value = self.post(url, data)
        self.assertEqual(return_value.status_code, 409)

        # add a invalid switch machine
        url = 's/witchedes'
        data = {
            'mac': 'xxx'
        }
        return_value = self.post(url, data)
        self.assertEqual(return_value.status_code, 404)

    def test_add_switch_machines(self):
        # batch switch machines
        url = '/switches'
        return_value = self.get(url)

        url = '/switches/machines'
        data = [{
            "switch_ip": "0.0.0.0",
            "mac": "1a:2b:3c:4d:5e:6f",
            "port": "100"
        }, {
            "switch_ip": "0.0.0.0",
            "mac": "a1:b2:c3:d4:e5:f6",
            "port": "101"
        }, {
            "switch_ip": "0.0.0.0",
            "mac": "a1:b2:c3:d4:e5:f6",
            "port": "101"
        }, {
            "switch_ip": "0.0.0.0",
            "mac": "a1:b2:c3:d4:e5:f6",
            "port": "102"
        }, {
            "switch_ip": "10.10.10.1",
            "mac": "b1:b2:c3:d4:e5:f6",
            "port": "200"
        }, {
            "switch_ip": "127.0.0.2",
            "mac": "a1:b2:f3:d4:e5:f6",
            "port": "100"
        }]
        return_value = self.post(url, data)
        expected = [{
            'switch_ip': '0.0.0.0',
            'port': '100',
            'mac': '1a:2b:3c:4d:5e:6f'
        }, {
            'switch_ip': '0.0.0.0',
            'port': '101',
            'mac': 'a1:b2:c3:d4:e5:f6'
        }, {
            'switch_ip': '10.10.10.1',
            'port': '200',
            'mac': 'b1:b2:c3:d4:e5:f6'
        }]
        expect_duplicate = [{'mac': 'a1:b2:c3:d4:e5:f6', 'port': '101'}]
        expect_failed = [
            {'mac': 'a1:b2:f3:d4:e5:f6', 'port': '100'},
            {'mac': 'a1:b2:c3:d4:e5:f6', 'port': '102'}
        ]
        resp = json.loads(return_value.get_data())
        res = []
        res_du = []
        res_fail = []
        for k, v in resp.items():
            if k == 'switches_machines':
                for item in v:
                    res.append(item)
            if k == 'duplicate_switches_machines':
                for item in v:
                    res_du.append(item)
            if k == 'fail_switches_machines':
                for item in v:
                    res_fail.append(item)
        self.assertEqual(len(res), len(expected))
        for i, v in enumerate(res):
            self.assertDictContainsSubset(
                expected[i], res[i]
            )
        self.assertEqual(len(res_fail), len(expect_failed))
        for i, v in enumerate(res_fail):
            self.assertDictContainsSubset(
                expect_failed[i], res_fail[i]
            )
        self.assertEqual(len(res_du), len(expect_duplicate))
        for i, v in enumerate(res_du):
            self.assertDictContainsSubset(
                expect_duplicate[i], res_du[i]
            )

    def test_show_switch_machine(self):
        # show a switch_machine successfully
        url = '/switches/2/machines/1'
        return_value = self.get(url)
        resp = json.loads(return_value.get_data())
        self.assertEqual(return_value.status_code, 200)
        self.assertEqual(resp['mac'], '28:6e:d4:46:c4:25')

        # give a non-existed switch_id
        url = '/switches/99/machines/1'
        return_value = self.get(url)
        self.assertEqual(return_value.status_code, 404)

    def test_update_switch_machine(self):
        # update a switch_machine successfully
        url = '/switches/2/machines/1'
        data = {
            'port': '100'
        }
        return_value = self.put(url, data)
        resp = json.loads(return_value.get_data())
        self.assertEqual(return_value.status_code, 200)
        self.assertEqual(resp['port'], '100')

        # give a non-existed switch_id
        url = '/switches/99/machines/1'
        data = {
            'port': '99'
        }
        return_value = self.put(url, data)
        self.assertEqual(return_value.status_code, 404)

        # give a wrong filter
        url = '/switches/2/machines/1'
        data = {
            'mac': '00:0c:29:a5:f2:05'
        }
        return_value = self.put(url, data)
        self.assertEqual(return_value.status_code, 400)
        self.assertIn('are not supported', return_value.get_data())

    def test_delete_switch_machine(self):
        # delete a switch_machine successfully
        url = '/switches/2/machines/1'
        return_value = self.delete(url)
        self.assertEqual(return_value.status_code, 200)


class TestMetadataAPI(ApiTestCase):
    """Test metadata api."""

    def setUp(self):
        super(TestMetadataAPI, self).setUp()

    def tearDown(self):
        super(TestMetadataAPI, self).tearDown()

    def test_get_os_ui_metadata(self):
        url = '/oses/%s/ui_metadata' % self.os_id
        return_value = self.get(url)
        self.assertEqual(return_value.status_code, 200)
        self.assertIn('os_global_config', return_value.get_data())

    def test_get_flavor_ui_metadata(self):
        url = '/flavors/%s/ui_metadata' % self.flavor_id
        return_value = self.get(url)
        self.assertEqual(return_value.status_code, 200)
        self.assertIn('flavor_config', return_value.get_data())


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
