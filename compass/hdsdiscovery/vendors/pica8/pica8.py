"""Vendor: Pica8"""
from compass.hdsdiscovery import base


#Vendor_loader will load vendor instance by CLASS_NAME
CLASS_NAME = 'Pica8'


class Pica8(base.BaseSnmpVendor):
    """Pica8 switch object"""

    def __init__(self):
        base.BaseSnmpVendor.__init__(self, ['pica8'])
        self._name = 'pica8'

    @property
    def name(self):
        """Get 'name' proptery"""
        return self._name
