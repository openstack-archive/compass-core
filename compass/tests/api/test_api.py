"""test api module"""
from copy import deepcopy
from celery import current_app
from mock import Mock
import simplejson as json
import os
import csv
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from compass.api import app
from compass.db import database
from compass.db.model import Switch
from compass.db.model import Machine
from compass.db.model import Cluster
from compass.db.model import ClusterState
from compass.db.model import ClusterHost
from compass.db.model import HostState
from compass.db.model import Adapter
from compass.db.model import Role
from compass.db.model import SwitchConfig
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import util


class ApiTestCase(unittest2.TestCase):
    """base api test class."""

    CLUSTER_NAME = "Test1"
    SWITCH_IP_ADDRESS1 = '10.10.10.1'
    SWITCH_CREDENTIAL = {'version': 'xxx',
                         'community': 'xxx'}
    DATABASE_URL = 'sqlite://'

    def setUp(self):
        super(ApiTestCase, self).setUp()
        logsetting.init()
        database.init(self.DATABASE_URL)
        database.create_db()
        self.test_client = app.test_client()

        # We do not want to send a real task as our test environment
        # does not have a AMQP system set up. TODO(): any better way?
        current_app.send_task = Mock()

    def tearDown(self):
        database.drop_db()
        super(ApiTestCase, self).tearDown()


class TestSwtichMachineAPI(ApiTestCase):
    """test switch machine api"""

    SWITCH_RESP_TPL = {"state": "under_monitoring",
                       "ip": "",
                       "link": {"href": "",
                                "rel": "self"},
                       "id": ""}

    def setUp(self):
        super(TestSwtichMachineAPI, self).setUp()
        logsetting.init()
        # Create one switch in database
        with database.session() as session:
            test_switch = Switch(ip=self.SWITCH_IP_ADDRESS1)
            test_switch.credential = self.SWITCH_CREDENTIAL
            test_switch.state = 'under_monitoring'
            session.add(test_switch)

    def tearDown(self):
        super(TestSwtichMachineAPI, self).tearDown()

    def test_get_switch_list(self):
        """tst get switch list api"""
        # Prepare testing data
        with database.session() as session:
            switches = [Switch(ip='192.168.1.1',
                               credential=self.SWITCH_CREDENTIAL),
                        Switch(ip='192.168.1.2',
                               credential=self.SWITCH_CREDENTIAL),
                        Switch(ip='192.1.192.1',
                               credential=self.SWITCH_CREDENTIAL),
                        Switch(ip='192.1.192.2',
                               credential=self.SWITCH_CREDENTIAL),
                        Switch(ip='192.1.195.3',
                               credential=self.SWITCH_CREDENTIAL),
                        Switch(ip='192.2.192.4',
                               credential=self.SWITCH_CREDENTIAL)]
            session.add_all(switches)

        # Start to query switches
        # a. query multiple switches with ip
        # b. query switches with only switchIpNetwork
        # c. query only with limit
        # d. query swithes with switchIpNetwork and limit number
        # e. query switches with all conditions
        # f. Invliad switch ip format
        # g. Invalid switch ip network format

        test_list = [{'url': ('/switches?switchIp=192.168.1.1'
                              '&switchIp=192.168.1.2'),
                     'expected_code': 200, 'expected_count': 2},
                     {'url': '/switches?switchIpNetwork=192.1.192.0/22',
                      'expected_code': 200, 'expected_count': 3},
                     {'url': '/switches?limit=3', 'expected_code': 200,
                      'expected_count': 3},
                     {'url': '/switches?limit=-1', 'expected_code': 400},
                     {'url': ('/switches?switchIpNetwork=192.1.192.0/22'
                              '&limit=1'),
                      'expected_code': 200, 'expected_count': 1},
                     {'url': ('/switches?switchIp=192.168.1.1'
                              '&switchIpNetwork=192.1.192.0/22&limit=3'),
                      'expected_code': 400},
                     {'url': '/switches?switchIp=192.168.1.xx',
                      'expected_code': 400},
                     {'url': '/switches?switchIpNetwork=192.168.1.x',
                      'expected_code': 400}]

        for test in test_list:
            url = test['url']
            return_value = self.test_client.get(url)
            data = json.loads(return_value.get_data())
            expected_code = test['expected_code']
            self.assertEqual(return_value.status_code, expected_code)

            if 'expected_count' in test:
                expected_count = test['expected_count']
                switch_count = len(data['switches'])
                self.assertEqual(switch_count, expected_count)

    def test_post_switch_list(self):
        """test post switch list"""
        # Test SwitchList POST method
        url = '/switches'

        # a. post a new switch
        data = {'switch': {
                'ip': '10.10.10.2',
                'credential': self.SWITCH_CREDENTIAL}}

        return_value = self.test_client.post(url, data=json.dumps(data))
        self.assertEqual(return_value.status_code, 202)

        with database.session() as session:
            switch = session.query(Switch).filter_by(ip='10.10.10.2').first()
            self.assertEqual(switch.ip, '10.10.10.2')

        # b. Post Conflict switch Ip
        return_value = self.test_client.post(url, data=json.dumps(data))
        self.assertEqual(return_value.status_code, 409)
        data = json.loads(return_value.get_data())
        self.assertEqual("IP address '10.10.10.2' already exists",
                         data['message'])
        self.assertEqual(2, data['failedSwitch'])

        # c. Invalid Ip format
        data = {'switch': {
                'ip': '192.543.1.1',
                'credential': self.SWITCH_CREDENTIAL}}
        return_value = self.test_client.post(url, data=json.dumps(data))
        self.assertEqual(return_value.status_code, 400)

    def test_get_switch_by_id(self):
        """test get switch y id"""
        # Test Get /switches/{id}
        # Non-exist switch id
        url = '/switches/1000'
        return_value = self.test_client.get(url)
        self.assertEqual(return_value.status_code, 404)

        correct_url = '/switches/1'
        return_value = self.test_client.get(correct_url)
        data = json.loads(return_value.get_data())

        expected_switch_resp = self.SWITCH_RESP_TPL.copy()
        expected_switch_resp['link']['href'] = correct_url
        expected_switch_resp['id'] = 1
        expected_switch_resp['ip'] = "10.10.10.1"

        self.assertEqual(return_value.status_code, 200)
        self.assertEqual(data["status"], "OK")
        self.assertDictEqual(data["switch"], expected_switch_resp)

    def test_put_switch_by_id(self):
        """test put switch by id"""
        # Test put a switch by id
        url = '/switches/1000'
        # Put a non-existing switch
        data = {'switch': {'credential': self.SWITCH_CREDENTIAL}}
        return_value = self.test_client.put(url, data=json.dumps(data))
        self.assertEqual(return_value.status_code, 404)

        # Put sucessfully
        url = '/switches/1'
        credential = deepcopy(self.SWITCH_CREDENTIAL)
        credential['version'] = '1v'
        data = {'switch': {'credential': credential}}
        return_value = self.test_client.put(url, data=json.dumps(data))
        self.assertEqual(return_value.status_code, 202)
        self.assertEqual(
            json.loads(return_value.get_data())['switch']['state'],
            'repolling')

    def test_delete_switch(self):
        """test delete switch"""
        url = '/switches/1'
        return_value = self.test_client.delete(url)
        self.assertEqual(return_value.status_code, 405)

    def test_get_machine_by_id(self):
        """test get machine by id"""
        # Prepare testing data
        with database.session() as session:
            machine = Machine(mac='00:27:88:0c:a6', port='1', vlan='1',
                              switch_id=1)
            session.add(machine)

        # machine id exists in Machine table
        url = '/machines/1'
        return_value = self.test_client.get(url)
        self.assertEqual(return_value.status_code, 200)

        # machine id doesn't exist
        url = '/machines/1000'
        return_value = self.test_client.get(url)
        self.assertEqual(return_value.status_code, 404)

    def test_get_machine_list(self):
        """test get machine list"""
        #Prepare testing data
        with database.session() as session:
            switch_config = [
                SwitchConfig(ip='10.10.10.1', filter_port='6'),
                SwitchConfig(ip='10.10.10.1', filter_port='7')
            ]
            session.add_all(switch_config)

            machines = [Machine(mac='00:27:88:0c:01', port='1', vlan='1',
                                switch_id=1),
                        Machine(mac='00:27:88:0c:02', port='2', vlan='1',
                                switch_id=1),
                        Machine(mac='00:27:88:0c:03', port='3', vlan='1',
                                switch_id=1),
                        Machine(mac='00:27:88:01:04', port='4', vlan='1',
                                switch_id=1),
                        Machine(mac='00:27:88:01:05', port='5', vlan='1',
                                switch_id=1),
                        Machine(mac='00:27:88:01:06', port='6', vlan='1',
                                switch_id=1),
                        Machine(mac='00:27:88:01:07', port='7', vlan='1',
                                switch_id=1),
                        Machine(mac='00:27:88:01:08', port='8', vlan='1',
                                switch_id=1),
                        Machine(mac='00:27:88:01:09', port='9', vlan='1',
                                switch_id=1),
                        Machine(mac='00:27:88:01:10', port='10', vlan='1',
                                switch_id=1),
                        Machine(mac='00:27:88:0c:04', port='3', vlan='1',
                                switch_id=2),
                        Machine(mac='00:27:88:0c:05', port='4', vlan='2',
                                switch_id=2),
                        Machine(mac='00:27:88:0c:06', port='5', vlan='3',
                                switch_id=3)]
            session.add_all(machines)

        test_list = [{'url': '/machines', 'expected': 11},
                     {'url': '/machines?limit=3', 'expected': 3},
                     {'url': '/machines?limit=50', 'expected': 11},
                     {'url': '/machines?switchId=1&vladId=1&port=2',
                             'expected': 1},
                     {'url': '/machines?switchId=1&vladId=1&limit=2',
                             'expected': 2},
                     {'url': '/machines?switchId=1', 'expected': 8},
                     # TODO:
                     #{'url': '/machines?switchId=1&port=6', 'expected': 1},
                     {'url': '/machines?switchId=4', 'expected': 0},
                     {'url': "/machines?mac='00:27:88:0c:01'", 'expected': 1}]

        for test in test_list:
            url = test['url']
            expected = test['expected']
            return_value = self.test_client.get(url)
            data = json.loads(return_value.get_data())
            count = len(data['machines'])
            self.assertEqual(return_value.status_code, 200)
            self.assertEqual(count, expected)


class TestClusterAPI(ApiTestCase):
    """test cluster api"""

    SECURITY_CONFIG = {
        'server_credentials': {
            'username': 'root',
            'password': 'huawei123'},
        'service_credentials': {
            'username': 'admin',
            'password': 'huawei123'},
        'console_credentials': {
            'username': 'admin',
            'password': 'huawei123'}}

    NETWORKING_CONFIG = {
        "interfaces": {
            "management": {
                "ip_start": "192.168.1.100",
                "ip_end": "192.168.1.200",
                "netmask": "255.255.255.0",
                "gateway": "192.168.1.1",
                "nic": "eth0",
                "promisc": 1},
            "tenant": {
                "ip_start": "192.168.1.100",
                "ip_end": "192.168.1.200",
                "netmask": "255.255.255.0",
                "gateway": "",
                "nic": "eth1",
                "promisc": 0},
            "public": {
                "ip_start": "192.168.1.100",
                "ip_end": "192.168.1.200",
                "netmask": "255.255.255.0",
                "gateway": "",
                "nic": "eth3",
                "promisc": 1},
            "storage": {
                "ip_start": "192.168.1.100",
                "ip_end": "192.168.1.200",
                "netmask": "255.255.255.0",
                "gateway": "",
                "nic": "eth3",
                "promisc": 1}},
        "global": {
            "gateway": "192.168.1.1",
            "proxy": "",
            "ntp_server": "",
            "nameservers": "8.8.8.8",
            "search_path": "ods.com,ods1.com"}}

    def setUp(self):
        super(TestClusterAPI, self).setUp()
        logsetting.init()
        #Prepare testing data
        with database.session() as session:
            clusters_list = [
                Cluster(name='cluster_01'),  # undeployed
                Cluster(name="cluster_02"),  # undeployed
                Cluster(name="cluster_03", mutable=False),  # installing
                Cluster(name="cluster_04", mutable=False),  # installing
                Cluster(name="cluster_05"),  # failed
                Cluster(name="cluster_06"),  # failed
                Cluster(name="cluster_07"),  # successful
                Cluster(name="cluster_08"),  # successful
            ]
            session.add_all(clusters_list)

            cluster_states = [
                ClusterState(id=3, state='INSTALLING'),
                ClusterState(id=4, state='INSTALLING'),
                ClusterState(id=5, state='ERROR'),
                ClusterState(id=6, state='ERROR'),
                ClusterState(id=7, state='READY'),
                ClusterState(id=8, state='READY'),
            ]
            session.add_all(cluster_states)
            session.flush()

    def tearDown(self):
        super(TestClusterAPI, self).tearDown()

    def test_get_cluster_by_id(self):
        """test get cluster by id"""
        # a. Get an existing cluster
        # b. Get a non-existing cluster, return 404
        test_list = [{'url': '/clusters/1', 'expected_code': 200,
                      'expected': {'clusterName': 'cluster_01',
                                   'href': '/clusters/1'}},
                     {'url': '/clusters/1000', 'expected_code': 404}]

        for test in test_list:
            url = test['url']
            return_value = self.test_client.get(url)
            data = json.loads(return_value.get_data())
            self.assertEqual(return_value.status_code, test['expected_code'])
            if 'expected' in test:
                excepted_name = test['expected']['clusterName']
                excepted_href = test['expected']['href']
                self.assertEqual(data['cluster']['clusterName'], excepted_name)
                self.assertEqual(data['cluster']['link']['href'],
                                 excepted_href)

    # Create a cluster
    def test_post_cluster(self):
        """test post cluster"""
        # a. Post a new cluster but no adapter exists
        cluster_req = {'cluster': {'name': 'cluster_09',
                                   'adapter_id': 1}}
        url = '/clusters'
        return_value = self.test_client.post(url, data=json.dumps(cluster_req))
        data = json.loads(return_value.get_data())

        self.assertEqual(return_value.status_code, 404)

        #b. Post a cluster sucessfully
        with database.session() as session:
            adapter = Adapter(name='Centos_openstack', os='Centos',
                              target_system='openstack')
            session.add(adapter)

        return_value = self.test_client.post(url, data=json.dumps(cluster_req))
        data = json.loads(return_value.get_data())
        self.assertEqual(data['cluster']['id'], 9)
        self.assertEqual(data['cluster']['name'], 'cluster_09')

        #c. Post an existing cluster, return 409
        return_value = self.test_client.post(url, data=json.dumps(cluster_req))
        self.assertEqual(return_value.status_code, 409)
        #d. Post a new cluster without providing a name
        cluster_req['cluster']['name'] = ''
        return_value = self.test_client.post(url, data=json.dumps(cluster_req))
        data = json.loads(return_value.get_data())
        self.assertEqual(data['cluster']['id'], 10)

    def test_get_clusters(self):
        """test get clusters"""
        # a. get all clusters
        url = "/clusters"
        return_value = self.test_client.get(url)
        data = json.loads(return_value.get_data())
        self.assertEqual(len(data['clusters']), 8)

        # b. get all undeployed clusters
        url = "/clusters?state=undeployed"
        return_value = self.test_client.get(url)
        data = json.loads(return_value.get_data())
        self.assertEqual(len(data['clusters']), 2)

        # c. get all failed clusters
        url = "/clusters?state=failed"
        return_value = self.test_client.get(url)
        data = json.loads(return_value.get_data())
        self.assertEqual(len(data['clusters']), 2)

        # d. get all installing clusters
        url = "/clusters?state=installing"
        return_value = self.test_client.get(url)
        data = json.loads(return_value.get_data())
        self.assertEqual(len(data['clusters']), 2)

        # e. get all successful clusters
        url = "/clusters?state=successful"
        return_value = self.test_client.get(url)
        data = json.loads(return_value.get_data())
        self.assertEqual(len(data['clusters']), 2)

    def test_put_cluster_security_resource(self):
        """test put cluster security resource"""
        # Prepare testing data
        security = {'security': self.SECURITY_CONFIG}

        # a. Upate cluster's security config
        url = '/clusters/1/security'
        return_value = self.test_client.put(url, data=json.dumps(security))
        self.assertEqual(return_value.status_code, 200)
        with database.session() as session:
            cluster_security_config = session.query(
                Cluster.security_config).filter_by(id=1).first()[0]
            self.assertDictEqual(self.SECURITY_CONFIG,
                                 json.loads(cluster_security_config))

        # b. Update a non-existing cluster's resource
        url = '/clusters/1000/security'
        return_value = self.test_client.put(url, data=json.dumps(security))
        self.assertEqual(return_value.status_code, 404)

        # c. Update invalid cluster config item
        url = '/clusters/1/xxx'
        return_value = self.test_client.put(url, data=json.dumps(security))
        self.assertEqual(return_value.status_code, 400)

        # d. Security config is invalid -- some required field is null
        url = "/clusters/1/security"
        invalid_security = deepcopy(security)
        invalid_security['security']['server_credentials']['username'] = None
        return_value = self.test_client.put(
            url, data=json.dumps(invalid_security))
        self.assertEqual(return_value.status_code, 400)

        # e. Security config is invalid -- keyword is incorrect
        invalid_security = deepcopy(security)
        invalid_security['security']['xxxx'] = {'xxx': 'xxx'}
        return_value = self.test_client.put(
            url, data=json.dumps(invalid_security))
        self.assertEqual(return_value.status_code, 400)

        # f. Security config is invalid -- missing keyword
        invalid_security = deepcopy(security)
        del invalid_security["security"]["server_credentials"]
        return_value = self.test_client.put(
            url, data=json.dumps(invalid_security))
        self.assertEqual(return_value.status_code, 400)

        # g. Security config is invalid -- missing subkey keyword
        invalid_security = deepcopy(security)
        del invalid_security["security"]["server_credentials"]["username"]
        return_value = self.test_client.put(
            url, data=json.dumps(invalid_security))
        self.assertEqual(return_value.status_code, 400)

    def test_put_cluster_networking_resource(self):
        """test put cluster networking resource"""
        networking = {"networking": self.NETWORKING_CONFIG}
        url = "/clusters/1/networking"
        return_value = self.test_client.put(url, data=json.dumps(networking))
        self.assertEqual(return_value.status_code, 200)

        # Missing some required keyword in interfaces section
        invalid_config = deepcopy(networking)
        del invalid_config["networking"]["interfaces"]["management"]["nic"]
        return_value = self.test_client.put(
            url, data=json.dumps(invalid_config))
        self.assertEqual(return_value.status_code, 400)

        invalid_config = deepcopy(networking)
        del invalid_config["networking"]["interfaces"]["management"]
        return_value = self.test_client.put(
            url, data=json.dumps(invalid_config))
        self.assertEqual(return_value.status_code, 400)

        invalid_config = deepcopy(networking)
        invalid_config["networking"]["interfaces"]["xxx"] = {}
        return_value = self.test_client.put(
            url, data=json.dumps(invalid_config))
        self.assertEqual(return_value.status_code, 400)

        # Missing some required keyword in global section
        invalid_config = deepcopy(networking)
        del invalid_config["networking"]["global"]["gateway"]
        return_value = self.test_client.put(
            url, data=json.dumps(invalid_config))
        self.assertEqual(return_value.status_code, 400)

        # Invalid value in interfaces section
        invalid_config = deepcopy(networking)
        invalid_config["networking"]["interfaces"]["tenant"]["nic"] = "eth0"
        return_value = self.test_client.put(
            url, data=json.dumps(invalid_config))
        self.assertEqual(return_value.status_code, 400)

        # Invalid value in global section
        invalid_config = deepcopy(networking)
        invalid_config["networking"]["global"]["nameservers"] = "*.*.*.*,"
        return_value = self.test_client.put(
            url, data=json.dumps(invalid_config))
        self.assertEqual(return_value.status_code, 400)

    def test_get_cluster_resource(self):
        """test get cluster resource"""
        # Test  resource
        with database.session() as session:
            cluster = session.query(Cluster).filter_by(id=1).first()
            cluster.security = self.SECURITY_CONFIG
            cluster.networking = self.NETWORKING_CONFIG

        # a. query secuirty config by cluster id
        url = '/clusters/1/security'
        return_value = self.test_client.get(url)
        data = json.loads(return_value.get_data())
        self.assertEqual(return_value.status_code, 200)
        self.assertDictEqual(data['security'], self.SECURITY_CONFIG)

        url = '/clusters/1/networking'
        return_value = self.test_client.get(url)
        data = json.loads(return_value.get_data())
        self.assertEqual(return_value.status_code, 200)
        self.assertDictEqual(data['networking'], self.NETWORKING_CONFIG)

        # b. query a nonsupported resource, return 400
        url = '/clusters/1/xxx'
        return_value = self.test_client.get(url)
        data = json.loads(return_value.get_data())
        self.assertEqual(return_value.status_code, 400)
        excepted_err_msg = "Invalid resource name 'xxx'!"
        self.assertEqual(data['message'], excepted_err_msg)

    def test_cluster_action(self):
        """test cluster action"""
        from sqlalchemy import func
        #Prepare testing data: create machines, clusters in database
        #The first three machines will belong to cluster_01, the last one
        #belongs to cluster_10
        with database.session() as session:
            machines = [Machine(mac='00:27:88:0c:01'),
                        Machine(mac='00:27:88:0c:02'),
                        Machine(mac='00:27:88:0c:03'),
                        Machine(mac='00:27:88:0c:04'),
                        Machine(mac='00:27:88:0c:05'),
                        Machine(mac='00:27:88:0c:06'),
                        Machine(mac='00:27:88:0c:07'),
                        Machine(mac='00:27:88:0c:08')]
            clusters = [Cluster(name='cluster_10')]
            session.add_all(machines)
            session.add_all(clusters)
            # add a host to machine '00:27:88:0c:04' to cluster_02
            host = ClusterHost(cluster_id=10, machine_id=4,
                               hostname='host_c2_01')
            session.add(host)

        # Do an action to a non-existing cluster
        url = '/clusters/1000/action'
        request = {'addHosts': [10, 20, 30]}
        return_value = self.test_client.post(url, data=json.dumps(request))
        self.assertEqual(return_value.status_code, 404)

        # Test 'addHosts' action on cluster_01
        # 1. add a host with  non-existing machine
        url = '/clusters/1/action'
        request = {'addHosts': [1, 1000, 1001]}
        return_value = self.test_client.post(url, data=json.dumps(request))
        self.assertEqual(return_value.status_code, 404)
        # ClusterHost table should not have any records.
        with database.session() as session:
            hosts_num = session.query(
                func.count(ClusterHost.id)).filter_by(
                cluster_id=1).scalar()
            self.assertEqual(hosts_num, 0)

        # 2. add a host with a installed machine
        request = {'addHosts': [1, 4]}
        return_value = self.test_client.post(url, data=json.dumps(request))
        self.assertEqual(return_value.status_code, 409)
        data = json.loads(return_value.get_data())
        self.assertEqual(len(data['failedMachines']), 1)

        # 3. add hosts to cluster_01
        request = {'addHosts': [1, 2, 3]}
        return_value = self.test_client.post(url, data=json.dumps(request))
        self.assertEqual(return_value.status_code, 200)
        total_hosts = 0
        with database.session() as session:
            total_hosts = session.query(
                func.count(ClusterHost.id)).filter_by(
                cluster_id=1).scalar()
            data = json.loads(return_value.get_data())
            self.assertEqual(len(data['cluster_hosts']), total_hosts)
            self.assertEqual(total_hosts, 3)

        # 4. try to remove some hosts not existing and in different cluster
        request = {'removeHosts': [1, 2, 3, 1000, 1001]}
        return_value = self.test_client.post(url, data=json.dumps(request))
        self.assertEqual(return_value.status_code, 404)
        data = json.loads(return_value.get_data())
        self.assertEqual(len(data['failedHosts']), 3)
        with database.session() as session:
            count = session.query(
                func.count(ClusterHost.id)).filter_by(cluster_id=1).scalar()
            self.assertEqual(count, 3)

        # 5. sucessfully remove requested hosts
        request = {'removeHosts': [2, 3]}
        return_value = self.test_client.post(url, data=json.dumps(request))
        self.assertEqual(return_value.status_code, 200)
        data = json.loads(return_value.get_data())
        self.assertEqual(len(data['cluster_hosts']), 2)
        with database.session() as session:
            count = session.query(
                func.count(ClusterHost.id)).filter_by(cluster_id=1).scalar()
            self.assertEqual(count, 1)

        # 6. Test 'replaceAllHosts' action on cluster_01
        request = {'replaceAllHosts': [5, 6, 7]}
        return_value = self.test_client.post(url, data=json.dumps(request))
        self.assertEqual(return_value.status_code, 200)
        data = json.loads(return_value.get_data())
        self.assertEqual(len(data['cluster_hosts']), 3)
        with database.session() as session:
            count = session.query(
                func.count(ClusterHost.id)).filter_by(cluster_id=1).scalar()
            self.assertEqual(count, 3)

        # 7. Test 'deploy' action on cluster_01
        request = {'deploy': []}
        return_value = self.test_client.post(url, data=json.dumps(request))
        self.assertEqual(return_value.status_code, 202)

        # 8. Test deploy cluster_01 the second time
        return_value = self.test_client.post(url, data=json.dumps(request))
        self.assertEqual(return_value.status_code, 400)

        # 9. Try to deploy cluster_02 which no host in
        url = '/clusters/2/action'
        with database.session() as session:
            session.query(
                ClusterHost).filter_by(cluster_id=2).delete(
                synchronize_session=False)
            host = session.query(
                ClusterHost).filter_by(cluster_id=2).first()

        return_value = self.test_client.post(url, data=json.dumps(request))
        self.assertEqual(return_value.status_code, 404)

        # 10. Try to add a new host to cluster_01 and deploy it
        with database.session() as session:
            cluster = session.query(Cluster).filter_by(id=1).first()
            cluster.mutable = True

            hosts = session.query(ClusterHost).filter_by(cluster_id=1).all()
            for host in hosts:
                host.mutable = True
        url = '/clusters/1/action'
        # add another machine as a new host into cluster_01
        request = json.dumps({"addHosts": [8]})
        return_value = self.test_client.post(url, data=request)
        host_id = json.loads(return_value.get_data())["cluster_hosts"][0]["id"]

        deploy_request = json.dumps({"deploy": [host_id]})
        return_value = self.app.post(url, data=deploy_request)
        self.assertEqual(202, return_value.status_code)

        cluster_state = session.query(ClusterState).filter_by(id=1).first()
        self.assertIsNone(cluster_state)

        expected_deploy_result = {
            "cluster": {
                "cluster_id": 1,
                "url": "/clusters/1/progress"
            },
            "hosts": [
                {"host_id": 5,
                 "url": "/cluster_hosts/5/progress"}
            ]
        }
        data = json.loads(return_value.get_data())["deployment"]
        self.assertDictEqual(expected_deploy_result, data)


class ClusterHostAPITest(ApiTestCase):
    """test cluster host api"""

    def setUp(self):
        super(ClusterHostAPITest, self).setUp()
        self.test_config_data = {
            "networking": {
                "interfaces": {
                    "management": {
                        "ip": "192.168.1.1"},
                    "tenant": {
                        "ip": "10.12.1.1"}
                },
                "global": {}},
            "roles": []}
        # Insert a host into database for testing
        with database.session() as session:
            clusters_list = [Cluster(name='cluster_01'),
                             Cluster(name='cluster_02')]
            session.add_all(clusters_list)

            switch = Switch(ip='192.168.1.1')
            session.add(switch)

            machines_list = [Machine(mac='00:27:88:0c:01', switch_id=1),
                             Machine(mac='00:27:88:0c:02', switch_id=1),
                             Machine(mac='00:27:88:0c:03', switch_id=1),
                             Machine(mac='00:27:88:0c:04', switch_id=1)]
            session.add_all(machines_list)

            host = ClusterHost(hostname='host_01', cluster_id=1, machine_id=1)
            host.config_data = json.dumps(self.test_config_data)
            session.add(host)

            hosts_list = [
                ClusterHost(hostname='host_02', cluster_id=1, machine_id=2),
                ClusterHost(hostname='host_03', cluster_id=1, machine_id=3),
                ClusterHost(hostname='host_04', cluster_id=2, machine_id=4)
            ]
            session.add_all(hosts_list)

    def tearDown(self):
        super(ClusterHostAPITest, self).tearDown()

    def test_clusterhost_get_config(self):
        """test get cluster host config"""
        # 1. Try to get a config of the cluster host which does not exist
        url = '/clusterhosts/1000/config'
        return_value = self.test_client.get(url)
        self.assertEqual(404, return_value.status_code)

        # 2. Get a config of a cluster host sucessfully
        test_config_data = deepcopy(self.test_config_data)
        test_config_data['hostname'] = 'host_01'

        url = '/clusterhosts/1/config'
        return_value = self.test_client.get(url)
        self.assertEqual(200, return_value.status_code)
        config = json.loads(return_value.get_data())['config']
        expected_config = deepcopy(test_config_data)
        expected_config['hostid'] = 1
        expected_config['hostname'] = 'host_01'
        expected_config['clusterid'] = 1
        expected_config['clustername'] = 'cluster_01'
        expected_config[
            'networking']['interfaces'][
            'management']['mac'] = "00:27:88:0c:01"
        expected_config['switch_port'] = ''
        expected_config['switch_ip'] = '192.168.1.1'
        expected_config['vlan'] = 0
        self.assertDictEqual(config, expected_config)

    def test_clusterhost_put_config(self):
        """test put clusterhost config"""
        config = deepcopy(self.test_config_data)
        config['roles'] = ['base']
        config[
            'networking']['interfaces'][
            'management']['ip'] = '192.168.1.2'
        config[
            'networking']['interfaces'][
            'tenant']['ip'] = '10.12.1.2'

        # 1. Try to put a config of the cluster host which does not exist
        url = '/clusterhosts/1000/config'
        return_value = self.test_client.put(url, data=json.dumps(config))
        self.assertEqual(404, return_value.status_code)

        # 2. Config with incorrect ip format
        url = '/clusterhosts/2/config'
        incorrect_conf = deepcopy(config)
        incorrect_conf['hostname'] = 'host_02'
        incorrect_conf[
            'networking']['interfaces']['management']['ip'] = 'xxx'
        return_vlaue = self.app.put(
            url, data=json.dumps(incorrect_conf))
        self.assertEqual(400, return_vlaue.status_code)

        # 3. Config put sucessfully
        config['hostname'] = 'host_02'
        return_value = self.app.put(url, data=json.dumps(config))
        self.assertEqual(200, return_value.status_code)
        with database.session() as session:
            host = session.query(ClusterHost).filter_by(id=2).first()
            config_db = json.loads(host.config_data)
            config_db['hostname'] = host.hostname
            self.maxDiff = None
            self.assertDictEqual(config, config_db)

    def test_clusterhost_delete_subkey(self):
        """test delete cluster host subkey"""
        # 1. Try to delete an unqalified subkey of config
        url = '/clusterhosts/1/config/gateway'
        return_value = self.test_client.delete(url)
        self.assertEqual(400, return_value.status_code)

        # 2. Try to delete a subkey sucessfully
        url = 'clusterhosts/1/config/roles'
        return_value = self.test_client.delete(url)
        self.assertEqual(200, return_value.status_code)
        expected_config = deepcopy(self.test_config_data)
        with database.session() as session:
            config_db = session.query(
                ClusterHost.config_data).filter_by(id=1).first()[0]
            self.assertDictEqual(expected_config, json.loads(config_db))

        # 3. Try to delete a subkey of a config belonged to an immtable host
        with database.session() as session:
            session.query(
                ClusterHost).filter_by(id=1).update({'mutable': False})

        url = 'clusterhosts/1/config/roles'
        return_value = self.test_client.delete(url)
        self.assertEqual(400, return_value.status_code)

    def test_clusterhost_get_by_id(self):
        """test get cluster host by id"""
        # 1. Get host sucessfully
        url = '/clusterhosts/1'
        return_value = self.test_client.get(url)
        self.assertEqual(200, return_value.status_code)
        hostname = json.loads(return_value.get_data())[
            'cluster_host']['hostname']
        self.assertEqual('host_01', hostname)

        # 2. Get a non-existing host
        url = '/clusterhosts/1000'
        return_value = self.test_client.get(url)
        self.assertEqual(404, return_value.status_code)

    def test_list_clusterhosts(self):
        """test list cluster hosts"""
        # 1. list the cluster host whose hostname is host_01
        url = '/clusterhosts?hostname=host_02'
        return_value = self.test_client.get(url)
        self.assertEqual(200, return_value.status_code)
        hostname = json.loads(return_value.get_data())[
            'cluster_hosts'][0]['hostname']
        self.assertEqual('host_02', hostname)

        # 2. list cluster hosts whose cluster name is cluster_01
        url = '/clusterhosts?clustername=cluster_01'
        return_value = self.test_client.get(url)
        self.assertEqual(200, return_value.status_code)
        hosts_num = len(json.loads(return_value.get_data())['cluster_hosts'])
        self.assertEqual(3, hosts_num)

        # 3. list the host whose name is host_03 and cluser name is cluster_01
        url = '/clusterhosts?hostname=host_03&clustername=cluster_01'
        return_value = self.test_client.get(url)
        self.assertEqual(200, return_value.status_code)
        hostname = json.loads(return_value.get_data())[
            'cluster_hosts'][0]['hostname']
        self.assertEqual('host_03', hostname)

        # 4. list all hosts
        url = '/clusterhosts'
        return_value = self.test_client.get(url)
        self.assertEqual(200, return_value.status_code)
        hosts_num = len(json.loads(return_value.get_data())['cluster_hosts'])
        self.assertEqual(4, hosts_num)

        # 5. Cannot found any hosts in clust name: cluster_1000
        url = '/clusterhosts?clustername=cluster_1000'
        return_value = self.test_client.get(url)
        self.assertEqual(200, return_value.status_code)
        hosts_result = json.loads(return_value.get_data())['cluster_hosts']
        self.assertListEqual([], hosts_result)

    def test_host_installing_progress(self):
        """test get host installing progress"""
        # 1. Get progress of a non-existing host
        url = '/clusterhosts/1000/progress'
        return_value = self.test_client.get(url)
        self.assertEqual(404, return_value.status_code)

        # 2. Get progress of a host without state
        url = '/clusterhosts/1/progress'
        return_value = self.test_client.get(url)
        self.assertEqual(200, return_value.status_code)

        # 3. Get progress which is in UNINITIALIZED state
        with database.session() as session:
            host = session.query(ClusterHost).filter_by(id=1).first()
            host.state = HostState()

        return_value = self.test_client.get(url)
        self.assertEqual(200, return_value.status_code)
        data = json.loads(return_value.get_data())
        self.assertEqual('UNINITIALIZED', data['progress']['state'])
        self.assertEqual(0, data['progress']['percentage'])

        # 4. Get progress which is in INSTALLING state
        with database.session() as session:
            host = session.query(ClusterHost).filter_by(id=1).first()
            host.state.state = 'INSTALLING'
            session.query(
                HostState).filter_by(id=1).update(
                {'progress': 0.3,
                 'message': 'Configuring...',
                 'severity': 'INFO'})

        return_value = self.test_client.get(url)
        self.assertEqual(200, return_value.status_code)
        data = json.loads(return_value.get_data())
        self.assertEqual('INSTALLING', data['progress']['state'])
        self.assertEqual(0.3, data['progress']['percentage'])


class TestAdapterAPI(ApiTestCase):
    """test adapter api"""

    def setUp(self):
        super(TestAdapterAPI, self).setUp()
        with database.session() as session:
            adapters = [Adapter(name='Centos_openstack', os='Centos',
                                target_system='openstack'),
                        Adapter(name='Ubuntu_openstack', os='Ubuntu',
                                target_system='openstack')]
            session.add_all(adapters)

            roles = [Role(name='Control', target_system='openstack'),
                     Role(name='Compute', target_system='openstack'),
                     Role(name='Master', target_system='hadoop')]
            session.add_all(roles)

    def tearDown(self):
        super(TestAdapterAPI, self).tearDown()

    def test_list_adapter_by_id(self):
        """test list adapter by id"""
        url = '/adapters/1'
        return_value = self.test_client.get(url)
        self.assertEqual(200, return_value.status_code)
        data = json.loads(return_value.get_data())
        self.assertEqual('Centos_openstack', data['adapter']['name'])

    def test_list_adapter_roles(self):
        """test list adapter roles"""
        url = '/adapters/1/roles'
        return_value = self.test_client.get(url)
        self.assertEqual(200, return_value.status_code)
        data = json.loads(return_value.get_data())
        self.assertEqual(2, len(data['roles']))

    def test_list_adapters(self):
        """test list adapters"""
        url = '/adapters?name=Centos_openstack'
        return_value = self.test_client.get(url)
        data = json.loads(return_value.get_data())
        self.assertEqual(200, return_value.status_code)
        execpted_result = {"name": "Centos_openstack",
                           "os": "Centos",
                           "target_system": "openstack",
                           "id": 1,
                           "link": {
                               "href": "/adapters/1",
                               "rel": "self"}
                           }
        self.assertDictEqual(execpted_result, data['adapters'][0])

        url = '/adapters'
        return_value = self.test_client.get(url)
        data = json.loads(return_value.get_data())
        self.assertEqual(200, return_value.status_code)
        self.assertEqual(2, len(data['adapters']))


class TestAPIWorkFlow(ApiTestCase):
    """test api workflow"""

    CLUSTER_SECURITY_CONFIG = {
        "security": {
            "server_credentials": {
                "username": "admin",
                "password": "admin"},
            "service_credentials": {
                "username": "admin",
                "password": "admin"},
            "console_credentials": {
                "username": "admin",
                "password": "admin"}
        }
    }

    CLUSTER_NETWORKING_CONFIG = {
        "networking": {
            "interfaces": {
                "management": {
                    "ip_start": "10.120.8.100",
                    "ip_end": "10.120.8.200",
                    "netmask": "255.255.255.0",
                    "gateway": "",
                    "nic": "eth0",
                    "promisc": 1
                },
                "tenant": {
                    "ip_start": "192.168.10.100",
                    "ip_end": "192.168.10.200",
                    "netmask": "255.255.255.0",
                    "gateway": "",
                    "nic": "eth1",
                    "promisc": 0
                },
                "public": {
                    "ip_start": "12.145.68.100",
                    "ip_end": "12.145.68.200",
                    "netmask": "255.255.255.0",
                    "gateway": "",
                    "nic": "eth2",
                    "promisc": 0
                },
                "storage": {
                    "ip_start": "172.29.8.100",
                    "ip_end": "172.29.8.200",
                    "netmask": "255.255.255.0",
                    "gateway": "",
                    "nic": "eth3",
                    "promisc": 0
                }
            },
            "global": {
                "nameservers": "8.8.8.8",
                "search_path": "ods.com",
                "gateway": "192.168.1.1",
                "proxy": "http://127.0.0.1:3128",
                "ntp_server": "127.0.0.1"
            }
        }
    }

    CLUSTER_PARTITION_CONFIG = {
        "partition": "/home 20%;"
    }

    CLUSTERHOST_CONFIG = {
        "hostname": "",
        "networking": {
            "interfaces": {
                "management": {
                    "ip": ""
                },
                "tenant": {
                    "ip": ""
                }
            }
        },
        "roles": ["base"]
    }

    def setUp(self):
        super(TestAPIWorkFlow, self).setUp()

        #Prepare test data
        with database.session() as session:
            # Populate switch info to DB
            switch = Switch(ip="192.168.2.1",
                            credential={"version": "2c",
                                        "community": "public"},
                            vendor="huawei",
                            state="under_monitoring")
            session.add(switch)

            # Populate machines info to DB
            machines = [
                Machine(mac='00:27:88:0c:a6', port='1', vlan='1', switch_id=1),
                Machine(mac='00:27:88:0c:a7', port='2', vlan='1', switch_id=1),
                Machine(mac='00:27:88:0c:a8', port='3', vlan='1', switch_id=1),
            ]

            session.add_all(machines)

            adapter = Adapter(name='Centos_openstack', os='Centos',
                              target_system='openstack')
            session.add(adapter)

    def tearDown(self):
        super(TestAPIWorkFlow, self).tearDown()

    def test_work_flow(self):
        """test api workflow"""
        # Polling switch: mock post switch
        # url = '/switches'
        # data = {"ip": "192.168.2.1",
        #         "credential": {"version": "2c", "community": "public"}}
        # self.test_client.post(url, json.dumps(data))

        # Get machines once polling switch done. If switch state changed to
        # "under_monitoring" state.
        url = '/switches/1'
        switch_state = "initialized"
        while switch_state != "under_monitoring":
            return_value = self.test_client.get(url)
            switch_state = json.loads(return_value.get_data())[
                'switch']['state']

        url = '/machines?switchId=1'
        return_value = self.test_client.get(url)
        self.assertEqual(200, return_value.status_code)
        machines = json.loads(return_value.get_data())['machines']

        # Create a Cluster and get cluster id from response
        # In this example, adapter_id will be 1 by default.
        url = '/clusters'
        data = {
            "cluster": {
                "name": "cluster_01",
                "adapter_id": 1
            }
        }
        return_value = self.test_client.post(url, data=json.dumps(data))
        self.assertEqual(200, return_value.status_code)
        cluster_id = json.loads(return_value.get_data())['cluster']['id']

        # Add machines as hosts of the cluster
        url = '/clusters/%s/action' % cluster_id
        machines_id = []
        for machine in machines:
            machines_id.append(machine["id"])

        data = {"addHosts": machines_id}
        return_value = self.test_client.post(url, data=json.dumps(data))
        self.assertEqual(200, return_value.status_code)
        hosts_info = json.loads(return_value.get_data())["cluster_hosts"]

        # Update cluster security configuration
        url = '/clusters/%s/security' % cluster_id
        security_config = json.dumps(self.CLUSTER_SECURITY_CONFIG)
        return_value = self.test_client.put(url, data=security_config)
        self.assertEqual(200, return_value.status_code)

        # Update cluster networking configuration
        url = '/clusters/%s/networking' % cluster_id
        networking_config = json.dumps(self.CLUSTER_NETWORKING_CONFIG)
        return_value = self.test_client.put(url, data=networking_config)
        self.assertEqual(200, return_value.status_code)

        # Update cluster partition configuration
        url = '/clusters/%s/partition' % cluster_id
        partition_config = json.dumps(self.CLUSTER_PARTITION_CONFIG)
        return_value = self.test_client.put(url, data=partition_config)
        self.assertEqual(200, return_value.status_code)

        # Put cluster host config individually
        hosts_configs = [
            deepcopy(self.CLUSTERHOST_CONFIG),
            deepcopy(self.CLUSTERHOST_CONFIG),
            deepcopy(self.CLUSTERHOST_CONFIG)
        ]
        names = ["host_01", "host_02", "host_03"]
        mgmt_ips = ["10.120.8.100", "10.120.8.101", "10.120.8.102"]
        tenant_ips = ["12.120.8.100", "12.120.8.101", "12.120.8.102"]
        for config, name, mgmt_ip, tenant_ip in zip(hosts_configs, names,
                                                    mgmt_ips, tenant_ips):
            config["hostname"] = name
            config["networking"]["interfaces"]["management"]["ip"] = mgmt_ip
            config["networking"]["interfaces"]["tenant"]["ip"] = tenant_ip

        for config, host_info in zip(hosts_configs, hosts_info):
            host_id = host_info["id"]
            url = 'clusterhosts/%d/config' % host_id
            return_value = self.test_client.put(url, data=json.dumps(config))
            self.assertEqual(200, return_value.status_code)

        # deploy the Cluster
        url = "/clusters/%d/action" % cluster_id
        data = json.dumps({"deploy": []})
        return_value = self.test_client.post(url, data=data)
        self.assertEqual(202, return_value.status_code)

        # Verify the final cluster configuration
        expected_cluster_config = {}
        expected_cluster_config.update(self.CLUSTER_SECURITY_CONFIG)
        expected_cluster_config.update(self.CLUSTER_NETWORKING_CONFIG)
        expected_cluster_config.update(self.CLUSTER_PARTITION_CONFIG)
        expected_cluster_config["clusterid"] = cluster_id
        expected_cluster_config["clustername"] = "cluster_01"

        with database.session() as session:
            cluster = session.query(Cluster).filter_by(id=cluster_id).first()
            config = cluster.config
            self.assertDictEqual(config, expected_cluster_config)

            # Verify each host configuration
            for host_info, excepted in zip(hosts_info, hosts_configs):
                machine_id = host_info["machine_id"]
                machine = session.query(
                    Machine).filter_by(id=machine_id).first()
                mac = machine.mac
                excepted["clusterid"] = cluster_id
                excepted["clustername"] = "cluster_01"
                excepted["hostid"] = host_info["id"]
                excepted["networking"]["interfaces"]["management"]["mac"] = mac
                excepted['switch_port'] = machine.port
                excepted['vlan'] = machine.vlan
                switch = machine.switch
                excepted['switch_ip'] = switch.ip
                host = session.query(
                    ClusterHost).filter_by(id=host_info["id"]).first()
                self.maxDiff = None
                self.assertDictEqual(host.config, excepted)


class TestExport(ApiTestCase):

    CLUSTER_SECURITY_CONFIG = {
        "security": {
            "server_credentials": {
                "username": "root",
                "password": "root"},
            "service_credentials": {
                "username": "service",
                "password": "admin"},
            "console_credentials": {
                "username": "console",
                "password": "admin"}
        }
    }
    CLUSTER_NETWORKING_CONFIG = {
        "networking": {
            "interfaces": {
                "management": {
                    "ip_start": "10.120.8.100",
                    "ip_end": "10.120.8.200",
                    "netmask": "255.255.255.0",
                    "gateway": "",
                    "nic": "eth0",
                    "promisc": 1
                },
                "tenant": {
                    "ip_start": "192.168.10.100",
                    "ip_end": "192.168.10.200",
                    "netmask": "255.255.255.0",
                    "gateway": "",
                    "nic": "eth1",
                    "promisc": 0
                },
                "public": {
                    "ip_start": "12.145.68.100",
                    "ip_end": "12.145.68.200",
                    "netmask": "255.255.255.0",
                    "gateway": "",
                    "nic": "eth2",
                    "promisc": 0
                },
                "storage": {
                    "ip_start": "172.29.8.100",
                    "ip_end": "172.29.8.200",
                    "netmask": "255.255.255.0",
                    "gateway": "",
                    "nic": "eth3",
                    "promisc": 0
                }
            },
            "global": {
                "nameservers": "8.8.8.8",
                "search_path": "ods.com",
                "gateway": "192.168.1.1",
                "proxy": "http://127.0.0.1:3128",
                "ntp_server": "127.0.0.1"
            }
        }
    }
    CLUSTER_PARTITION_CONFIG = {
        "partition": "/home 20%;/tmp 10%;/var 30%;"
    }

    CLUSTERHOST_CONFIG = {
        "networking": {
            "interfaces": {
                "management": {
                    "ip": ""
                },
                "tenant": {
                    "ip": ""
                }
            }
        },
        "roles": ["base"]
    }
    CSV_EXCEPTED_OUTPUT_DIR = '/'.join((
        os.path.dirname(os.path.realpath(__file__)), 'expected_csv'))

    def setUp(self):
        super(TestExport, self).setUp()
        #Prepare test data
        with database.session() as session:
            # populate switch_config
            switch_config = [SwitchConfig(ip='192.168.1.10', filter_port='1'),
                             SwitchConfig(ip='192.168.1.11', filter_port='2')]
            session.add_all(switch_config)

            # populate role table
            role = Role(name='compute', target_system='openstack')
            session.add(role)

            # Populate one adapter to DB
            adapter = Adapter(name='Centos_openstack', os='Centos',
                              target_system='openstack')
            session.add(adapter)

            #Populate switches info to DB
            switches = [Switch(ip="192.168.2.1",
                               credential={"version": "2c",
                                           "community": "public"},
                               vendor="huawei",
                               state="under_monitoring"),
                        Switch(ip="192.168.2.2",
                               credential={"version": "2c",
                                           "community": "public"},
                               vendor="huawei",
                               state="under_monitoring"),
                        Switch(ip="192.168.2.3",
                               credential={"version": "2c",
                                           "community": "public"},
                               vendor="huawei",
                               state="under_monitoring"),
                        Switch(ip="192.168.2.4",
                               credential={"version": "2c",
                                           "community": "public"},
                               vendor="huawei",
                               state="under_monitoring")]
            session.add_all(switches)

            # Populate machines info to DB
            machines = [
                Machine(mac='00:0c:27:88:0c:a1', port='1', vlan='1',
                        switch_id=1),
                Machine(mac='00:0c:27:88:0c:a2', port='2', vlan='1',
                        switch_id=1),
                Machine(mac='00:0c:27:88:0c:a3', port='3', vlan='1',
                        switch_id=1),
                Machine(mac='00:0c:27:88:0c:b1', port='1', vlan='1',
                        switch_id=2),
                Machine(mac='00:0c:27:88:0c:b2', port='2', vlan='1',
                        switch_id=2),
                Machine(mac='00:0c:27:88:0c:b3', port='3', vlan='1',
                        switch_id=2),
                Machine(mac='00:0c:27:88:0c:c1', port='1', vlan='1',
                        switch_id=3),
                Machine(mac='00:0c:27:88:0c:c2', port='2', vlan='1',
                        switch_id=3),
                Machine(mac='00:0c:27:88:0c:c3', port='3', vlan='1',
                        switch_id=3),
                Machine(mac='00:0c:27:88:0c:d1', port='1', vlan='1',
                        switch_id=4),
                Machine(mac='00:0c:27:88:0c:d2', port='2', vlan='1',
                        switch_id=4),
            ]

            session.add_all(machines)

            # Popluate clusters into DB
            """
            a. cluster #1: a new machine will be added to it.
            b. cluster #2: a failed machine needs to be re-deployed.
            c. cluster #3: a new cluster with 3 hosts will be deployed.
            """
            clusters_networking_config = [
                {"networking":
                    {"interfaces": {"management": {"ip_start": "10.120.1.100",
                                                   "ip_end": "10.120.1.200"},
                                    "tenant": {"ip_start": "192.168.1.100",
                                               "ip_end": "192.168.1.200"},
                                    "public": {"ip_start": "12.145.1.100",
                                               "ip_end": "12.145.1.200"},
                                    "storage": {"ip_start": "172.29.1.100",
                                                "ip_end": "172.29.1.200"}}}},
                {"networking":
                    {"interfaces": {"management": {"ip_start": "10.120.2.100",
                                                   "ip_end": "10.120.2.200"},
                                    "tenant": {"ip_start": "192.168.2.100",
                                               "ip_end": "192.168.2.200"},
                                    "public": {"ip_start": "12.145.2.100",
                                               "ip_end": "12.145.2.200"},
                                    "storage": {"ip_start": "172.29.2.100",
                                                "ip_end": "172.29.2.200"}}}}
            ]
            cluster_names = ['cluster_01', 'cluster_02']
            for name, networking_config in zip(cluster_names,
                                               clusters_networking_config):
                nconfig = deepcopy(self.CLUSTER_NETWORKING_CONFIG)
                util.merge_dict(nconfig, networking_config)
                c = Cluster(name=name, adapter_id=1,
                            security_config=json.dumps(
                                self.CLUSTER_SECURITY_CONFIG['security']),
                            networking_config=json.dumps(
                                nconfig['networking']),
                            partition_config=json.dumps(
                                self.CLUSTER_PARTITION_CONFIG['partition']))
                session.add(c)

            # Populate hosts to each cluster
            host_mips = ['10.120.1.100', '10.120.1.101', '10.120.1.102',
                         '10.120.2.100', '10.120.2.101', '10.120.2.102']
            host_tips = ['192.168.1.100', '192.168.1.101', '192.168.1.102',
                         '192.168.2.100', '192.168.2.101', '192.168.2.102']
            hosts_config = []
            for mip, tip in zip(host_mips, host_tips):
                config = deepcopy(self.CLUSTERHOST_CONFIG)
                config['networking']['interfaces']['management']['ip'] = mip
                config['networking']['interfaces']['tenant']['ip'] = tip
                hosts_config.append(json.dumps(config))

            hosts = [
                ClusterHost(hostname='host_01', machine_id=1, cluster_id=1,
                            config_data=hosts_config[0]),
                ClusterHost(hostname='host_02', machine_id=2, cluster_id=1,
                            config_data=hosts_config[1]),
                ClusterHost(hostname='host_03', machine_id=3, cluster_id=1,
                            config_data=hosts_config[2]),
                ClusterHost(hostname='host_01', machine_id=4, cluster_id=2,
                            config_data=hosts_config[3]),
                ClusterHost(hostname='host_02', machine_id=5, cluster_id=2,
                            config_data=hosts_config[4]),
                ClusterHost(hostname='host_03', machine_id=6, cluster_id=2,
                            config_data=hosts_config[5])
            ]
            session.add_all(hosts)

            # Populate cluster state and host state
            cluster_states = [
                ClusterState(id=1, state="READY", progress=1.0,
                             message="Successfully!"),
                ClusterState(id=2, state="ERROR", progress=0.5,
                             message="Failed!")
            ]
            session.add_all(cluster_states)

            host_states = [
                HostState(id=1, state="READY", progress=1.0,
                          message="Successfully!"),
                HostState(id=2, state="READY", progress=1.0,
                          message="Successfully!"),
                HostState(id=3, state="READY", progress=1.0,
                          message="Successfully!"),
                HostState(id=4, state="ERROR", progress=0.5,
                          message="Failed!"),
                HostState(id=5, state="READY", progress=1.0,
                          message="Successfully!"),
                HostState(id=6, state="ERROR", progress=1.0,
                          message="Failed!")
            ]
            session.add_all(host_states)
            session.flush()

    def tearDown(self):
        super(TestExport, self).tearDown()

    def test_export(self):
        talbes = ['switch', 'machine', 'cluster', 'cluster_host', 'adapter',
                  'role', 'switch_config']
        for tname in talbes:
            url = '/'.join(('/export', tname))
            rv = self.app.get(url)
            resp_data = rv.get_data()
            resp_data = resp_data.split('\n')
            resp_data = csv.DictReader(resp_data)
            expected_file = '/'.join((self.CSV_EXCEPTED_OUTPUT_DIR,
                                     (tname + '.csv')))
            expected_data = csv.DictReader(open(expected_file))
            for export_row, expected_row in zip(resp_data, expected_data):
                self.assertDictEqual(export_row, expected_row)
                self.maxDiff = None


if __name__ == '__main__':
    flags.init()
    flags.OPTIONS.logfile = '/var/log/compass/test.log'
    logsetting.init()
    unittest2.main()
