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

"""Compass Appliance Mac module."""
from compass.hdsdiscovery import base

CLASS_NAME = "Mac"


class Mac(base.BaseSnmpMacPlugin):
    """Processes MAC address."""

    def __init__(self, host, credential):
        return

    def scan(self):
        """Implemnets the scan method in BasePlugin class.

           .. note::
            Dummy scan function for compass appliance.
            Returns fixed mac addresses.
        """
        mac_list = [
            {
                'port': '200',
                'mac': '80:fb:06:35:8c:85',
                'vlan': 0,
            },
            {
                'port': '201',
                'mac': '70:7b:e8:75:71:dc',
                'vlan': 0,
            }, {
                'port': '202',
                'mac': '80:fb:06:35:8c:a0',
                'vlan': 0,
            },
            {
                'port': '203',
                'mac': '70:7b:e8:75:71:d3',
                'vlan': 0,
            }, {
                'port': '204',
                'mac': '70:7b:e8:75:72:21',
                'vlan': 0,
            },
            {
                'port': '205',
                'mac': '70:7b:e8:75:71:37',
                'vlan': 0,
            }, {
                'port': '206',
                'mac': '70:fb:e8:75:71:d6',
                'vlan': 0,
            },
            {
                'port': '207',
                'mac': '70:7b:e8:75:71:d9',
                'vlan': 0,
            }]
        return mac_list

