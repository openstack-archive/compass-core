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
import logging
import netaddr
import re
import socket

from compass.utils import setting_wrapper as setting
from compass.utils import util


def is_valid_ip(name, ip_addr, **kwargs):
    """Valid the format of an IP address."""
    if isinstance(ip_addr, list):
        return all([
            is_valid_ip(name, item, **kwargs) for item in ip_addr
        ])
    try:
        netaddr.IPAddress(ip_addr)
    except Exception:
        logging.debug('%s invalid ip addr %s', name, ip_addr)
        return False
    return True


def is_valid_network(name, ip_network, **kwargs):
    """Valid the format of an Ip network."""
    if isinstance(ip_network, list):
        return all([
            is_valid_network(name, item, **kwargs) for item in ip_network
        ])
    try:
        netaddr.IPNetwork(ip_network)
    except Exception:
        logging.debug('%s invalid network %s', name, ip_network)
        return False
    return True


def is_valid_netmask(name, ip_addr, **kwargs):
    """Valid the format of a netmask."""
    if isinstance(ip_addr, list):
        return all([
            is_valid_netmask(name, item, **kwargs) for item in ip_addr
        ])
    if not is_valid_ip(ip_addr):
        return False
    ip = netaddr.IPAddress(ip_addr)
    if ip.is_netmask():
        return True
    logging.debug('%s invalid netmask %s', name, ip_addr)
    return False


def is_valid_gateway(name, ip_addr, **kwargs):
    """Valid the format of gateway."""
    if isinstance(ip_addr, list):
        return all([
            is_valid_gateway(name, item, **kwargs) for item in ip_addr
        ])
    if not is_valid_ip(ip_addr):
        return False
    ip = netaddr.IPAddress(ip_addr)
    if ip.is_private() or ip.is_public():
        return True
    logging.debug('%s invalid gateway %s', name, ip_addr)
    return False


def is_valid_dns(name, dns, **kwargs):
    """Valid the format of DNS."""
    if isinstance(dns, list):
        return all([is_valid_dns(name, item, **kwargs) for item in dns])
    if is_valid_ip(dns):
        return True
    try:
        socket.gethostbyname_ex(dns)
    except Exception:
        logging.debug('%s invalid dns name %s', name, dns)
        return False
    return True


def is_valid_url(name, url, **kwargs):
    """Valid the format of url."""
    if isinstance(url, list):
        return all([
            is_valid_url(name, item, **kwargs) for item in url
        ])
    if re.match(
        r'^(http|https|ftp)://([0-9A-Za-z_-]+)(\.[0-9a-zA-Z_-]+)*'
        r'(:\d+)?(/[0-9a-zA-Z_-]+)*$',
        url
    ):
        return True
    logging.debug(
        '%s invalid url %s', name, url
    )
    return False


def is_valid_domain(name, domain, **kwargs):
    """Validate the format of domain."""
    if isinstance(domain, list):
        return all([
            is_valid_domain(name, item, **kwargs) for item in domain
        ])
    if re.match(
        r'^([0-9a-zA-Z_-]+)(\.[0-9a-zA-Z_-]+)*$',
        domain
    ):
        return True
    logging.debug(
        '%s invalid domain %s', name, domain
    )
    return False


def is_valid_username(name, username, **kwargs):
    """Valid the format of username."""
    if bool(username):
        return True
    logging.debug(
        '%s username is empty', name
    )


def is_valid_password(name, password, **kwargs):
    """Valid the format of password."""
    if bool(password):
        return True
    logging.debug('%s password is empty', name)
    return False


def is_valid_partition(name, partition, **kwargs):
    """Valid the format of partition name."""
    if name != 'swap' and not name.startswith('/'):
        logging.debug(
            '%s is not started with / or swap', name
        )
        return False
    if 'size' not in partition and 'percentage' not in partition:
        logging.debug(
            '%s partition does not contain sie or percentage',
            name
        )
        return False
    return True


def is_valid_percentage(name, percentage, **kwargs):
    """Valid the percentage."""
    if 0 <= percentage <= 100:
        return True
    logging.debug('%s invalid percentage %s', name, percentage)


def is_valid_port(name, port, **kwargs):
    """Valid the format of port."""
    if 0 < port < 65536:
        return True
    logging.debug('%s invalid port %s', name, port)


def is_valid_size(name, size, **kwargs):
    if re.match(r'^(\d+)(K|M|G|T)$', size):
        return True
    logging.debug('%s invalid size %s', name, size)
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
