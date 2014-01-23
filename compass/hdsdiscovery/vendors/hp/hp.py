"""Vendor: HP"""
from compass.hdsdiscovery import base


#Vendor_loader will load vendor instance by CLASS_NAME
CLASS_NAME = 'Hp'


class Hp(base.BaseSnmpVendor):
    """Hp switch object"""

    def __init__(self):
        base.BaseSnmpVendor.__init__(self, ['hp', 'procurve'])
        self.names = ['hp', 'procurve']

    @property
    def name(self):
        """Get 'name' proptery"""
        return self.names[0]
