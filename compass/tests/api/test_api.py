import logging
import simplejson as json
from copy import deepcopy
from celery import current_app

from mock import Mock
import unittest2

from compass.api import app
from compass.db import database
from compass.db.model import Switch
from compass.db.model import Machine
from compass.db.model import Cluster
from compass.db.model import ClusterHost
from compass.db.model import HostState
from compass.db.model import Adapter
from compass.db.model import Role


class ApiTestCase(unittest2.TestCase):

    CLUSTER_NAME = "Test1"
    SWITCH_IP_ADDRESS1 = '10.10.10.1'
    SWITCH_CREDENTIAL = {'version': 'xxx',
                         'community': 'xxx'}
    DATABASE_URL = 'sqlite://'

    def setUp(self):
        super(ApiTestCase, self).setUp()
        database.init(self.DATABASE_URL)
        database.create_db()
        self.app = app.test_client()

        # We do not want to send a real task as our test environment
        # does not have a AMQP system set up. TODO(): any better way?
        current_app.send_task = Mock()

        # We do not want to send a real task as our test environment
        # does not have a AMQP system set up. TODO(): any better way?
        current_app.send_task = Mock()

    def tearDown(self):
        database.drop_db()
        super(ApiTestCase, self).tearDown()


class TestSwtichMachineAPI(ApiTestCase):

    SWITCH_RESP_TPL = {"state": "not_reached",
                       "ip": "",
                       "link": {"href": "",
                                "rel": "self"},
                       "id": ""}

    def setUp(self):
        super(TestSwtichMachineAPI, self).setUp()
        # Create one switch in database
        with database.session() as session:
            test_switch = Switch(ip=self.SWITCH_IP_ADDRESS1)
            test_switch.credential = self.SWITCH_CREDENTIAL
            session.add(test_switch)

    def tearDown(self):
        super(TestSwtichMachineAPI, self).tearDown()

    def test_get_switchList(self):
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

        testList = [{'url': ('/switches?switchIp=192.168.1.1'
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

        for test in testList:
            url = test['url']
            rv = self.app.get(url)
            data = json.loads(rv.get_data())
            expected_code = test['expected_code']
            self.assertEqual(rv.status_code, expected_code)

            if 'expected_count' in test:
                expected_count = test['expected_count']
                switch_count = len(data['switches'])
                self.assertEqual(switch_count, expected_count)

    def test_post_switchList(self):
        # Test SwitchList POST method
        url = '/switches'

        # a. post a new switch
        data = {'switch': {
                'ip': '10.10.10.2',
                'credential': self.SWITCH_CREDENTIAL}}

        rv = self.app.post(url, data=json.dumps(data))
        self.assertEqual(rv.status_code, 202)

        with database.session() as session:
            switch = session.query(Switch).filter_by(ip='10.10.10.2').first()
            self.assertEqual(switch.ip, '10.10.10.2')

        # b. Post Conflict switch Ip
        rv = self.app.post(url, data=json.dumps(data))
        self.assertEqual(rv.status_code, 409)
        data = json.loads(rv.get_data())
        self.assertEqual("IP address '10.10.10.2' already exists",
                         data['message'])
        self.assertEqual(2, data['failedSwitch'])

        # c. Invalid Ip format
        data = {'switch': {
                'ip': '192.543.1.1',
                'credential': self.SWITCH_CREDENTIAL}}
        rv = self.app.post(url, data=json.dumps(data))
        self.assertEqual(rv.status_code, 400)

    def test_get_switch_by_id(self):
        # Test Get /switches/{id}
        # Non-exist switch id
        url = '/switches/1000'
        rv = self.app.get(url)
        logging.info('[test_get_switch_by_id] url %s', url)
        self.assertEqual(rv.status_code, 404)

        correct_url = '/switches/1'
        rv = self.app.get(correct_url)
        data = json.loads(rv.get_data())

        expected_switch_resp = self.SWITCH_RESP_TPL.copy()
        expected_switch_resp['link']['href'] = correct_url
        expected_switch_resp['id'] = 1
        expected_switch_resp['ip'] = "10.10.10.1"

        self.assertEqual(rv.status_code, 200)
        self.assertEqual(data["status"], "OK")
        self.assertDictEqual(data["switch"], expected_switch_resp)

    def test_put_switch_by_id(self):
        # Test put a switch by id
        url = '/switches/1000'
        # Put a non-existing switch
        data = {'switch': {'credential': self.SWITCH_CREDENTIAL}}
        rv = self.app.put(url, data=json.dumps(data))
        self.assertEqual(rv.status_code, 404)

        # Put sucessfully
        url = '/switches/1'
        credential = deepcopy(self.SWITCH_CREDENTIAL)
        credential['version'] = '1v'
        data = {'switch': {'credential': credential}}
        rv = self.app.put(url, data=json.dumps(data))
        self.assertEqual(rv.status_code, 202)

    def test_delete_switch(self):
        url = '/switches/1'
        rv = self.app.delete(url)
        self.assertEqual(rv.status_code, 405)

    def test_get_machine_by_id(self):
        # Test get a machine by id
        # Prepare testing data
        with database.session() as session:
            machine = Machine(mac='00:27:88:0c:a6', port='1', vlan='1',
                              switch_id=1)
            session.add(machine)

        # machine id exists in Machine table
        url = '/machines/1'
        rv = self.app.get(url)
        self.assertEqual(rv.status_code, 200)

        # machine id doesn't exist
        url = '/machines/1000'
        rv = self.app.get(url)
        self.assertEqual(rv.status_code, 404)

    def test_get_machineList(self):
        #Prepare testing data
        with database.session() as session:
            machines = [Machine(mac='00:27:88:0c:01', port='1', vlan='1',
                                switch_id=1),
                        Machine(mac='00:27:88:0c:02', port='2', vlan='1',
                                switch_id=1),
                        Machine(mac='00:27:88:0c:03', port='3', vlan='1',
                                switch_id=1),
                        Machine(mac='00:27:88:0c:04', port='3', vlan='1',
                                switch_id=2),
                        Machine(mac='00:27:88:0c:05', port='4', vlan='2',
                                switch_id=2),
                        Machine(mac='00:27:88:0c:06', port='5', vlan='3',
                                switch_id=3)]
            session.add_all(machines)

        testList = [{'url': '/machines', 'expected': 6},
                    {'url': '/machines?limit=3', 'expected': 3},
                    {'url': '/machines?limit=50', 'expected': 6},
                    {'url': '/machines?switchId=1&vladId=1&port=2',
                            'expected': 1},
                    {'url': '/machines?switchId=1&vladId=1&limit=2',
                            'expected': 2},
                    {'url': '/machines?switchId=4', 'expected': 0}]

        for test in testList:
            url = test['url']
            expected = test['expected']
            rv = self.app.get(url)
            data = json.loads(rv.get_data())
            count = len(data['machines'])
            self.assertEqual(rv.status_code, 200)
            self.assertEqual(count, expected)


class TestClusterAPI(ApiTestCase):

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
                "vlan": "",
                "nic": "eth0",
                "promisc": 1},
            "tenant": {
                "ip_start": "192.168.1.100",
                "ip_end": "192.168.1.200",
                "netmask": "255.255.255.0",
                "nic": "eth1",
                "promisc": 0},
            "public": {
                "ip_start": "192.168.1.100",
                "ip_end": "192.168.1.200",
                "netmask": "255.255.255.0",
                "nic": "eth3",
                "promisc": 1},
            "storage": {
                "ip_start": "192.168.1.100",
                "ip_end": "192.168.1.200",
                "netmask": "255.255.255.0",
                "nic": "eth3",
                "promisc": 1}},
        "global": {
            "gateway": "192.168.1.1",
            "proxy": "",
            "ntp_sever": "",
            "nameservers": "8.8.8.8",
            "search_path": "ods.com,ods1.com"}}

    def setUp(self):
        super(TestClusterAPI, self).setUp()
        #Prepare testing data
        with database.session() as session:
            cluster = Cluster(name='cluster_01')
            session.add(cluster)
            session.flush()

    def tearDown(self):
        super(TestClusterAPI, self).tearDown()

    def test_get_cluster_by_id(self):
        # a. Get an existing cluster
        # b. Get a non-existing cluster, return 404
        testList = [{'url': '/clusters/1', 'expected_code': 200,
                     'expected': {'clusterName': 'cluster_01',
                                  'href': '/clusters/1'}},
                    {'url': '/clusters/1000', 'expected_code': 404}]

        for test in testList:
            url = test['url']
            rv = self.app.get(url)
            data = json.loads(rv.get_data())
            self.assertEqual(rv.status_code, test['expected_code'])
            if 'expected' in test:
                excepted_name = test['expected']['clusterName']
                excepted_href = test['expected']['href']
                self.assertEqual(data['cluster']['clusterName'], excepted_name)
                self.assertEqual(data['cluster']['link']['href'],
                                 excepted_href)

    # Create a cluster
    def test_post_cluster(self):
        # a. Post a new cluster
        cluster_req = {'cluster': {'name': 'cluster_02',
                                   'adapter_id': 1}}
        url = '/clusters'
        rv = self.app.post(url, data=json.dumps(cluster_req))
        data = json.loads(rv.get_data())

        self.assertEqual(rv.status_code, 200)
        self.assertEqual(data['cluster']['id'], 2)
        self.assertEqual(data['cluster']['name'], 'cluster_02')

        #b. Post an existing cluster, return 409
        rv = self.app.post(url, data=json.dumps(cluster_req))
        self.assertEqual(rv.status_code, 409)
        #c. Post a new cluster without providing a name
        cluster_req['cluster']['name'] = ''
        rv = self.app.post(url, data=json.dumps(cluster_req))
        data = json.loads(rv.get_data())
        self.assertEqual(data['cluster']['id'], 3)

    def test_get_clusters(self):
        #Insert more clusters in db
        with database.session() as session:
            clusters_list = [
                Cluster(name="cluster_02"),
                Cluster(name="cluster_03"),
                Cluster(name="cluster_04")]
            session.add_all(clusters_list)
            session.flush()
        
        url = "/clusters"
        rv = self.app.get(url)
        data = json.loads(rv.get_data())
        self.assertEqual(len(data['clusters']), 4)

    def test_put_cluster_security_resource(self):
        # Prepare testing data
        security = {'security': self.SECURITY_CONFIG}

        # a. Upate cluster's security config
        url = '/clusters/1/security'
        rv = self.app.put(url, data=json.dumps(security))
        self.assertEqual(rv.status_code, 200)

        # b. Update a non-existing cluster's resource
        url = '/clusters/1000/security'
        rv = self.app.put(url, data=json.dumps(security))
        self.assertEqual(rv.status_code, 404)

        # c. Update invalid cluster config item
        url = '/clusters/1/xxx'
        rv = self.app.put(url, data=json.dumps(security))
        self.assertEqual(rv.status_code, 400)

        # d. Security config is invalid -- some required field is null
        security['security']['server_credentials']['username'] = None
        rv = self.app.put(url, data=json.dumps(security))
        self.assertEqual(rv.status_code, 400)

        # e. Security config is invalid -- keyword is incorrect
        security['security']['xxxx'] = {'xxx': 'xxx'}
        rv = self.app.put(url, data=json.dumps(security))
        self.assertEqual(rv.status_code, 400)

    def test_put_cluster_networking_resource(self):
        networking = {"networking" : self.NETWORKING_CONFIG}
        url = "/clusters/1/networking"
        rv = self.app.put(url, data=json.dumps(networking))
        self.assertEqual(rv.status_code, 200)

    def test_get_cluster_resource(self):
        # Test only one resource - secuirty as an example
        with database.session() as session:
            cluster = session.query(Cluster).filter_by(id=1).first()
            cluster.security = self.SECURITY_CONFIG

        # a. query secuirty config by cluster id
        url = '/clusters/1/security'
        rv = self.app.get(url)
        data = json.loads(rv.get_data())
        self.assertEqual(rv.status_code, 200)
        self.assertDictEqual(data['security'], self.SECURITY_CONFIG)

        # b. query a nonsupported resource, return 400
        url = '/clusters/1/xxx'
        rv = self.app.get(url)
        data = json.loads(rv.get_data())
        self.assertEqual(rv.status_code, 400)
        excepted_err_msg = "Invalid resource name 'xxx'!"
        self.assertEqual(data['message'], excepted_err_msg)

    def test_cluster_action(self):
        from sqlalchemy import func
        #Prepare testing data: create machines, clusters in database
        #The first three machines will belong to cluster_01, the last one
        #belongs to cluster_02
        with database.session() as session:
            machines = [Machine(mac='00:27:88:0c:01'),
                        Machine(mac='00:27:88:0c:02'),
                        Machine(mac='00:27:88:0c:03'),
                        Machine(mac='00:27:88:0c:04')]
            clusters = [Cluster(name='cluster_02')]
            session.add_all(machines)
            session.add_all(clusters)
            # add a host to machine '00:27:88:0c:04' to cluster_02
            host = ClusterHost(cluster_id=2, machine_id=4,
                               hostname='host_c2_01')
            session.add(host)

        # Do an action to a non-existing cluster
        url = '/clusters/1000/action'
        request = {'addHosts': [10, 20, 30]}
        rv = self.app.post(url, data=json.dumps(request))
        self.assertEqual(rv.status_code, 404)

        # Test 'addHosts' action on cluster_01
        # 1. add a host with  non-existing machine
        url = '/clusters/1/action'
        request = {'addHosts': [1, 1000, 1001]}
        rv = self.app.post(url, data=json.dumps(request))
        self.assertEqual(rv.status_code, 404)
        # ClusterHost table should not have any records.
        with database.session() as session:
            hosts_num = session.query(func.count(ClusterHost.id))\
                               .filter_by(cluster_id=1).scalar()
            self.assertEqual(hosts_num, 0)

        # 2. add a host with a installed machine
        request = {'addHosts': [1, 4]}
        rv = self.app.post(url, data=json.dumps(request))
        self.assertEqual(rv.status_code, 409)
        data = json.loads(rv.get_data())
        self.assertEqual(len(data['failedMachines']), 1)

        # 3. add hosts to cluster_01
        request = {'addHosts': [1, 2, 3]}
        rv = self.app.post(url, data=json.dumps(request))
        self.assertEqual(rv.status_code, 200)
        data = json.loads(rv.get_data())
        self.assertEqual(len(data['cluster_hosts']), 3)

        # 4. try to remove some hosts which do not exists
        request = {'removeHosts': [1, 1000, 1001]}
        rv = self.app.post(url, data=json.dumps(request))
        self.assertEqual(rv.status_code, 404)
        data = json.loads(rv.get_data())
        self.assertEqual(len(data['failedHosts']), 2)

        # 5. sucessfully remove requested hosts
        request = {'removeHosts': [1, 2]}
        rv = self.app.post(url, data=json.dumps(request))
        self.assertEqual(rv.status_code, 200)
        data = json.loads(rv.get_data())
        self.assertEqual(len(data['cluster_hosts']), 2)

        # 6. Test 'replaceAllHosts' action on cluster_01
        request = {'replaceAllHosts': [1, 2, 3]}
        rv = self.app.post(url, data=json.dumps(request))
        self.assertEqual(rv.status_code, 200)
        data = json.loads(rv.get_data())
        self.assertEqual(len(data['cluster_hosts']), 3)

        # 7. Test 'deploy' action on cluster_01
        request = {'deploy': {}}
        rv = self.app.post(url, data=json.dumps(request))
        self.assertEqual(rv.status_code, 202)

        # 8. Test deploy cluster_01 the second time
        rv = self.app.post(url, data=json.dumps(request))
        self.assertEqual(rv.status_code, 400)

        # 9. Try to deploy cluster_02  which no host
        url = '/clusters/2/action'
        with database.session() as session:
            session.query(ClusterHost).filter_by(cluster_id=2)\
                                      .delete(synchronize_session=False)
            host = session.query(ClusterHost).filter_by(cluster_id=2).first()

        rv = self.app.post(url, data=json.dumps(request))
        self.assertEqual(rv.status_code, 404)


class ClusterHostAPITest(ApiTestCase):

    def setUp(self):
        super(ClusterHostAPITest, self).setUp()
        self.test_config_data = {
            "networking": {
                "interfaces": {
                    "management": {
                        "ip": "192.168.1.1"}},
                "global": {}},
            "roles": ""}
        # Insert a host into database for testing
        with database.session() as session:
            clusters_list = [Cluster(name='cluster_01'),
                             Cluster(name='cluster_02')]
            session.add_all(clusters_list)
            hosts_list = [ClusterHost(hostname='host_02', cluster_id=1),
                          ClusterHost(hostname='host_03', cluster_id=1),
                          ClusterHost(hostname='host_04', cluster_id=2)]
            host = ClusterHost(hostname='host_01', cluster_id=1)
            host.config_data = json.dumps(self.test_config_data)
            session.add(host)
            session.add_all(hosts_list)

    def tearDown(self):
        super(ClusterHostAPITest, self).tearDown()

    def test_clusterHost_get_config(self):
        # 1. Try to get a config of the cluster host which does not exist
        url = '/clusterhosts/1000/config'
        rv = self.app.get(url)
        self.assertEqual(404, rv.status_code)

        # 2. Get a config of a cluster host sucessfully
        test_config_data = deepcopy(self.test_config_data)
        test_config_data['hostname'] = 'host_01'

        url = '/clusterhosts/1/config'
        rv = self.app.get(url)
        self.assertEqual(200, rv.status_code)
        config = json.loads(rv.get_data())['config']
        expected_config = deepcopy(test_config_data)
        expected_config['hostid'] = 1
        expected_config['hostname'] = 'host_01'
        expected_config['clusterid'] = 1
        expected_config['clustername'] = 'cluster_01'
        self.assertDictEqual(config, expected_config)

    def test_clusterHost_put_config(self):
        config = deepcopy(self.test_config_data)
        config['roles'] = ['base']

        # 1. Try to put a config of the cluster host which does not exist
        url = '/clusterhosts/1000/config'
        rv = self.app.put(url, data=json.dumps(config))
        self.assertEqual(404, rv.status_code)

        # 2. Config with incorrect ip format
        url = '/clusterhosts/1/config'
        config2 = deepcopy(self.test_config_data)
        config2['hostname'] = 'host_01_01'
        config2['networking']['interfaces']['management']['ip'] = 'xxx'
        rv = self.app.put(url, data=json.dumps(config2))
        self.assertEqual(400, rv.status_code)

        # 3. Config put sucessfully
        rv = self.app.put(url, data=json.dumps(config))
        self.assertEqual(200, rv.status_code)
        with database.session() as session:
            config_db = session.query(ClusterHost.config_data)\
                               .filter_by(id=1).first()[0]
            self.assertDictEqual(config, json.loads(config_db))

    def test_clusterHost_delete_subkey(self):
        # 1. Try to delete an unqalified subkey of config
        url = '/clusterhosts/1/config/gateway'
        rv = self.app.delete(url)
        self.assertEqual(400, rv.status_code)

        # 2. Try to delete a subkey sucessfully
        url = 'clusterhosts/1/config/ip'
        rv = self.app.delete(url)
        self.assertEqual(200, rv.status_code)

        expected_config = deepcopy(self.test_config_data)
        expected_config['networking']['interfaces']['management']['ip'] = ''
        with database.session() as session:
            config_db = session.query(ClusterHost.config_data).filter_by(id=1)\
                                                              .first()[0]
            self.assertDictEqual(expected_config, json.loads(config_db))

        # 3. Try to delete a subkey of a config belonged to an immtable host
        with database.session() as session:
            session.query(ClusterHost).filter_by(id=1)\
                                      .update({'mutable': False})
        url = 'clusterhosts/1/config/ip'
        rv = self.app.delete(url)
        self.assertEqual(400, rv.status_code)

    def test_clusterHost_get_by_id(self):
        # 1. Get host sucessfully
        url = '/clusterhosts/1'
        rv = self.app.get(url)
        self.assertEqual(200, rv.status_code)
        hostname = json.loads(rv.get_data())['cluster_host']['hostname']
        self.assertEqual('host_01', hostname)

        # 2. Get a non-existing host
        url = '/clusterhosts/1000'
        rv = self.app.get(url)
        self.assertEqual(404, rv.status_code)

    def test_list_clusterhosts(self):
        # 1. list the cluster host whose hostname is host_01
        url = '/clusterhosts?hostname=host_02'
        rv = self.app.get(url)
        self.assertEqual(200, rv.status_code)
        hostname = json.loads(rv.get_data())['cluster_hosts'][0]['hostname']
        self.assertEqual('host_02', hostname)

        # 2. list cluster hosts whose cluster name is cluster_01
        url = '/clusterhosts?clustername=cluster_01'
        rv = self.app.get(url)
        self.assertEqual(200, rv.status_code)
        hosts_num = len(json.loads(rv.get_data())['cluster_hosts'])
        self.assertEqual(3, hosts_num)

        # 3. list the host whose name is host_03 and cluser name is cluster_01
        url = '/clusterhosts?hostname=host_03&clustername=cluster_01'
        rv = self.app.get(url)
        self.assertEqual(200, rv.status_code)
        hostname = json.loads(rv.get_data())['cluster_hosts'][0]['hostname']
        self.assertEqual('host_03', hostname)

        # 4. list all hosts
        url = '/clusterhosts'
        rv = self.app.get(url)
        self.assertEqual(200, rv.status_code)
        hosts_num = len(json.loads(rv.get_data())['cluster_hosts'])
        self.assertEqual(4, hosts_num)

        # 5. Cannot found any hosts in clust name: cluster_1000
        url = '/clusterhosts?clustername=cluster_1000'
        rv = self.app.get(url)
        self.assertEqual(200, rv.status_code)
        hosts_result = json.loads(rv.get_data())['cluster_hosts']
        self.assertListEqual([], hosts_result)

    def test_host_installing_progress(self):
        # 1. Get progress of a non-existing host
        url = '/clusterhosts/1000/progress'
        rv = self.app.get(url)
        self.assertEqual(404, rv.status_code)

        # 2. Get progress of a host without state
        url = '/clusterhosts/1/progress'
        rv = self.app.get(url)
        self.assertEqual(200, rv.status_code)

        # 3. Get progress which is in UNINITIALIZED state
        with database.session() as session:
            host = session.query(ClusterHost).filter_by(id=1).first()
            host.state = HostState()

        rv = self.app.get(url)
        self.assertEqual(200, rv.status_code)
        data = json.loads(rv.get_data())
        self.assertEqual('UNINITIALIZED', data['progress']['state'])
        self.assertEqual(0, data['progress']['percentage'])

        # 4. Get progress which is in INSTALLING state
        with database.session() as session:
            host = session.query(ClusterHost).filter_by(id=1).first()
            host.state.state = 'INSTALLING'
            session.query(HostState).filter_by(id=1)\
                                    .update({'progress': 0.3,
                                            'message': 'Configuring...',
                                            'severity': 'INFO'})
        rv = self.app.get(url)
        self.assertEqual(200, rv.status_code)
        data = json.loads(rv.get_data())
        self.assertEqual('INSTALLING', data['progress']['state'])
        self.assertEqual(0.3, data['progress']['percentage'])


class TestAdapterAPI(ApiTestCase):

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
        url = '/adapters/1'
        rv = self.app.get(url)
        self.assertEqual(200, rv.status_code)
        data = json.loads(rv.get_data())
        self.assertEqual('Centos_openstack', data['adapter']['name'])

    def test_list_adapter_roles(self):
        url = '/adapters/1/roles'
        rv = self.app.get(url)
        self.assertEqual(200, rv.status_code)
        data = json.loads(rv.get_data())
        self.assertEqual(2, len(data['roles']))

    def test_list_adapters(self):
        url = '/adapters?name=Centos_openstack'
        rv = self.app.get(url)
        data = json.loads(rv.get_data())
        self.assertEqual(200, rv.status_code)
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
        rv = self.app.get(url)
        data = json.loads(rv.get_data())
        self.assertEqual(200, rv.status_code)
        self.assertEqual(2, len(data['adapters']))
        

if __name__ == '__main__':
    unittest2.main()
