"""Manage hdsdiscovery functionalities"""
import os
import re
import logging

from compass.hdsdiscovery import utils


class HDManager:
    """Process a request."""

    def __init__(self):
        base_dir = os.path.dirname(os.path.realpath(__file__))
        self.vendors_dir = os.path.join(base_dir, 'vendors')
        self.vendor_plugins_dir = os.path.join(self.vendors_dir, '?/plugins')

    def learn(self, host, credential, vendor, req_obj, oper="SCAN", **kwargs):
        """Insert/update record of switch_info. Get expected results from
           switch according to sepcific operation.

        :param req_obj: the object of a machine
        :param host: switch IP address
        :param credientials: credientials to access switch
        :param oper: operations of the plugin (SCAN, GETONE, SET)
        :param kwargs(optional): key-value pairs
        """
        plugin_dir = self.vendor_plugins_dir.replace('?', vendor)
        if not os.path.exists(plugin_dir):
            logging.error('No such directory: %s', plugin_dir)
            return None

        plugin = utils.load_module(req_obj, plugin_dir, host, credential)
        if not plugin:
            # No plugin found!
            #TODO add more code to catch excpetion or unexpected state
            logging.error('no plugin %s to load from %s', req_obj, plugin_dir)
            return None

        return plugin.process_data(oper)

    def is_valid_vendor(self, host, credential, vendor):
        """ Check if vendor is associated with this host and credential

        :param host: switch ip
        :param credential: credential to access switch
        :param vendor: the vendor of switch
        """
        vendor_dir = os.path.join(self.vendors_dir, vendor)
        if not os.path.exists(vendor_dir):
            logging.error('no such directory: %s', vendor_dir)
            return False

        vendor_instance = utils.load_module(vendor, vendor_dir)
        #TODO add more code to catch excpetion or unexpected state
        if not vendor_instance:
            # Cannot found the vendor in the directory!
            logging.error('no vendor instance %s load from %s',
                          vendor, vendor_dir)
            return False

        return vendor_instance.is_this_vendor(host, credential)

    def get_vendor(self, host, credential):
        """ Check and get vendor of the switch.

        :param host: switch ip:
        :param credential: credential to access switch
        """
        # List all vendors in vendors directory -- a directory but hidden
        # under ../vendors
        all_vendors = sorted(o for o in os.listdir(self.vendors_dir)
                       if os.path.isdir(os.path.join(self.vendors_dir, o))
                       and re.match(r'^[^\.]', o))

        logging.debug("[get_vendor]: %s ", all_vendors)
        for vname in all_vendors:
            vpath = os.path.join(self.vendors_dir, vname)
            instance = utils.load_module(vname, vpath)
            #TODO add more code to catch excpetion or unexpected state
            if not instance:
                logging.error('no instance %s load from %s', vname, vpath)
                continue

            if instance.is_this_vendor(host, credential):
                return vname

        return None
