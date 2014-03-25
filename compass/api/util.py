# Copyright 2014 Huawei Technologies Co. Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utils for API usage."""
import netaddr
import re

from flask.ext.restful import Api
from flask import make_response
import simplejson as json

from compass.api import app


API = Api(app)


def make_json_response(status_code, data):
    """Wrap json format to the reponse object."""

    result = json.dumps(data, indent=4)
    resp = make_response(result, status_code)
    resp.headers['Content-type'] = 'application/json'
    return resp


def make_csv_response(status_code, csv_data, fname):
    """Wrap CSV format to the reponse object."""
    fname = '.'.join((fname, 'csv'))
    resp = make_response(csv_data, status_code)
    resp.mimetype = 'text/csv'
    resp.headers['Content-Disposition'] = 'attachment; filename="%s"' % fname
    return resp


def add_resource(*args, **kwargs):
    """Add resource."""
    API.add_resource(*args, **kwargs)


def is_valid_ip(ip_address):
    """Valid the format of an Ip address."""
    if not ip_address:
        return False

    regex = (r'^(([0-9]|[1-9][0-9]|1[0-9]{2}|[1-2][0-4][0-9]|25[0-5])\.)'
             r'{3}'
             r'([0-9]|[1-9][0-9]|1[0-9]{2}|[1-2][0-4][0-9]|25[0-5])')

    if re.match(regex, ip_address):
        return True

    return False


def is_valid_ipnetowrk(ip_network):
    """Valid the format of an Ip network."""

    if not ip_network:
        return False

    regex = (r'^(([0-9]|[1-9][0-9]|1[0-9]{2}|[1-2][0-4][0-9]|25[0-5])\.)'
             r'{3}'
             r'([0-9]|[1-9][0-9]|1[0-9]{2}|[1-2][0-4][0-9]|25[0-5])'
             r'((\/[0-9]|\/[1-2][0-9]|\/[1-3][0-2]))$')

    if re.match(regex, ip_network):
        return True
    return False


def is_valid_netmask(ip_addr):
    """Valid the format of a netmask."""
    try:
        ip_address = netaddr.IPAddress(ip_addr)
        return ip_address.is_netmask()

    except Exception:
        return False


def is_valid_gateway(ip_addr):
    """Valid the format of gateway."""

    invalid_ip_prefix = ['0', '224', '169', '127']
    try:
        # Check if ip_addr is an IP address and not start with 0
        ip_addr_prefix = ip_addr.split('.')[0]
        if is_valid_ip(ip_addr) and ip_addr_prefix not in invalid_ip_prefix:
            ip_address = netaddr.IPAddress(ip_addr)
            if not ip_address.is_multicast():
                # Check if ip_addr is not multicast and reserved IP
                return True
        return False
    except Exception:
        return False


def _is_valid_nameservers(value):
    """Valid the format of nameservers."""
    if value:
        nameservers = value.strip(",").split(",")
        for elem in nameservers:
            if not is_valid_ip(elem):
                return False
    else:
        return False

    return True


def is_valid_security_config(config):
    """Valid the format of security section in config."""
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
    """Valid the format of networking config."""

    def _is_valid_interfaces_config(interfaces_config):
        """Valid the format of interfaces section in config."""
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
        """Valid the format of 'global' section in config."""
        global_section = {
            "nameservers": {"req": 1, "validator": _is_valid_nameservers},
            "search_path": {"req": 1, "validator": ""},
            "gateway": {"req": 1, "validator": is_valid_gateway},
            "proxy": {"req": 0, "validator": ""},
            "ntp_server": {"req": 0, "validator": ""},
            "ha_vip": {"req": 0, "validator": is_valid_ip}
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
    """Valid the configuration format."""

    if not config:
        return (False, '%s in partition cannot be null!' % config)

    return (True, '')


def valid_host_config(config):
    """Valid the host configuration format.

       .. note::
          Valid_format is used to check if the input config is qualified
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
        except Exception:
            continue
        else:
            value = flat_config[key]
            if validator:
                is_valid_format = globals()[validator](value)
                if not is_valid_format:
                    error_msg = "The format '%s' is incorrect!" % value
                    raise errors.UserInvalidUsage(error_msg)


def flatten_dict(dictionary, output, flat_key=""):
    """This function will convert the dictionary into a flatten dict.

       .. note::
          For example:
          dict = {'a':{'b': 'c'}, 'd': 'e'}  ==>
          flatten dict = {'a/b': 'c', 'd': 'e'}
    """

    keywords = dictionary.keys()
    for key in keywords:
        tmp = '/'.join((flat_key, key))
        if isinstance(dictionary[key], dict):
            flatten_dict(dictionary[key], output, tmp)
        else:
            output[tmp] = dictionary[key]


def update_dict_value(searchkey, dictionary):
    """Update dictionary value."""

    keywords = dictionary.keys()
    for key in keywords:
        if key == searchkey:
            if isinstance(dictionary[key], str):
                dictionary[key] = ''
            elif isinstance(dictionary[key], list):
                dictionary[key] = []

        elif isinstance(dictionary[key], dict):
            update_dict_value(searchkey, dictionary[key])
        else:
            continue


def is_valid_keys(expected, input_dict, section=""):
    """Validate keys."""
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


def get_col_val_from_dict(result, data):
    """Convert a dict's values to a list.

    :param result: a list of values for each column
    :param data: input data

       .. note::
          for example:
          data = {"a": {"b": {"c": 1}, "d": 2}}
          the result will be  [1, 2]
    """
    if not isinstance(data, dict):
        data = str(data) if str(data) else 'None'
        result.append(data)
        return

    for key in data:
        get_col_val_from_dict(result, data[key])


def get_headers_from_dict(headers, colname, data):
    """Convert a column which value is dict to a list of column name and keys.

       .. note::
          nested keys in dict will be joined by '.' as a column name in CSV.
          for example:
          the column name is 'config_data', and
          the value is {"a": {"b": {"c": 1}, "d": 2}}
          then headers will be ['config_data.a.b.c', 'config_data.a.d']

    :param headers: the result list to hold dict keys
    :param colname: the column name
    :param data: input data

    """
    if not colname:
        raise "colname cannot be None!"

    if not isinstance(data, dict):
        headers.append(colname)
        return

    for key in data:
        tmp_header = '.'.join((colname, key))
        get_headers_from_dict(headers, tmp_header, data[key])
