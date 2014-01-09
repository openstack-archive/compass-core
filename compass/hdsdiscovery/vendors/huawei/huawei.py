"""Huawei Switch"""
import re
import logging

from compass.hdsdiscovery import base
from compass.hdsdiscovery import utils


#Vendor_loader will load vendor instance by CLASS_NAME
CLASS_NAME = "Huawei"


class Huawei(base.BaseVendor):
    """Huawei switch"""

    def __init__(self):

        self.__name = "huawei"

    def is_this_vendor(self, host, credential):
        """
        Determine if the hostname is accociated witH this vendor.
        This example will use snmp sysDescr OID ,regex to extract
        the vendor's name ,and then compare with self.name variable.

        :param host: swtich's IP address
        :param credential: credential to access switch
        """
        if not utils.valid_ip_format(host):
            #invalid ip address
            return False

        if "Version" not in credential or "Community" not in credential:
            # The format of credential is incompatible with this vendor
            error_msg = "[huawei]Missing 'Version' or 'Community' in %r"
            logging.error(error_msg, credential)
            return False
        sys_info = utils.snmp_get(host, credential, "sysDescr.0")

        if not sys_info:
            return False

        if re.search(r"\b" + re.escape(self.__name) + r"\b", sys_info.lower()):
            return True

        return False

    @property
    def name(self):
        """Return switch name"""
        return self.__name
