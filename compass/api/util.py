"""Utils for API usage"""
import logging

from flask import make_response
from flask.ext.restful import Api

import re
from netaddr import IPAddress
import simplejson as json

from compass.api import app

api = Api(app)


def make_json_response(status_code, data):
    """Wrap json format to the reponse object"""

    result = json.dumps(data, indent=4)
    resp = make_response(result, status_code)
    resp.headers['Content-type'] = 'application/json'
    return resp


def add_resource(*args, **kwargs):
    """Add resource"""
    api.add_resource(*args, **kwargs)


def is_valid_ip(ip_address):
    """Valid the format of an Ip address"""
    if not ip_address:
        return False

    regex = ('^(([0-9]|[1-9][0-9]|1[0-9]{2}|[1-2][0-4][0-9]|25[0-5])\.)'
             '{3}'
             '([0-9]|[1-9][0-9]|1[0-9]{2}|[1-2][0-4][0-9]|25[0-5])')

    if re.match(regex, ip_address):
        return True

    return False


def is_valid_ipnetowrk(ip_network):
    """Valid the format of an Ip network"""

    if not ip_network:
        return False

    regex = ('^(([0-9]|[1-9][0-9]|1[0-9]{2}|[1-2][0-4][0-9]|25[0-5])\.)'
             '{3}'
             '([0-9]|[1-9][0-9]|1[0-9]{2}|[1-2][0-4][0-9]|25[0-5])'
             '((\/[0-9]|\/[1-2][0-9]|\/[1-3][0-2]))$')

    if re.match(regex, ip_network):
        return True
    return False


def is_valid_netmask(ip_addr):
    """Valid the format of a netmask"""
    try:
        ip_address = IPAddress(ip_addr)
        return ip_address.is_netmask()

    except Exception:
        return False


def is_valid_gateway(ip_addr):
    """Valid the format of gateway"""

    invalid_ip_prefix = ['0', '224', '169', '127']
    try:
        # Check if ip_addr is an IP address and not start with 0
        ip_addr_prefix = ip_addr.split('.')[0]
        if is_valid_ip(ip_addr) and ip_addr_prefix not in invalid_ip_prefix:
            ip_address = IPAddress(ip_addr)
            if not ip_address.is_multicast():
                # Check if ip_addr is not multicast and reserved IP
                return True
        return False
    except Exception:
        return False


def is_valid_security_config(config):
    """Valid the format of security section in config"""

    security_keys = ['server_credentials', 'service_credentials',
                     'console_credentials']
    fields = ['username', 'password']
    logging.debug('config: %s', config)
    for key in security_keys:
        try:
            content = config[key]
        except KeyError:
            error_msg = "Missing '%s' in security config!" % key
            logging.error(error_msg)
            raise KeyError(error_msg)

        for k in fields:
            try:
                value = content[k]
                if not value:
                    return False, '%s in %s cannot be null!' % (k, key)

            except KeyError:
                error_msg = ("Missing '%s' in '%s' section of security config"
                             % (k, key))
                logging.error(error_msg)
                raise KeyError(error_msg)

    return True, 'valid!'


def is_valid_networking_config(config):
    """Valid the format of networking config"""

    networking = ['interfaces', 'global']

    def _is_valid_interfaces_config(interfaces_config):
        """Valid the format of interfaces section in config"""

        expected_keys = ['management', 'tenant', 'public', 'storage']
        required_fields = ['nic', 'promisc']
        normal_fields = ['ip_start', 'ip_end', 'netmask']
        other_fields = ['gateway', 'vlan']

        interfaces_keys = interfaces_config.keys()
        for key in expected_keys:
            if key not in interfaces_keys:
                error_msg = "Missing '%s' in interfaces config!" % key
                return False, error_msg

            content = interfaces_config[key]
            for field in required_fields:
                if field not in content:
                    error_msg = "Keyword '%s' in interface %s cannot be None!"\
                                % (field, key)
                    return False, error_msg

                value = content[field]
                if value is None:
                    error_msg = ("The value of '%s' in '%s' "
                                 'config cannot be None!' %
                                 (field, key))
                    return False, error_msg

                if field == 'promisc':
                    valid_values = [0, 1]
                    if int(value) not in valid_values:
                        return (
                            False,
                            ('The value of Promisc for interface %s can '
                             'only be 0/1.bit_length' % key)
                            )

                elif field == 'nic':
                    if not value.startswith('eth'):
                        return (
                            False,
                            ('The value of nic for interface %s should start'
                             'with eth' % key)
                            )

            if not content['promisc']:
                for field in normal_fields:
                    value = content[field]
                    if field == 'netmask' and not is_valid_netmask(value):
                        return (False, "Invalid netmask format for interface "
                                " %s: '%s'!" % (key, value))
                    elif not is_valid_ip(value):
                        return (False,
                                "Invalid Ip format for interface %s: '%s'"
                                % (key, value))

            for field in other_fields:
                if field in content and field == 'gateway':
                    value = content[field]
                    if value and not is_valid_gateway(value):
                        return False, "Invalid gateway format '%s'" % value

        return True, 'Valid!'

    def _is_valid_global_config(global_config):
        """Valid the format of 'global' section in config"""

        required_fields = ['nameservers', 'search_path', 'gateway']
        global_keys = global_config.keys()
        for key in required_fields:
            if key not in global_keys:
                error_msg = ("Missing %s in global config of networking config"
                             % key)
                return False, error_msg

            value = global_config[key]
            if not value:
                error_msg = ("Value of %s in global config cannot be None!" %
                             key)
                return False, error_msg

            if key == 'nameservers':
                nameservers = [nameserver for nameserver in value.split(',')
                               if nameserver]
                for nameserver in nameservers:
                    if not is_valid_ip(nameserver):
                        return (
                            False,
                            "The nameserver format is invalid! '%s'" % value
                            )

            elif key == 'gateway' and not is_valid_gateway(value):
                return False, "The gateway format is invalid! '%s'" % value

        return True, 'Valid!'

    #networking_keys = networking.keys()
    is_valid = False
    msg = None
    for nkey in networking:
        if nkey in config:
            content = config[nkey]

            if nkey == 'interfaces':
                is_valid, msg = _is_valid_interfaces_config(content)
            elif nkey == 'global':
                is_valid, msg = _is_valid_global_config(content)

            if not is_valid:
                return is_valid, msg

        else:
            error_msg = "Missing '%s' in networking config!" % nkey
            return False, error_msg

    return True, 'valid!'


def is_valid_partition_config(config):
    """Valid the configuration format"""

    if not config:
        return False, '%s in partition cannot be null!' % config

    return True, 'valid!'


def valid_host_config(config):
    """ valid_format is used to check if the input config is qualified
        the required fields and format.
        The key is the required field and format of the input config
        The value is the validator function name of the config value
    """

    from api import errors
    valid_format = {"/networking/interfaces/management/ip": "is_valid_ip",
                    "/networking/global/gateway": "is_valid_gateway",
                    "/networking/global/nameserver": "",
                    "/networking/global/search_path": "",
                    "/roles": ""}
    flat_config = {}
    flatten_dict(config, flat_config)

    config_keys = flat_config.keys()
    for key in config_keys:
        validator = None
        try:
            validator = valid_format[key]
        except:
            error_msg = ("Cannot find the path '%s'. Please check the keywords"
                         % key)
            raise errors.UserInvalidUsage(error_msg)
        else:
            value = flat_config[key]
            if validator:
                is_valid_format = globals()[validator](value)
                if not is_valid_format:
                    error_msg = "The format '%s' is incorrect!" % value
                    raise errors.UserInvalidUsage(error_msg)


def flatten_dict(dictionary, output, flat_key=""):
    """This function will convert the dictionary into a list
       For example:
       dict = {'a':{'b': 'c'}, 'd': 'e'}  ==>
       list = ['a/b/c', 'd/e']
    """

    keywords = dictionary.keys()
    for key in keywords:
        tmp = '/'.join((flat_key, key))
        if isinstance(dictionary[key], dict):
            flatten_dict(dictionary[key], output, tmp)
        else:
            output[tmp] = dictionary[key]


def update_dict_value(searchkey, newvalue, dictionary):
    """Update dictionary value"""

    keywords = dictionary.keys()
    for key in keywords:
        if key == searchkey:
            dictionary[key] = newvalue
        elif isinstance(dictionary[key], dict):
            update_dict_value(searchkey, newvalue, dictionary[key])
        else:
            continue
