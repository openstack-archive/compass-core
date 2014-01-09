"""
Base class extended by specific vendor in vendors directory.
a vendor need to implment abstract methods of base class.
"""


class BaseVendor(object):
    """Basic Vendor object"""

    def is_this_vendor(self, *args, **kwargs):
        """Determine if the host is associated with this vendor.
           This function must be implemented by vendor itself
        """
        raise NotImplementedError


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
