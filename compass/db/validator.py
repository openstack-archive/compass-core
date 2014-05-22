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

"""Validator methods. Please note that functions below may not the best way
   to do the validation.
"""
# TODO(xiaodong): please refactor/rewrite the following functions as necessary
import netaddr
import re
import socket


def is_valid_ip(ip_addr):
    """Valid the format of an IP address."""
    if not ip_addr:
        return False

    try:
        socket.inet_aton(ip_addr)
    except socket.error:
        return False

    return True


def is_valid_ipNetowrk(ip_network):
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
    if not ip_addr:
        return False

    try:
        ip_address = netaddr.IPAddress(ip_addr)
        return ip_address.is_netmask()

    except Exception:
        return False


def is_valid_gateway(ip_addr):
    """Valid the format of gateway."""

    if not ip_addr:
        return False

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


def is_valid_dnsServer(dns):
    """Valid the format of DNS."""
    if dns and not is_valid_ip(dns):
        return False

    return True
