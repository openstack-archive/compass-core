"""Huawei Switch"""
from compass.hdsdiscovery import base


#Vendor_loader will load vendor instance by CLASS_NAME
CLASS_NAME = "Huawei"


class Huawei(base.BaseSnmpVendor):
    """Huawei switch"""

    def __init__(self):
        base.BaseSnmpVendor.__init__(self, ["huawei"])
        self.__name = "huawei"

    @property
    def name(self):
        """Return switch name"""
        return self.__name
