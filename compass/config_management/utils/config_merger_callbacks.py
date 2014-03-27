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

"""ConfigMerger Callbacks module.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import copy
import itertools
import logging
import netaddr
import re

from compass.utils import util


def _get_role_bundle_mapping(roles, bundles):
    """Get role bundles.
    """
    bundle_mapping = {}
    for role in roles:
        bundle_mapping[role] = role

    for bundle in bundles:
        bundled_role = None
        for role in bundle:
            if role not in roles:
                continue
            while role != bundle_mapping[role]:
                role = bundle_mapping[role]
            if not bundled_role:
                bundled_role = role
            else:
                bundle_mapping[role] = bundled_role

    role_bundles = {}
    for role in roles:
        bundled_role = role
        while bundled_role != bundle_mapping[bundled_role]:
            bundled_role = bundle_mapping[bundled_role]
        bundle_mapping[role] = bundled_role
        role_bundles.setdefault(bundled_role, set()).add(role)

    logging.debug('bundle_mapping is %s', bundle_mapping)
    logging.debug('role_bundles is %s', role_bundles)
    return bundle_mapping, role_bundles


def _get_bundled_exclusives(exclusives, bundle_mapping):
    """Get bundled exclusives."""
    bundled_exclusives = set()
    for exclusive in exclusives:
        if exclusive not in bundle_mapping:
            logging.error(
                'exclusive role %s did not found in roles %s',
                exclusive, bundle_mapping.keys())
            continue
        bundled_exclusives.add(bundle_mapping[exclusive])

    logging.debug('bundled exclusives: %s', bundled_exclusives)
    return bundled_exclusives


def _get_max(lhs, rhs):
    """Get max value."""
    if lhs < 0:
        return lhs

    if rhs < 0:
        return rhs

    return max(lhs, rhs)


def _get_min(lhs, rhs):
    """Get min value."""
    if lhs < 0:
        return rhs

    if rhs < 0:
        return lhs

    return min(lhs, rhs)


def _dec_max_min(value):
    """dec max and min value."""
    if value > 0:
        return value - 1
    else:
        return value


def _get_bundled_max_mins(maxs, mins, default_max, default_min, role_bundles):
    """Get max and mins for each bundled role."""
    bundled_maxs = {}
    bundled_mins = {}
    default_min = max(default_min, 0)
    default_max = _get_max(default_max, default_min)

    for bundled_role, roles in role_bundles.items():
        bundled_min = None
        bundled_max = None
        for role in roles:
            new_max = maxs.get(role, default_max)
            new_min = mins.get(role, default_min)
            if bundled_min is None:
                bundled_min = new_min
            else:
                bundled_min = min(bundled_min, max(new_min, 0))

            if bundled_max is None:
                bundled_max = new_max
            else:
                bundled_max = _get_min(
                    bundled_max, _get_max(new_max, bundled_min))

        if bundled_min is None:
            bundled_min = default_min

        if bundled_max is None:
            bundled_max = max(default_max, bundled_min)

        bundled_mins[bundled_role] = bundled_min
        bundled_maxs[bundled_role] = bundled_max

    logging.debug('bundled_maxs are %s', bundled_maxs)
    logging.debug('bundled_mins are %s', bundled_mins)
    return bundled_maxs, bundled_mins


def _update_assigned_roles(lower_refs, to_key, bundle_mapping,
                           role_bundles, bundled_maxs, bundled_mins):
    """Update bundled maxs/mins and assign roles to each unassigned host."""
    lower_roles = {}
    unassigned_hosts = []
    for lower_key, lower_ref in lower_refs.items():
        roles_per_host = lower_ref.get(to_key, [])
        roles = set()
        bundled_roles = set()
        for role in roles_per_host:
            if role in bundle_mapping:
                bundled_role = bundle_mapping[role]
                bundled_roles.add(bundled_role)
                roles |= set(role_bundles[bundled_role])
            else:
                roles.add(role)

        for bundled_role in bundled_roles:
            bundled_maxs[bundled_role] = _dec_max_min(
                bundled_maxs[bundled_role])
            bundled_mins[bundled_role] = _dec_max_min(
                bundled_mins[bundled_role])

        lower_roles[lower_key] = list(roles)
        if not roles:
            unassigned_hosts.append(lower_key)

    logging.debug('assigned roles: %s', lower_roles)
    logging.debug('unassigned_hosts: %s', unassigned_hosts)
    logging.debug('bundled maxs for unassigned hosts: %s', bundled_maxs)
    logging.debug('bundled mins for unassigned hosts: %s', bundled_mins)
    return lower_roles, unassigned_hosts


def _update_exclusive_roles(bundled_exclusives, lower_roles,
                            unassigned_hosts, bundled_maxs,
                            bundled_mins, role_bundles):
    """Assign exclusive roles to hosts."""
    for bundled_exclusive in bundled_exclusives:
        while bundled_mins[bundled_exclusive] > 0:
            if not unassigned_hosts:
                raise ValueError('no enough unassigned hosts for exlusive %s',
                                 bundled_exclusive)
            host = unassigned_hosts.pop(0)
            bundled_mins[bundled_exclusive] = _dec_max_min(
                bundled_mins[bundled_exclusive])
            bundled_maxs[bundled_exclusive] = _dec_max_min(
                bundled_maxs[bundled_exclusive])
            lower_roles[host] = list(role_bundles[bundled_exclusive])

        del role_bundles[bundled_exclusive]

    logging.debug('assigned roles after assigning exclusives: %s', lower_roles)
    logging.debug('unassigned_hosts after assigning exclusives: %s',
                  unassigned_hosts)
    logging.debug('bundled maxs after assigning exclusives: %s', bundled_maxs)
    logging.debug('bundled mins after assigning exclusives: %s', bundled_mins)


def _assign_roles_by_mins(role_bundles, lower_roles, unassigned_hosts,
                          bundled_maxs, bundled_mins):
    """Assign roles to hosts by min restriction."""
    available_hosts = copy.deepcopy(unassigned_hosts)
    for bundled_role, roles in role_bundles.items():
        while bundled_mins[bundled_role] > 0:
            if not available_hosts:
                raise ValueError('no enough available hosts to assign to %s',
                                 bundled_role)

            host = available_hosts.pop(0)
            available_hosts.append(host)
            if host in unassigned_hosts:
                unassigned_hosts.remove(host)

            bundled_mins[bundled_role] = _dec_max_min(
                bundled_mins[bundled_role])
            bundled_maxs[bundled_role] = _dec_max_min(
                bundled_maxs[bundled_role])
            if host not in lower_roles:
                lower_roles[host] = list(roles)
            elif set(lower_roles[host]) & roles:
                duplicated_roles = set(lower_roles[host]) & roles
                raise ValueError(
                    'duplicated roles %s on %s' % (duplicated_roles, host))
            else:
                lower_roles[host].extend(list(roles))

    logging.debug('assigned roles after assigning mins: %s', lower_roles)
    logging.debug('unassigned_hosts after assigning mins: %s',
                  unassigned_hosts)
    logging.debug('bundled maxs after assigning mins: %s', bundled_maxs)


def _assign_roles_by_maxs(role_bundles, lower_roles, unassigned_hosts,
                          bundled_maxs):
    """Assign roles to host by max restriction."""
    available_lists = []
    default_roles_lists = []
    for bundled_role in role_bundles.keys():
        if bundled_maxs[bundled_role] > 0:
            available_lists.append(
                [bundled_role] * bundled_maxs[bundled_role])
        elif bundled_maxs[bundled_role] < 0:
            default_roles_lists.append(
                [bundled_role] * (-bundled_maxs[bundled_role]))

    available_list = util.flat_lists_with_possibility(available_lists)

    for bundled_role in available_list:
        if not unassigned_hosts:
            break

        host = unassigned_hosts.pop(0)
        lower_roles[host] = list(role_bundles[bundled_role])

    logging.debug('assigned roles after assigning max: %s', lower_roles)
    logging.debug('unassigned_hosts after assigning maxs: %s',
                  unassigned_hosts)

    default_roles = util.flat_lists_with_possibility(
        default_roles_lists)

    if default_roles:
        default_iter = itertools.cycle(default_roles)
        while unassigned_hosts:
            host = unassigned_hosts.pop(0)
            bundled_role = default_iter.next()
            lower_roles[host] = list(role_bundles[bundled_role])

    logging.debug('assigned roles are %s', lower_roles)
    logging.debug('unassigned hosts: %s', unassigned_hosts)


def _sort_roles(lower_roles, roles):
    """Sort roles with the same order as in all roles."""
    for lower_key, lower_value in lower_roles.items():
        updated_roles = []
        for role in roles:
            if role in lower_value:
                updated_roles.append(role)

        for role in lower_value:
            if role not in updated_roles:
                logging.debug('found role %s not in roles %s', role, roles)
                updated_roles.append(role)

        lower_roles[lower_key] = updated_roles


def assign_roles(_upper_ref, _from_key, lower_refs, to_key,
                 roles=[], maxs={}, mins={}, default_max=-1,
                 default_min=0, exclusives=[], bundles=[], **_kwargs):
    """Assign roles to lower configs."""
    logging.debug(
        'assignRoles with roles=%s, maxs=%s, mins=%s, '
        'default_max=%s, default_min=%s, exclusives=%s, bundles=%s',
        roles, maxs, mins, default_max,
        default_min, exclusives, bundles)
    bundle_mapping, role_bundles = _get_role_bundle_mapping(roles, bundles)
    bundled_exclusives = _get_bundled_exclusives(exclusives, bundle_mapping)
    bundled_maxs, bundled_mins = _get_bundled_max_mins(
        maxs, mins, default_max, default_min, role_bundles)

    lower_roles, unassigned_hosts = _update_assigned_roles(
        lower_refs, to_key, bundle_mapping, role_bundles,
        bundled_maxs, bundled_mins)
    if not unassigned_hosts:
        logging.debug(
            'there is not unassigned hosts, assigned roles by host is: %s',
            lower_roles)
    else:
        _update_exclusive_roles(
            bundled_exclusives, lower_roles, unassigned_hosts,
            bundled_maxs, bundled_mins, role_bundles)
        _assign_roles_by_mins(
            role_bundles, lower_roles, unassigned_hosts,
            bundled_maxs, bundled_mins)
        _assign_roles_by_maxs(
            role_bundles, lower_roles, unassigned_hosts,
            bundled_maxs)

    _sort_roles(lower_roles, roles)

    return lower_roles


def assign_roles_by_host_numbers(upper_ref, from_key, lower_refs, to_key,
                                 policy_by_host_numbers={}, default={},
                                 **kwargs):
    """Assign roles by role assign policy."""
    host_numbers = str(len(lower_refs))
    policy_kwargs = copy.deepcopy(kwargs)
    util.merge_dict(policy_kwargs, default)
    if host_numbers in policy_by_host_numbers:
        util.merge_dict(policy_kwargs, policy_by_host_numbers[host_numbers])
    else:
        logging.debug('didnot find policy %s by host numbers %s',
                      policy_by_host_numbers, host_numbers)

    return assign_roles(upper_ref, from_key, lower_refs,
                        to_key, **policy_kwargs)


def has_intersection(upper_ref, from_key, _lower_refs, _to_key,
                     lower_values={}, **_kwargs):
    """Check if upper config has intersection with lower values."""
    has = {}
    for lower_key, lower_value in lower_values.items():
        values = set(lower_value)
        intersection = values.intersection(set(upper_ref.config))
        logging.debug(
            'lower_key %s values %s intersection'
            'with from_key %s value %s: %s',
            lower_key, values, from_key, upper_ref.config, intersection)
        if intersection:
            has[lower_key] = True
        else:
            has[lower_key] = False

    return has


def get_intersection(upper_ref, from_key, _lower_refs, _to_key,
                     lower_values={}, **_kwargs):
    """Get intersection of upper config and  lower values."""
    intersections = {}
    for lower_key, lower_value in lower_values.items():
        values = set(lower_value)
        intersection = values.intersection(set(upper_ref.config))
        logging.debug(
            'lower_key %s values %s intersection'
            'with from_key %s value %s: %s',
            lower_key, values, from_key, upper_ref.config, intersection)
        if intersection:
            intersections[lower_key] = list(intersection)

    return intersections


def assign_ips(_upper_ref, _from_key, lower_refs, to_key,
               ip_start='192.168.0.1', ip_end='192.168.0.254',
               **_kwargs):
    """Assign ips to hosts' configurations."""
    if not ip_start or not ip_end:
        raise ValueError(
            'ip_start %s or ip_end %s is empty' % (ip_start, ip_end))

    if not re.match(r'^\d+\.\d+\.\d+\.\d+$', ip_start):
        raise ValueError(
            'ip_start %s formmat is not correct' % ip_start)

    if not re.match(r'^\d+\.\d+\.\d+\.\d+$', ip_end):
        raise ValueError(
            'ip_end %s format is not correct' % ip_end)

    host_ips = {}
    unassigned_hosts = []
    try:
        ips = netaddr.IPSet(netaddr.IPRange(ip_start, ip_end))
    except Exception:
        raise ValueError(
            'failed to create ip block [%s, %s]' % (ip_start, ip_end))

    for lower_key, lower_ref in lower_refs.items():
        ip_addr = lower_ref.get(to_key, '')
        if ip_addr:
            host_ips[lower_key] = ip_addr
            ips.remove(ip_addr)
        else:
            unassigned_hosts.append(lower_key)

    for ip_addr in ips:
        if not unassigned_hosts:
            break

        host = unassigned_hosts.pop(0)
        host_ips[host] = str(ip_addr)

    if unassigned_hosts:
        raise ValueError(
            'there is no enough ips to assign to %s: [%s-%s]' % (
                unassigned_hosts, ip_start, ip_end))

    logging.debug('assign %s: %s', to_key, host_ips)
    return host_ips


def generate_order(start=0, end=-1):
    """generate order num."""
    while start < end or end < 0:
        yield start
        start += 1


def assign_by_order(_upper_ref, _from_key, lower_refs, _to_key,
                    prefix='',
                    orders=[], default_order=0, reverse=False,
                    conditions={}, **kwargs):
    """assign to_key by order."""
    host_values = {}
    orders = iter(orders)
    lower_keys = lower_refs.keys()
    if reverse:
        lower_keys = reversed(lower_keys)

    for lower_key in lower_keys:
        if lower_key in conditions and conditions[lower_key]:
            try:
                order = orders.next()
            except StopIteration:
                order = default_order

            host_values[lower_key] = prefix + type(prefix)(order)

    logging.debug('assign orders: %s', host_values)
    return host_values


def assign_from_pattern(_upper_ref, _from_key, lower_refs, to_key,
                        upper_keys=[], lower_keys=[], pattern='', **kwargs):
    """assign to_key by pattern."""
    host_values = {}
    upper_configs = {}
    if set(upper_keys) & set(lower_keys):
        raise KeyError(
            'overlap between upper_keys %s and lower_keys %s' % (
                upper_keys, lower_keys))

    for key in upper_keys:
        if key not in kwargs:
            raise KeyError(
                'param %s is missing' % key)

        upper_configs[key] = kwargs[key]

    for lower_key, _ in lower_refs.items():
        group = copy.deepcopy(upper_configs)
        for key in lower_keys:
            if key not in kwargs:
                raise KeyError('param %s is missing' % key)

            if not isinstance(kwargs[key], dict):
                raise KeyError(
                    'param %s type is %s while expected type is dict' % (
                        kwargs[key], type(kwargs[key])))

            group[key] = kwargs[key][lower_key]

        try:
            host_values[lower_key] = pattern % group
        except KeyError as error:
            logging.error('failed to assign %s[%s] = %s %% %s',
                          lower_key, to_key, pattern, group)
            raise error

    return host_values


def assign_noproxy(_upper_ref, _from_key, lower_refs,
                   to_key, default=[], clusterid=None,
                   noproxy_pattern='',
                   hostnames={}, ips={}, **_kwargs):
    """Assign no proxy to hosts."""
    no_proxy_list = copy.deepcopy(default)
    if not clusterid:
        raise KeyError(
            'clusterid %s is empty' % clusterid)

    for lower_key, _ in lower_refs.items():
        if lower_key not in hostnames:
            raise KeyError(
                'lower_key %s is not in hostnames %s' % (
                    lower_key, hostnames))

        if lower_key not in ips:
            raise KeyError(
                'lower_key %s is not in ips %s' % (
                    lower_key, ips))

        mapping = {
            'clusterid': clusterid,
            'hostname': hostnames[lower_key],
            'ip': ips[lower_key]
        }
        try:
            no_proxy_list.append(noproxy_pattern % mapping)
        except KeyError as error:
            logging.error('failed to assign %s[%s] = %s %% %s',
                          lower_key, to_key, noproxy_pattern, mapping)
            raise error

    no_proxy = ','.join([no_proxy for no_proxy in no_proxy_list if no_proxy])
    host_no_proxy = {}
    for lower_key, _ in lower_refs.items():
        host_no_proxy[lower_key] = no_proxy

    return host_no_proxy


def override_if_empty(_upper_ref, _ref_key, lower_ref, _to_key):
    """Override if the configuration value is empty."""
    if not lower_ref.config:
        return True

    return False
