"""
Base class extended by specific vendor in vendors directory.
A vendor needs to implement abstract methods of base class.
"""
import re
import logging

from compass.hdsdiscovery import utils
from compass.hdsdiscovery.error import TimeoutError


class BaseVendor(object):
    """Basic Vendor object"""

    def is_this_vendor(self, *args, **kwargs):
        """Determine if the host is associated with this vendor.
           This function must be implemented by vendor itself
        """
        raise NotImplementedError


class BaseSnmpVendor(BaseVendor):
    """Base SNMP-based vendor plugin. It uses MIB-II sysDescr value
       to determine the vendor of the switch. """

    def __init__(self, matched_names):
        self._matched_names = matched_names

    def is_this_vendor(self, host, credential, sys_info):

        if utils.is_valid_snmp_v2_credential(credential) and sys_info:
            for name in self._matched_names:
                if re.search(r"\b" + re.escape(name) + r"\b", sys_info,
                             re.IGNORECASE):
                    return True
        return False


class BasePlugin(object):
    """Extended by vendor's plugin, which processes request and
       retrieve info directly from the switch.
    """

    def process_data(self, *args, **kwargs):
        """Each vendors will have some plugins to do some operations.
           Plugin will process request data and return expected result.

        :param args: arguments
        :param kwargs: key-value pairs of arguments
        """
        raise NotImplementedError

    # At least one of these three functions below must be implemented.
    def scan(self, *args, **kwargs):
        """Get multiple records at once"""
        pass

    def set(self, *args, **kwargs):
        """Set value to desired variable"""
        pass

    def get(self, *args, **kwargs):
        """Get one record from a host"""
        pass


class BaseSnmpMacPlugin(BasePlugin):
    def __init__(self, host, credential, oid='BRIDGE-MIB::dot1dTpFdbPort',
                 vlan_oid='Q-BRIDGE-MIB::dot1qPvid'):
        self.host = host
        self.credential = credential
        self.oid = oid
        self.port_oid = 'ifName'
        self.vlan_oid = vlan_oid

    def process_data(self, oper='SCAN'):
        func_name = oper.lower()
        return getattr(self, func_name)()

    def scan(self):
        results = None
        try:
            results = utils.snmpwalk_by_cl(self.host, self.credential,
                                           self.oid)
        except TimeoutError as e:
            logging.debug("PluginMac:scan snmpwalk_by_cl failed: %s",
                          e.message)
            return None

        mac_list = []
        for entity in results:
            ifIndex = entity['value']
            if entity and int(ifIndex):
                tmp = {}
                mac_numbers = entity['iid'].split('.')
                tmp['mac'] = self.get_mac_address(mac_numbers)
                tmp['port'] = self.get_port(ifIndex)
                tmp['vlan'] = self.get_vlan_id(ifIndex)
                mac_list.append(tmp)

        return mac_list

    def get_vlan_id(self, port):
        """Get vlan Id"""
        if not port:
            return None

        oid = '.'.join((self.vlan_oid, port))
        vlan_id = None
        result = None
        try:
            result = utils.snmpget_by_cl(self.host, self.credential, oid)
        except TimeoutError as e:
            logging.debug("[PluginMac:get_vlan_id snmpget_by_cl failed: %s]",
                          e.message)
            return None

        vlan_id = result.split()[-1]
        return vlan_id

    def get_port(self, if_index):
        """Get port number"""

        if_name = '.'.join((self.port_oid, if_index))
        result = None
        try:
            result = utils.snmpget_by_cl(self.host, self.credential, if_name)
        except TimeoutError as e:
            logging.debug("[PluginMac:get_port snmpget_by_cl failed: %s]",
                          e.message)
            return None

        # A result may be like "Value:  FasterEthernet1/2/34
        port = result.split()[-1].split('/')[-1]
        return port

    def convert_to_hex(self, value):
        """Convert the integer from decimal to hex"""

        return "%0.2x" % int(value)

    def get_mac_address(self, mac_numbers):
        """Assemble mac address from the list"""
        if len(mac_numbers) != 6:
            logging.error("[PluginMac:get_mac_address] MAC address must be "
                          "6 digitals")
            return None

        mac_in_hex = [self.convert_to_hex(num) for num in mac_numbers]
        return ":".join(mac_in_hex)
