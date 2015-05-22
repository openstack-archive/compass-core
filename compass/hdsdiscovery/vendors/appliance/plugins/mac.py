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
from compass.utils import setting_wrapper as setting
from compass.utils import util

import logging


CLASS_NAME = "Mac"


class Mac(base.BaseSnmpMacPlugin):
    """Processes MAC address."""

    def __init__(self, host, credential):
        self.host = host
        # self.credential = credential
        # return

    def scan(self):
        """Implemnets the scan method in BasePlugin class.

           .. note::
            Dummy scan function for compass appliance.
            Returns fixed mac addresses.
        """
        mac_list = None
        machine_lists = util.load_configs(setting.MACHINE_LIST_DIR)
        for items in machine_lists:
            for item in items['MACHINE_LIST']:
                for k, v in item.items():
                    if k == self.host:
                        mac_list = v
        return mac_list
