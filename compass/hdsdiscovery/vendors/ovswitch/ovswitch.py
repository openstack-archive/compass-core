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

"""Open Vswitch module."""
import logging
import re

from compass.hdsdiscovery import base
from compass.hdsdiscovery import utils


# Vendor_loader will load vendor instance by CLASS_NAME
CLASS_NAME = "OVSwitch"


class OVSwitch(base.BaseVendor):
    """Open Vswitch."""
    def __init__(self):
        self.__name = "Open vSwitch"

    def is_this_vendor(self, sys_info, host=None, credential=None, **kwargs):
        """Determine if the hostname is accociated witH this vendor.

        :param host: swtich's IP address
        :param credential: credential to access switch
        """
        result = sys_info
        if host and credential:
            if utils.is_valid_ssh_credential(credential):
                user = credential['username']
                pwd = credential['password']

            else:
                msg = ("[OVSwitch]The format of credential %r is not for SSH "
                       "or incorrect Keywords! " % credential)
                logging.info(msg)
                return False

            cmd = "ovs-vsctl -V"
            result = None
            try:
                result = utils.ssh_remote_execute(host, user, pwd, cmd)
                logging.debug('%s result for %s is %s', cmd, host, result)
                if not result:
                    return False
            except Exception as exc:
                logging.error("No vendor or connection failed to run %s", cmd)
                logging.exception(exc)
                return False

            if isinstance(result, str):
                result = [result]

        for line in result:
            if not line:
                continue
            if re.search(r"\b" + re.escape(self.__name) + r"\b", line):
                return True

        return False

    @property
    def name(self):
        """Open Vswitch name."""
        return self.__name
