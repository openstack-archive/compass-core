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
"""Test health check api."""

import os
import simplejson as json
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from test_api import ApiTestCase


from compass.db.api import cluster as cluster_db
from compass.db.api import health_check_report as health_check_db
from compass.utils import flags
from compass.utils import logsetting


report_sample = {
    "report": {
        "actions": {
            "neutron.create_network": {
                "duration": {
                    "data": [1.105, 0.973],
                    "summary": {
                        "errors": 0,
                        "success": "100.0%",
                        "min (sec)": 0.973,
                        "avg (sec)": 1.04,
                        "max (sec)": 1.105,
                        "total": 2
                    }
                }
            },
            "neutron.delete_network": {
                "duration": {
                    "data": [1.038, 0.842],
                    "summary": {
                        "errors": 0,
                        "success": "100.0%",
                        "min (sec)": 0.842,
                        "avg (sec)": 0.940,
                        "max (sec)": 1.038,
                        "total": 2
                    }
                }
            }
        },
        "errors_info": []
    },
    "raw_output": {}
}


api_resp_tpml = {
    "cluster_id": 1,
    "name": "sample_name",
    "report": {},
    "state": "verifying",
    "errors_message": ""
}


class TestHealthCheckAPI(ApiTestCase):
    """Test health check api."""

    def setUp(self):
        super(TestHealthCheckAPI, self).setUp()
        self.cluster_id = 1
        self.url = '/clusters/%s/healthreports' % self.cluster_id

    def tearDown(self):
        super(TestHealthCheckAPI, self).tearDown()

    def test_add_and_list_reports(self):
        # Create multiple reports
        reports_list = [
            {'name': 'rp1', 'category': 'c1'},
            {'name': 'rp2', 'category': 'c2'},
            {'name': 'rp3', 'category': 'c3'}
        ]
        request_data = json.dumps({"report_list": reports_list})
        return_value = self.test_client.post(self.url, data=request_data)
        resp = json.loads(return_value.get_data())

        self.assertEqual(200, return_value.status_code)
        self.assertEqual(3, len(resp))

        # Create one report
        request_data = json.dumps({'name': 'rp4 test'})
        return_value = self.test_client.post(self.url, data=request_data)
        resp = json.loads(return_value.get_data())

        self.assertEqual(200, return_value.status_code)
        self.assertEqual('rp4-test', resp['name'])

        # Create duplicate report
        return_value = self.test_client.post(self.url, data=request_data)
        self.assertEqual(409, return_value.status_code)

        # List all reports
        return_value = self.test_client.get(self.url)
        resp = json.loads(return_value.get_data())

        self.assertEqual(200, return_value.status_code)
        self.assertEqual(4, len(resp))

    def test_update_and_get_health_report(self):
        report_name = 'test-report'
        health_check_db.add_report_record(self.cluster_id, name=report_name)

        url = '/'.join((self.url, report_name))
        request_data = json.dumps(
            {"report": report_sample, "state": "finished"}
        )
        return_value = self.test_client.put(url, data=request_data)
        resp = json.loads(return_value.get_data())
        self.maxDiff = None

        self.assertEqual(200, return_value.status_code)
        self.assertDictEqual(report_sample, resp['report'])

        return_value = self.test_client.put(url, data=request_data)
        self.assertEqual(403, return_value.status_code)

        # Get report
        return_value = self.test_client.get(url)

        self.assertEqual(200, return_value.status_code)
        self.assertDictEqual(report_sample, resp['report'])

    def test_action_start_check_health(self):
        url = '/clusters/%s/action' % self.cluster_id
        request_data = json.dumps({'check_health': None})

        # Cluster's state is not 'SUCCESSFUL' yet.
        return_value = self.test_client.post(url, data=request_data)
        self.assertEqual(403, return_value.status_code)

        # Cluster has been deployed successfully.
        cluster_db.update_cluster_state(
            self.cluster_id, state='SUCCESSFUL'
        )
        return_value = self.test_client.post(url, data=request_data)
        self.assertEqual(202, return_value.status_code)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
