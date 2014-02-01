"""Utils for API usage"""
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


def _is_valid_nameservers(value):
    if value:
        nameservers = value.strip(",").split(",")
        for elem in nameservers:
            if not is_valid_ip(elem):
                return False
    else:
        return False

    return True


def is_valid_security_config(config):
    """Valid the format of security section in config"""
    outer_format = {
        "server_credentials": {}, "service_credentials": {},
        "console_credentials": {}
    }
    inner_format = {
        "username": {}, "password": {}
    }
    valid_outter, err = is_valid_keys(outer_format, config, "Security")
    if not valid_outter:
        return (False, err)

    for key in config:
        content = config[key]
        valid_inner, err = is_valid_keys(inner_format, content, key)
        if not valid_inner:
            return (False, err)

        for sub_key in content:
            if not content[sub_key]:
                return (False, ("The value of %s in %s in security config "
                                "cannot be None!") % (sub_key, key))
    return (True, '')


def is_valid_networking_config(config):
    """Valid the format of networking config"""

    def _is_valid_interfaces_config(interfaces_config):
        """Valid the format of interfaces section in config"""
        interfaces_section = {
            "management": {}, "tenant": {}, "public": {}, "storage": {}
        }
        section = {
            "ip_start": {"req": 1, "validator": is_valid_ip},
            "ip_end": {"req": 1, "validator": is_valid_ip},
            "netmask": {"req": 1, "validator": is_valid_netmask},
            "gateway": {"req": 0, "validator": is_valid_gateway},
            "nic": {},
            "promisc": {}
        }

        # Check if interfaces outer layer keywords
        is_valid_outer, err = is_valid_keys(interfaces_section,
                                            interfaces_config, "interfaces")
        if not is_valid_outer:
            return (False, err)

        promisc_nics = []
        nonpromisc_nics = []

        for key in interfaces_config:
            content = interfaces_config[key]
            is_valid_inner, err = is_valid_keys(section, content, key)
            if not is_valid_inner:
                return (False, err)

            if content["promisc"] not in [0, 1]:
                return (False, ("The value of Promisc in %s section of "
                                "interfaces can only be either 0 or 1!") % key)
            if not content["nic"]:
                return (False, ("The NIC in %s cannot be None!") % key)

            if content["promisc"]:
                if content["nic"] not in nonpromisc_nics:
                    promisc_nics.append(content["nic"])
                    continue
                else:
                    return (False,
                            ("The NIC in %s cannot be assigned in promisc "
                             "and nonpromisc mode at the same time!" % key))
            else:
                if content["nic"] not in promisc_nics:
                    nonpromisc_nics.append(content["nic"])
                else:
                    return (False,
                            ("The NIC in %s cannot be assigned in promisc "
                             "and nonpromisc mode at the same time!" % key))

            # Validate other keywords in the section
            for sub_key in content:
                if sub_key == "promisc" or sub_key == "nic":
                    continue
                value = content[sub_key]
                is_required = section[sub_key]["req"]
                validator = section[sub_key]["validator"]
                if value:
                    if validator and not validator(value):
                        error_msg = "The format of %s in %s is invalid!" % \
                            (sub_key, key)
                        return (False, error_msg)

                elif is_required:
                    return (False,
                            ("%s in %s section in interfaces of networking "
                             "config cannot be None!") % (sub_key, key))

        return (True, '')

    def _is_valid_global_config(global_config):
        """Valid the format of 'global' section in config"""
        global_section = {
            "nameservers": {"req": 1, "validator": _is_valid_nameservers},
            "search_path": {"req": 1, "validator": ""},
            "gateway": {"req": 1, "validator": is_valid_gateway},
            "proxy": {"req": 0, "validator": ""},
            "ntp_server": {"req": 0, "validator": ""}
        }
        is_valid_format, err = is_valid_keys(global_section, global_config,
                                             "global")
        if not is_valid_format:
            return (False, err)

        for key in global_section:
            value = global_config[key]
            is_required = global_section[key]["req"]
            validator = global_section[key]["validator"]

            if value:
                if validator and not validator(value):
                    return (False, ("The format of %s in global section of "
                                    "networking config is invalid!") % key)
            elif is_required:
                return (False, ("The value of %s in global section of "
                                "netowrking config cannot be None!") % key)

        return (True, '')

    networking_config = {
        "interfaces": _is_valid_interfaces_config,
        "global": _is_valid_global_config
    }

    valid_format, err = is_valid_keys(networking_config, config, "networking")
    if not valid_format:
        return (False, err)

    for key in networking_config:
        validator = networking_config[key]
        is_valid, err = validator(config[key])
        if not is_valid:
            return (False, err)

    return (True, '')


def is_valid_partition_config(config):
    """Valid the configuration format"""

    if not config:
        return (False, '%s in partition cannot be null!' % config)

    return (True, '')


def valid_host_config(config):
    """ valid_format is used to check if the input config is qualified
        the required fields and format.
        The key is the required field and format of the input config
        The value is the validator function name of the config value
    """

    from api import errors
    valid_format = {"/networking/interfaces/management/ip": "is_valid_ip",
                    "/networking/interfaces/tenant/ip": "is_valid_ip",
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


def is_valid_keys(expected, input_dict, section=""):
    excepted_keys = set(expected.keys())
    input_keys = set(input_dict.keys())
    if excepted_keys != input_keys:
        invalid_keys = list(excepted_keys - input_keys) if \
            len(excepted_keys) > len(input_keys) else\
            list(input_keys - excepted_keys)
        error_msg = ("Invalid or missing keywords in the %s "
                     "section of networking config. Please check these "
                     "keywords %s") % (section, invalid_keys)
        return (False, error_msg)

    return (True, "")


def is_same_dict_keys(expected_dict, config_dict):

    if not expected_dict or not config_dict:
        return (False, "The Config cannot be None!")

    if expected_dict.viewkeys() == config_dict.viewkeys():
        for expected_key, config_key in zip(expected_dict, config_dict):
            if isinstance(expected_dict[expected_key], str):
                return (True, "")

            is_same, err = is_same_dict_keys(expected_dict[expected_key],
                                             config_dict[config_key])
            if not is_same:
                return (False, err)
        return (True, "")

    if len(expected_dict) >= len(config_dict):
        invalid_list = list(expected_dict.viewkeys() - config_dict.viewkeys())
    else:
        invalid_list = list(config_dict.viewkeys() - expected_dict.viewkeys())
    return (False, "Invalid key(s) %r in the config" % invalid_list)
