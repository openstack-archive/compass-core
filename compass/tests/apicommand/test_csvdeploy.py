#!/usr/bin/env python
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

"""test deploy from csv file."""
import mock
import os
import shutil
import signal
import simplejson as json
import socket
import subprocess
import sys
import tempfile
import time
import unittest2


curr_dir = os.path.dirname(os.path.realpath(__file__))
api_cmd_path = '/'.join((
    os.path.dirname(os.path.dirname(os.path.dirname(curr_dir))), 'bin'))
sys.path.append(api_cmd_path)


import csvdeploy


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from compass.db import database
from compass.db.model import Cluster
from compass.db.model import ClusterHost
from compass.utils import flags
from compass.utils import logsetting

from compass.apiclient.restful import Client


class ApiTestCase(unittest2.TestCase):
    def setUp(self):
        super(ApiTestCase, self).setUp()
        # Create database file
        try:
            self.db_dir = tempfile.mkdtemp()
            self.db_file = '/'.join((self.db_dir, 'app.db'))
        except Exception:
            sys.exit(2)

        database_url = '/'.join(('sqlite://', self.db_file))
        # Get a free random port for app server

        try:
            tmp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tmp_socket.bind(('', 0))
            self.port = tmp_socket.getsockname()[-1]
            tmp_socket.close()
            time.sleep(10)
        except socket.error:
            sys.exit(1)

        cmd = '%s run_server.py %s %d' % (
            sys.executable, database_url, self.port)
        self.proc = subprocess.Popen(cmd, shell=True,
                                     stderr=subprocess.PIPE,
                                     preexec_fn=os.setsid,
                                     cwd=curr_dir)
        time.sleep(5)

        # Initial database
        try:
            database.init(database_url)
        except Exception as e:
            print "======>", e

    def tearDown(self):
        super(ApiTestCase, self).tearDown()

        database.ENGINE.dispose()
        database.init('sqlite://')
        os.killpg(self.proc.pid, signal.SIGTERM)
        try:
            if os.path.exists(self.db_dir):
                shutil.rmtree(self.db_dir)
        except Exception:
            sys.exit(1)


class TestAPICommand(ApiTestCase):
    CSV_IMPORT_DIR = '/'.join((curr_dir, 'test_files'))

    def setUp(self):
        super(TestAPICommand, self).setUp()
        self.deploy_return_val = {
            'status': 'accepted',
            'deployment': {'cluster': {'cluster_id': 1,
                                       'url': '/clusters/1/progress'},
                           'hosts': [{'host_id': 1,
                                      'url': '/cluster_hosts/1/progress'}]}}

    def tearDown(self):
        # Remove the resulting output file from the test case.
        try:
            os.remove(os.path.join(self.CSV_IMPORT_DIR, 'progress.csv'))
        except OSError:
            pass
        super(TestAPICommand, self).tearDown()

    def test_start(self):
        """test start deploy from csv."""
        Client.deploy_hosts = mock.Mock(
            return_value=(202, self.deploy_return_val))
        url = "http://127.0.0.1:%d" % self.port
        csvdeploy.start(self.CSV_IMPORT_DIR, url)
        clusters = csvdeploy.get_csv('cluster.csv',
                                     csv_dir=self.CSV_IMPORT_DIR)
        with database.session() as session:
            for csv_cluster in clusters:
                cluster_id = csv_cluster['id']
                cluster = session.query(
                    Cluster
                ).filter_by(id=cluster_id).first()
                self.assertIsNotNone(cluster)
                self.assertEqual(csv_cluster['name'], cluster.name)
                self.assertDictEqual(csv_cluster['security_config'],
                                     json.loads(cluster.security_config))
                self.maxDiff = None
                self.assertDictEqual(csv_cluster['networking_config'],
                                     json.loads(cluster.networking_config))
                self.assertEqual(csv_cluster['partition_config'],
                                 json.loads(cluster.partition_config))
                self.assertEqual(csv_cluster['adapter_id'], cluster.adapter_id)
                self.maxDiff = None

            hosts = csvdeploy.get_csv('cluster_host.csv',
                                      csv_dir=self.CSV_IMPORT_DIR)
            for csv_host in hosts:
                cluster_id = csv_host['cluster_id']
                hostname = csv_host['hostname']
                host_in_db = session.query(ClusterHost)\
                                    .filter_by(cluster_id=cluster_id,
                                               hostname=hostname).first()
                self.assertIsNotNone(host_in_db)
                self.assertEqual(csv_host['hostname'], host_in_db.hostname)
                self.assertEqual(csv_host['machine_id'], host_in_db.machine_id)
                self.assertDictEqual(csv_host['config_data'],
                                     json.loads(host_in_db.config_data))
                self.maxDiff = None


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
