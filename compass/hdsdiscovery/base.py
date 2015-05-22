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

"""
Base class extended by specific vendor in vendors directory.
A vendor needs to implement abstract methods of base class.
"""
import logging
import re

from abc import ABCMeta

from compass.hdsdiscovery.error import TimeoutError
from compass.hdsdiscovery import utils


class BaseVendor(object):
    """Basic Vendor object."""
    __metaclass__ = ABCMeta

    def is_this_vendor(self, sys_info, **kwargs):
        """Determine if the host is associated with this vendor.

        This function must be implemented by vendor itself
        """
        raise NotImplementedError


class BaseSnmpVendor(BaseVendor):
    """Base SNMP-based vendor plugin.

       .. note::
          It uses MIB-II sysDescr value to determine the vendor of the switch.
    """

    def __init__(self, matched_names):
        super(BaseSnmpVendor, self).__init__()
        self._matched_names = matched_names

    def is_this_vendor(self, sys_info, **kwargs):
        """Determine if the switch belongs to this vendor.

        Matching the system information retrieved from the switch.
        :param str sys_info: the system information retrieved from a switch
        Return True
        """
        if sys_info:
            for name in self._matched_names:
                if re.search(r"\b" + re.escape(name) + r"\b", sys_info,
                             re.IGNORECASE):
                    return True
        return False


class BasePlugin(object):
    """Extended by vendor's plugin.

    This plugin processes request and retrieve info directly from the switch.
    """
    __metaclass__ = ABCMeta

    def process_data(self, oper='SCAN', **kwargs):
        """Each vendors will have some plugins to do some operations.

        Plugin will process request data and return expected result.

        :param oper: operation function name.
        :param kwargs: key-value pairs of arguments
        """
        raise NotImplementedError

    # At least one of these three functions below must be implemented.
    def scan(self, **kwargs):
        """Get multiple records at once."""
        pass

    def set(self, **kwargs):
        """Set value to desired variable."""
        pass

    def get(self, **kwargs):
        """Get one record from a host."""
        pass


class BaseSnmpMacPlugin(BasePlugin):
    """Base snmp plugin."""

    def __init__(self, host, credential, oid='BRIDGE-MIB::dot1dTpFdbPort',
                 vlan_oid='Q-BRIDGE-MIB::dot1qPvid'):
        super(BaseSnmpMacPlugin, self).__init__()
        self.host = host
        self.credential = credential
        self.oid = oid
        self.port_oid = 'ifName'
        self.vlan_oid = vlan_oid

    def process_data(self, oper='SCAN', **kwargs):
        """progress data."""
        func_name = oper.lower()
        return getattr(self, func_name)(**kwargs)

    def scan(self, **kwargs):
        """scan."""
        results = None
        try:
            results = utils.snmpwalk_by_cl(self.host, self.credential,
                                           self.oid)
        except TimeoutError as error:
            logging.debug("PluginMac:scan snmpwalk_by_cl failed: %s",
                          error.message)
            return None

        mac_list = []
        for entity in results:
            if_index = entity['value']
            if entity and int(if_index):
                tmp = {}
                mac_numbers = entity['iid'].split('.')
                tmp['mac'] = self.get_mac_address(mac_numbers)
                tmp['port'] = self.get_port(if_index)
                tmp['vlan'] = self.get_vlan_id(if_index)
                mac_list.append(tmp)

        return mac_list

    def get_vlan_id(self, port):
        """Get vlan Id."""
        if not port:
            return None

        oid = '.'.join((self.vlan_oid, port))
        vlan_id = None
        result = None
        try:
            result = utils.snmpget_by_cl(self.host, self.credential, oid)
        except TimeoutError as error:
            logging.debug("[PluginMac:get_vlan_id snmpget_by_cl failed: %s]",
                          error.message)
            return None

        vlan_id = result.split()[-1]
        return vlan_id

    def get_port(self, if_index):
        """Get port number."""

        if_name = '.'.join((self.port_oid, if_index))
        result = None
        try:
            result = utils.snmpget_by_cl(self.host, self.credential, if_name)
        except TimeoutError as error:
            logging.debug("[PluginMac:get_port snmpget_by_cl failed: %s]",
                          error.message)
            return None

        # A result may be like "Value:  FasterEthernet1/2/34
        port = result.split()[-1].split('/')[-1]
        return port

    def convert_to_hex(self, value):
        """Convert the integer from decimal to hex."""

        return "%0.2x" % int(value)

    def get_mac_address(self, mac_numbers):
        """Assemble mac address from the list."""
        if len(mac_numbers) != 6:
            logging.error("[PluginMac:get_mac_address] MAC address must be "
                          "6 digitals")
            return None

        mac_in_hex = [self.convert_to_hex(num) for num in mac_numbers]
        return ":".join(mac_in_hex)
