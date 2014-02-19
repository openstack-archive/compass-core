"""Open Vswitch Mac address module"""
import logging

from compass.hdsdiscovery import utils
from compass.hdsdiscovery import base


CLASS_NAME = "Mac"


class Mac(base.BasePlugin):
    """Open Vswitch MAC address module"""
    def __init__(self, host, credential):
        self.host = host
        self.credential = credential

    def process_data(self, oper="SCAN", **kwargs):
        """Dynamically call the function according 'oper'

        :param oper: operation of data processing
        """
        func_name = oper.lower()
        return getattr(self, func_name)(**kwargs)

    def scan(self, **kwargs):
        """
        Implemnets the scan method in BasePlugin class. In this module,
        mac addesses were retrieved by ssh
        """
        try:
            user = self.credential['username']
            pwd = self.credential['password']
        except KeyError:
            logging.error("Cannot find username and password in credential")
            return None

        cmd = ("BRIDGES=$(ovs-vsctl show |grep Bridge |cut -f 2 -d '\"');"
               "for br in $BRIDGES; do"
               "PORTS=$(ovs-ofctl show $br |grep addr |cut -f 1 -d ':' "
               "|egrep -v 'eth|wlan|LOCAL'|awk -F '(' '{print $1}');"
               "for port in $PORTS; do"
               "RESULT=$(ovs-appctl fdb/show $br |"
               "awk '$1 == '$port' {print $1"  "$2"  "$3}');"
               "echo '$RESULT'"
               "done;"
               "done;")
        output = None
        try:
            output = utils.ssh_remote_execute(self.host, user, pwd, cmd)
        except:
            return None

        logging.debug("[scan][output] output is %s", output)
        if not output:
            return None

        fields_arr = ['port', 'vlan', 'mac']

        result = []
        for line in output:
            if not line or line == '\n':
                continue
            values_arr = line.split()
            temp = {}
            for field, value in zip(fields_arr, values_arr):
                temp[field] = value
            result.append(temp.copy())
        return result
