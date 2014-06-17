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

"""Module to provider util functions in all compass code

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import copy
import crypt
import datetime
import re
import sys


def parse_datetime(date_time, exception_class=Exception):
    """Parse datetime str to get datetime object."""
    try:
        return datetime.datetime.strptime(
            date_time, '%Y-%m-%d %H:%M:%S'
        )
    except Exception:
        raise exception_class(
            'date time %s format is invalid' % date_time
        )


def parse_datetime_range(date_time_range, exception_class=Exception):
    """parse datetime range str to pair of datetime objects."""
    try:
        start, end = date_time_range.split(',')
    except Exception:
        raise exception_class(
            'there is no `,` in date time range %s' % date_time_range
        )
    if start:
        start_datetime = parse_datetime(start, exception_class)
    else:
        start_datetime = None
    if end:
        end_datetime = parse_datetime(end, exception_class)
    else:
        end_datetime = None
    return start_datetime, end_datetime


def format_datetime(date_time):
    """Generate string from datetime object."""
    return date_time.strftime("%Y-%m-%d %H:%M:%S")


def merge_dict(lhs, rhs, override=True):
    """Merge nested right dict into left nested dict recursively.

    :param lhs: dict to be merged into.
    :type lhs: dict
    :param rhs: dict to merge from.
    :type rhs: dict
    :param override: the value in rhs overide the value in left if True.
    :type override: str

    :raises: TypeError if lhs or rhs is not a dict.
    """
    if not rhs:
        return

    if not isinstance(lhs, dict):
        raise TypeError('lhs type is %s while expected is dict' % type(lhs),
                        lhs)

    if not isinstance(rhs, dict):
        raise TypeError('rhs type is %s while expected is dict' % type(rhs),
                        rhs)

    for key, value in rhs.items():
        if (
            isinstance(value, dict) and key in lhs and
            isinstance(lhs[key], dict)
        ):
            merge_dict(lhs[key], value, override)
        else:
            if override or key not in lhs:
                lhs[key] = copy.deepcopy(value)


def encrypt(value, crypt_method=None):
    """Get encrypted value."""
    if not crypt_method:
        if hasattr(crypt, 'METHOD_MD5'):
            crypt_method = crypt.METHOD_MD5
        else:
            # for python2.7, copy python2.6 METHOD_MD5 logic here.
            from random import choice
            import string

            _saltchars = string.ascii_letters + string.digits + './'

            def _mksalt():
                """generate salt."""
                salt = '$1$'
                salt += ''.join(choice(_saltchars) for _ in range(8))
                return salt

            crypt_method = _mksalt()

    return crypt.crypt(value, crypt_method)


def parse_time_interval(time_interval_str):
    if not time_interval_str:
        return 0

    time_interval_tuple = [
        time_interval_element
        for time_interval_element in time_interval_str.split(' ')
        if time_interval_element
    ]
    time_interval_dict = {}
    time_interval_unit_mapping = {
        'd': 'days',
        'w': 'weeks',
        'h': 'hours',
        'm': 'minutes',
        's': 'seconds'
    }
    for time_interval_element in time_interval_tuple:
        mat = re.match(r'^([+-]?\d+)(w|d|h|m|s).*', time_interval_element)
        if not mat:
            continue

        time_interval_value = int(mat.group(1))
        time_interval_unit = time_interval_unit_mapping[mat.group(2)]
        time_interval_dict[time_interval_unit] = (
            time_interval_dict.get(time_interval_unit, 0) + time_interval_value
        )

    time_interval = datetime.timedelta(**time_interval_dict)
    if sys.version_info[0:2] > (2, 6):
        return time_interval.total_seconds()
    else:
        return (
            time_interval.microseconds + (
                time_interval.seconds + time_interval.days * 24 * 3600
            ) * 1e6
        ) / 1e6

def order_keys(keys, orders):
    """Get ordered keys.

    :param keys: keys to be sorted.
    :type keys: list of str
    :param orders: the order of the keys. '.' is all other keys not in order.
    :type orders: list of str.

    :returns: keys as list sorted by orders.

    :raises: TypeError if keys or orders is not list.
    """

    if not isinstance(keys, list):
        raise TypeError('keys %s type should be list' % keys)

    if not isinstance(orders, list):
        raise TypeError('orders ^s type should be list' % orders)

    found_dot = False
    pres = []
    posts = []
    for order in orders:
        if order == '.':
            found_dot = True
        else:
            if found_dot:
                posts.append(order)
            else:
                pres.append(order)

    return ([pre for pre in pres if pre in keys] +
            [key for key in keys if key not in orders] +
            [post for post in posts if post in keys])


def is_instance(instance, expected_types):
    """Check instance type is in one of expected types.

    :param instance: instance to check the type.
    :param expected_types: types to check if instance type is in them.
    :type expected_types: list of type

    :returns: True if instance type is in expect_types.
    """
    for expected_type in expected_types:
        if isinstance(instance, expected_type):
            return True

    return False


def flat_lists_with_possibility(lists):
    """Return list of item from list of list of identity item.

    :param lists: list of list of identity item.

    :returns: list.

    .. note::
       For each first k elements in the returned list, it should be the k
       most possible items. e.g. the input lists is
       ['a', 'a', 'a', 'a'], ['b', 'b'], ['c'],
       the expected output is ['a', 'b', 'c', 'a', 'a', 'b', 'a'].
    """
    lists = copy.deepcopy(lists)
    lists = sorted(lists, key=len, reverse=True)
    list_possibility = []
    max_index = 0
    total_elements = 0
    possibilities = []
    for items in lists:
        list_possibility.append(0.0)
        length = len(items)
        if length > 0:
            total_elements += length
            possibilities.append(1.0 / length)
        else:
            possibilities.append(0.0)

    output = []
    while total_elements > 0:
        if not lists[max_index]:
            list_possibility[max_index] -= total_elements
        else:
            list_possibility[max_index] -= possibilities[max_index]
            element = lists[max_index].pop(0)
            output.append(element)
            total_elements -= 1
        max_index = list_possibility.index(max(list_possibility))

    return output


def pretty_print(*contents):
    """pretty print contents."""
    if len(contents) == 0:
        print ""
    else:
        print "\n".join(content for content in contents)


def get_clusters_from_str(clusters_str):
    """get clusters from string."""
    clusters = {}
    for cluster_and_hosts in clusters_str.split(';'):
        if not cluster_and_hosts:
            continue

        if ':' in cluster_and_hosts:
            cluster_str, hosts_str = cluster_and_hosts.split(
                ':', 1)
        else:
            cluster_str = cluster_and_hosts
            hosts_str = ''

        hosts = [
            host for host in hosts_str.split(',')
            if host
        ]
        clusters[cluster_str] = hosts

    return clusters


def _get_switch_ips(switch_config):
    """Helper function to get switch ips."""
    ips = []
    blocks = switch_config['switch_ips'].split('.')
    ip_blocks_list = []
    for block in blocks:
        ip_blocks_list.append([])
        sub_blocks = block.split(',')
        for sub_block in sub_blocks:
            if not sub_block:
                continue

            if '-' in sub_block:
                start_block, end_block = sub_block.split('-', 1)
                start_block = int(start_block)
                end_block = int(end_block)
                if start_block > end_block:
                    continue

                ip_block = start_block
                while ip_block <= end_block:
                    ip_blocks_list[-1].append(str(ip_block))
                    ip_block += 1

            else:
                ip_blocks_list[-1].append(sub_block)

    ip_prefixes = [[]]
    for ip_blocks in ip_blocks_list:
        prefixes = []
        for ip_block in ip_blocks:
            for prefix in ip_prefixes:
                prefixes.append(prefix + [ip_block])

        ip_prefixes = prefixes

    for prefix in ip_prefixes:
        if not prefix:
            continue

        ips.append('.'.join(prefix))

    return ips


def _get_switch_filter_ports(switch_config):
    """Helper function to get switch filter ports."""
    port_pat = re.compile(r'(\D*)(\d+(?:-\d+)?)')
    filter_ports = []
    for port_range in switch_config['filter_ports'].split(','):
        if not port_range:
            continue

        mat = port_pat.match(port_range)
        if not mat:
            filter_ports.append(port_range)
        else:
            port_prefix = mat.group(1)
            port_range = mat.group(2)
            if '-' in port_range:
                start_port, end_port = port_range.split('-', 1)
                start_port = int(start_port)
                end_port = int(end_port)
                if start_port > end_port:
                    continue

                port = start_port
                while port <= end_port:
                    filter_ports.append('%s%s' % (port_prefix, port))
                    port += 1

            else:
                filter_ports.append('%s%s' % (port_prefix, port_range))

    return filter_ports


def get_switch_filters(switch_configs):
    """get switch filters."""
    switch_filters = []
    for switch_config in switch_configs:
        ips = _get_switch_ips(switch_config)
        filter_ports = _get_switch_filter_ports(switch_config)

        for ip_addr in ips:
            for filter_port in filter_ports:
                switch_filters.append(
                    {'ip': ip_addr, 'filter_port': filter_port})

    return switch_filters


def get_switch_machines_from_file(filename):
    """get switch machines from file."""
    switches = []
    switch_machines = {}
    with open(filename) as switch_file:
        for line in switch_file:
            line = line.strip()
            if not line:
                # ignore empty line
                continue

            if line.startswith('#'):
                # ignore comments
                continue

            columns = [column for column in line.split(',')]
            if not columns:
                # ignore empty line
                continue

            if columns[0] == 'switch':
                (switch_ip, switch_vendor, switch_version,
                 switch_community, switch_state) = columns[1:]
                switches.append({
                    'ip': switch_ip,
                    'vendor_info': switch_vendor,
                    'credential': {
                        'version': switch_version,
                        'community': switch_community,
                    },
                    'state': switch_state,
                })
            elif columns[0] == 'machine':
                switch_ip, switch_port, vlan, mac = columns[1:]
                switch_machines.setdefault(switch_ip, []).append({
                    'mac': mac,
                    'port': switch_port,
                    'vlan': int(vlan)
                })

    return (switches, switch_machines)


def get_properties_from_str(properties_str):
    """get matching properties from string."""
    properties = {}
    if not properties_str:
        return properties

    for property_str in properties_str.split(','):
        if not property_str:
            # ignore empty str
            continue

        property_name, property_value = property_str.split('=', 1)
        properties[property_name] = property_value

    return properties


def get_properties_name_from_str(properties_name_str):
    """get properties name to print from string."""
    properties_name = []
    for property_name in properties_name_str.split(','):
        if not property_name:
            # ignore empty str
            continue

        properties_name.append(property_name)

    return properties_name


def print_properties(properties):
    """print properties."""
    print '-----------------------------------------------'
    for property_item in properties:
        property_pairs = []
        for property_name, property_value in property_item.items():
            property_pairs.append('%s=%s' % (property_name, property_value))

        print ','.join(property_pairs)

    print '-----------------------------------------------'
