import logging
from compass.hdsdiscovery import utils
from compass.hdsdiscovery.base import BaseSnmpMacPlugin


CLASS_NAME = "Mac"


class Mac(BaseSnmpMacPlugin):
    """Processes MAC address"""

    def __init__(self, host, credential):
        super(Mac, self).__init__(host, credential,
                                  'HUAWEI-L2MAM-MIB::hwDynFdbPort')

    def scan(self):
        """
        Implemnets the scan method in BasePlugin class. In this mac module,
        mac addesses were retrieved by snmpwalk commandline.
        """
        results = utils.snmpwalk_by_cl(self.host, self.credential, self.oid)

        if not results:
            logging.info("[Huawei][mac] No results returned from SNMP walk!")
            return None

        mac_list = []

        for entity in results:

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
