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
                'port': 1,
                'mac': '00:01:02:03:04:05',
                'vlan': 0,
            },
            {
                'port': 2,
                'mac': '06:07:08:09:0a:0b',
                'vlan': 0,
            }]
        return mac_list
