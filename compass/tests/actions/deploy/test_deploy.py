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


"""Test deploy action module."""


from mock import patch
import os
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from compass.actions import deploy
from compass.actions import util
from compass.utils import flags
from compass.utils import logsetting


class TestDeployAction(unittest2.TestCase):
    """Test deploy moudle functions in actions."""
    def setUp(self):
        super(TestDeployAction, self).setUp()

    def tearDown(self):
        super(TestDeployAction, self).tearDown()

    @patch('compass.db.api.cluster.get_cluster_metadata')
    @patch('compass.db.api.adapter_holder.get_adapter')
    def test_get_adatper_info(self, mock_get_adapter, mock_get_cluster_meta):
        mock_get_adapter.return_value = {
            "id": 1,
            "name": "test_adapter",
            "flavors": [
                {
                    "flavor_name": "test_flavor",
                    "template": "test_tmpl.tmpl",
                    "roles": [
                        {
                            "name": "test-role-1",
                            "display_name": "test role 1"
                        },
                        {
                            "name": "test-role-2",
                            "display_name": "test role 2"
                        }
                    ]
                }
            ],
            "os_installer": {
                "name": "test_os_installer",
                "settings": {
                    "url": "http://127.0.0.1"
                }
            },
            "pk_installer": {
                "name": "test_pk_installer",
                "settings": {
                    "url": "http://127.0.0.1"
                }
            }
        }
        mock_get_cluster_meta.return_value = {
            "os_config": {},
            "package_config": {}
        }
        expected_output = {
            "id": 1,
            "name": "test_adapter",
            "flavors": [{
                "flavor_name": "test_flavor",
                "template": "test_tmpl.tmpl",
                "roles": ["test-role-1", "test-role-2"]
            }],
            "os_installer": {
                "name": "test_os_installer",
                "settings": {
                    "url": "http://127.0.0.1"
                }
            },
            "pk_installer": {
                "name": "test_pk_installer",
                "settings": {
                    "url": "http://127.0.0.1"
                }
            },
            "metadata": {
                "os_config": {},
                "package_config": {}
            }
        }
        output = util.ActionHelper.get_adapter_info(1, 1, None)
        self.maxDiff = None
        self.assertDictEqual(expected_output, output)

    @patch('compass.db.api.cluster.get_cluster_host_config')
    @patch('compass.db.api.cluster.get_cluster_host')
    def test_get_hosts_info(self, mock_get_cluster_host,
                            mock_get_cluster_host_config):
        mock_get_cluster_host_config.return_value = {
            "os_config": {},
            "package_config": {},
            "deployed_os_config": {},
            "deployed_package_config": {}
        }
        mock_get_cluster_host.return_value = {
            "id": 1,
            "host_id": 10,
            "name": "test",
            "mac": "00:89:23:a1:e9:10",
            "hostname": "server01",
            "roles": [
                {
                    "name": "test-role-1",
                    "display_name": "test role 1"
                },
                {
                    "name": "test-role-2",
                    "display_name": "test role 2"
                }
            ],
            "networks": [
                {
                    "interface": "eth0",
                    "ip": "127.0.0.1",
                    "netmask": "255.255.255.0",
                    "is_mgmt": True,
                    "subnet": "127.0.0.0/24",
                    "is_promiscuous": False,
                }
            ]
        }
        expected_output = {
            1: {
                "id": 1,
                "host_id": 10,
                "name": "test",
                "mac": "00:89:23:a1:e9:10",
                "hostname": "server01",
                "roles": ["test-role-1", "test-role-2"],
                "networks": {
                    "eth0": {
                        "ip": "127.0.0.1",
                        "netmask": "255.255.255.0",
                        "is_mgmt": True,
                        "subnet": "127.0.0.0/24",
                        "is_promiscuous": False
                    }
                },
                "os_config": {},
                "package_config": {},
                "deployed_os_config": {},
                "deployed_package_config": {}
            }
        }
        output = util.ActionHelper.get_hosts_info(1, [1], None)
        self.maxDiff = None
        self.assertDictEqual(expected_output, output)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
