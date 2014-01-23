"""Manage hdsdiscovery functionalities"""
import os
import re
import logging

from compass.hdsdiscovery import utils
from compass.hdsdiscovery.error import TimeoutError

UNREACHABLE = 'unreachable'
NOTSUPPORTED = 'notsupported'


class HDManager:
    """Process a request."""

    def __init__(self):
        base_dir = os.path.dirname(os.path.realpath(__file__))
        self.vendors_dir = os.path.join(base_dir, 'vendors')
        self.vendor_plugins_dir = os.path.join(self.vendors_dir, '?/plugins')
        self.snmp_sysdescr = 'sysDescr.0'

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

        sys_info, err = self.get_sys_info(host, credential)
        if not sys_info:
            logging.debug("[hdsdiscovery][hdmanager][is_valid_vendor]"
                          "failded to get sys information: %s", err)
            return False

        instance = utils.load_module(vendor, vendor_dir)
        if not instance:
            logging.debug("[hdsdiscovery][hdmanager][is_valid_vendor]"
                          "No such vendor found!")
            return False

        if instance.is_this_vendor(host, credential, sys_info):
            logging.info("[hdsdiscovery][hdmanager][is_valid_vendor]"
                         "vendor %s is correct!", vendor)
            return True

        return False

    def get_vendor(self, host, credential):
        """ Check and get vendor of the switch.

        :param host: switch ip:
        :param credential: credential to access switch
        :return a tuple (vendor, switch_state, error)
        """

        # TODO(grace): Why do we need to have valid IP?
        # a hostname should also work.
        if not utils.valid_ip_format(host):
            logging.error("host '%s' is not valid IP address!" % host)
            return (None, "", "Invalid IP address %s!" % host)

        if not utils.is_valid_snmp_v2_credential(credential):
            logging.debug("******The credential %s of host %s cannot "
                          "be used for either SNMP v2 or SSH*****",
                          credential, host)
            return (None, "", "Invalid credential")

        sys_info, err = self.get_sys_info(host, credential)
        if not sys_info:
            return (None, UNREACHABLE, err)

        # List all vendors in vendors directory -- a directory but hidden
        # under ../vendors
        all_vendors = [o for o in os.listdir(self.vendors_dir)
                       if os.path.isdir(os.path.join(self.vendors_dir, o))
                       and re.match(r'^[^\.]', o)]

        logging.debug("[get_vendor][available vendors]: %s ", all_vendors)
        logging.debug("[get_vendor] System Information is [%s]" % sys_info)

        # TODO(grace): should not conver to lower. The vendor impl can choose
        # to do case-insensitive match
        # sys_info = sys_info.lower()
        vendor = None
        for vname in all_vendors:
            vpath = os.path.join(self.vendors_dir, vname)
            instance = utils.load_module(vname, vpath)
            if not instance:
                logging.error('no instance %s load from %s', vname, vpath)
                continue

            if instance.is_this_vendor(host, credential, sys_info):
                logging.info("[get_vendor]****Found vendor '%s'****" % vname)
                vendor = vname
                break

        if not vendor:
            logging.debug("[get_vendor] No vendor found! <==================")
            return (None, NOTSUPPORTED, "Not supported switch vendor!")

        return (vendor, "Found", "")

    def get_sys_info(self, host, credential):
        sys_info = None
        try:
            sys_info = utils.snmpget_by_cl(host,
                                           credential,
                                           self.snmp_sysdescr)
        except TimeoutError as e:
            return (None, e.message)

        return (sys_info, "")
