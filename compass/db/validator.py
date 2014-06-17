# Copyright 2014 Huawei Technologies Co. Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Validator methods."""
import netaddr
import re
import socket

from compass.utils import setting_wrapper as setting
from compass.utils import util


def is_valid_ip(name, ip_addr):
    """Valid the format of an IP address."""
    try:
        netaddr.IPAddress(ip_addr)
    except Exception:
        return False
    return True


def is_valid_network(name, ip_network):
    """Valid the format of an Ip network."""
    try:
        netaddr.IPNetwork(ip_network)
    except Exception:
        return False
    return False


def is_valid_netmask(name, ip_addr):
    """Valid the format of a netmask."""
    if not is_valid_ip(ip_addr):
        return False
    ip = netaddr.IPAddress(ip_addr)
    if ip.is_netmask():
        return True
    else:
        return False


def is_valid_gateway(name, ip_addr):
    """Valid the format of gateway."""
    if not is_valid_ip(ip_addr):
        return False
    ip = netaddr.IPAddress(ip_addr)
    if ip.is_private() or ip.is_public():
        return True
    else:
        return False


def is_valid_dns(name, dns):
    """Valid the format of DNS."""
    if is_valid_ip(dns):
        return True
    try:
        socket.gethostbyname_ex(dns)
    except Exception:
        return False
    return True


def is_valid_username(name, username):
    """Valid the format of username."""
    return bool(username)


def is_valid_password(name, password):
    """Valid the format of password."""
    return bool(password)


def is_valid_partition(name, partition):
    """Valid the format of partition name."""
    if name != 'swap' and not name.startswith('/'):
        return False
    if 'size' not in partition and 'percentage' not in partition:
        return False
    return True


def is_valid_percentage(name, percentage):
    """Valid the percentage."""
    return 0 <= percentage <= 100


def is_valid_port(name, port):
    """Valid the format of port."""
    return 0 < port < 65536


def is_valid_size(name, size):
    if re.match(r'(\d+)(K|M|G|T)?', size):
        return True
    return False


VALIDATOR_GLOBALS = globals()
VALIDATOR_LOCALS = locals()
VALIDATOR_CONFIGS = util.load_configs(
    setting.VALIDATOR_DIR,
    config_name_suffix='.py',
    env_globals=VALIDATOR_GLOBALS,
    env_locals=VALIDATOR_LOCALS
)
for validator_config in VALIDATOR_CONFIGS:
    VALIDATOR_LOCALS.update(validator_config)
