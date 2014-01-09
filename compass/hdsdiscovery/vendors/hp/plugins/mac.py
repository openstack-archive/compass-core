"""HP Switch Mac module"""
from compass.hdsdiscovery import utils
from compass.hdsdiscovery import base

CLASS_NAME = 'Mac'


class Mac(base.BasePlugin):
    """Process MAC address by HP switch"""

    def __init__(self, host, credential):
        self.host = host
        self.credential = credential

    def process_data(self, oper='SCAN'):
        """Dynamically call the function according 'oper'

        :param oper: operation of data processing
        """
        func_name = oper.lower()
        return getattr(self, func_name)()

    def scan(self):
        """
        Implemnets the scan method in BasePlugin class. In this mac module,
        mac addesses were retrieved by snmpwalk python lib.
        """
        walk_result = utils.snmp_walk(self.host, self.credential,
                                      "BRIDGE-MIB::dot1dTpFdbPort")
        if not walk_result:
            return None

        mac_list = []
        for result in walk_result:
            if not result or result['value'] == str(0):
                continue
            temp = {}
            mac_numbers = result['iid'].split('.')
            temp['mac'] = self._get_mac_address(mac_numbers)
            temp['port'] = self._get_port(result['value'])
            temp['vlan'] = self._get_vlan_id(temp['port'])
            mac_list.append(temp)

        return mac_list

    def _get_vlan_id(self, port):
        """Get vlan Id"""

        oid = '.'.join(('Q-BRIDGE-MIB::dot1qPvid', port))
        vlan_id = utils.snmp_get(self.host, self.credential, oid).strip()

        return vlan_id

    def _get_port(self, if_index):
        """Get port number"""

        if_name = '.'.join(('ifName', if_index))
        port = utils.snmp_get(self.host, self.credential, if_name).strip()
        return port

    def _convert_to_hex(self, integer):
        """Convert the integer from decimal to hex"""

        hex_string = str(hex(int(integer)))[2:]
        length = len(hex_string)
        if length == 1:
            hex_string = str(0) + hex_string

        return hex_string

    def _get_mac_address(self, mac_numbers):
        """Assemble mac address from the list"""

        mac = ""
        for num in mac_numbers:
            num = self._convert_to_hex(num)
            mac = ':'.join((mac, num))
        mac = mac[1:]
        return mac
