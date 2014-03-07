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

"""Huawei Switch Mac module."""
import logging

from compass.hdsdiscovery.base import BaseSnmpMacPlugin
from compass.hdsdiscovery import utils


CLASS_NAME = "Mac"


class Mac(BaseSnmpMacPlugin):
    """Processes MAC address."""

    def __init__(self, host, credential):
        super(Mac, self).__init__(
            host, credential,
            'HUAWEI-L2MAM-MIB::hwDynFdbPort')

    def scan(self):
        """Implemnets the scan method in BasePlugin class.

           .. note::
              In this mac module, mac addesses were retrieved by
              snmpwalk commandline.
        """
        results = utils.snmpwalk_by_cl(self.host, self.credential, self.oid)

        if not results:
            logging.info("[Huawei][mac] No results returned from SNMP walk!")
            return None

        mac_list = []

        for entity in results:
            # The format of 'iid' is like '248.192.1.214.34.15.31.1.48'
            # The first 6 numbers will be the MAC address
            # The 7th number is its vlan ID
            numbers = entity['iid'].split('.')
            mac = self.get_mac_address(numbers[:6])
            vlan = numbers[6]
            port = self.get_port(entity['value'])

            tmp = {}
            tmp['port'] = port
            tmp['mac'] = mac
            tmp['vlan'] = vlan
            mac_list.append(tmp)

        return mac_list
