import subprocess
from compass.hdsdiscovery import utils
from compass.hdsdiscovery import base


CLASS_NAME = "Mac"


class Mac(base.BasePlugin):
    """Processes MAC address"""

    def __init__(self, host, credential):
        self.mac_mib_obj = 'HUAWEI-L2MAM-MIB::hwDynFdbPort'
        self.host = host
        self.credential = credential

    def process_data(self, oper="SCAN"):
        """
        Dynamically call the function according 'oper'

        :param oper: operation of data processing
        """
        func_name = oper.lower()
        return getattr(self, func_name)()

    def scan(self):
        """
        Implemnets the scan method in BasePlugin class. In this mac module,
        mac addesses were retrieved by snmpwalk commandline.
        """

        version = self.credential['Version']
        community = self.credential['Community']
        if version == 2:
        # Command accepts 1|2c|3 as version arg
            version = '2c'

        cmd = 'snmpwalk -v%s -Cc -c %s -O b %s %s' % \
              (version, community, self.host, self.mac_mib_obj)

        try:
            sub_p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
            result = []
            for line in sub_p.stdout.readlines():
                if not line or line == '\n':
                    continue
                temp = {}
                arr = line.split(" ")
                temp['iid'] = arr[0].split('.', 1)[-1]
                temp['value'] = arr[-1]
                result.append(temp)

            return self._process_mac(result)
        except:
            return None

    def _process_mac(self, walk_result):
        """Get mac addresses from snmpwalk result"""

        mac_list = []

        for entity in walk_result:

            iid = entity['iid']
            ifIndex = entity['value']

            numbers = iid.split('.')
            mac = self._get_mac_address(numbers, 6)
            vlan = numbers[6]
            port = self._get_port(ifIndex)

            attri_dict_temp = {}
            attri_dict_temp['port'] = port
            attri_dict_temp['mac'] = mac
            attri_dict_temp['vlan'] = vlan
            mac_list.append(attri_dict_temp)

        return mac_list

    def _get_port(self, if_index):
        """Get port number by using snmpget and OID 'IfName'

        :param int if_index:the index of 'IfName'
        """

        if_name = '.'.join(('ifName', if_index))
        result = utils.snmp_get(self.host, self.credential, if_name)
        """result variable will be  like: GigabitEthernet0/0/23"""
        port = result.split("/")[2]
        return port

    def _convert_to_hex(self, integer):
        """Convert the integer from decimal to hex"""

        hex_string = str(hex(int(integer)))[2:]
        length = len(hex_string)
        if length == 1:
            hex_string = str(0) + hex_string

        return hex_string

    # Get Mac address: The first 6th numbers in the list
    def _get_mac_address(self, iid_numbers, length):
        """Assemble mac address from the list"""

        mac = ""
        for index in range(length):
            num = self._convert_to_hex(iid_numbers[index])
            mac = ':'.join((mac, num))
        mac = mac[1:]
        return mac
