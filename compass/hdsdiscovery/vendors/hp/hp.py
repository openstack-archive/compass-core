"""Vendor: HP"""
import re
import logging

from compass.hdsdiscovery import base
from compass.hdsdiscovery import utils


#Vendor_loader will load vendor instance by CLASS_NAME
CLASS_NAME = 'Hp'


class Hp(base.BaseVendor):
    """Hp switch object"""

    def __init__(self):
        # the name of switch model belonging to Hewlett-Packard (HP) vendor
        self.names = ['hp', 'procurve']

    def is_this_vendor(self, host, credential):
        """
        Determine if the hostname is accociated witH this vendor.
        This example will use snmp sysDescr OID ,regex to extract
        the vendor's name ,and then compare with self.name variable.

        :param host: switch's IP address
        :param credential: credential to access switch
        """

        if "Version" not in credential or "Community" not in credential:
            # The format of credential is incompatible with this vendor
            err_msg = "[Hp]Missing keyword 'Version' or 'Community' in %r"
            logging.error(err_msg, credential)
            return False

        sys_info = utils.snmp_get(host, credential, "sysDescr.0")
        if not sys_info:
            logging.info("Dismatch vendor information")
            return False

        sys_info = sys_info.lower()
        for name in self.names:
            if re.search(r"\b" + re.escape(name) + r"\b", sys_info):
                return True

        return False

    @property
    def name(self):
        """Get 'name' proptery"""
        return 'hp'
