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

"""Adapter related database operations."""
import logging
import re

from compass.db.api import database
from compass.db.api import utils
from compass.db import exception
from compass.db import models

from compass.utils import setting_wrapper as setting
from compass.utils import util


OSES = None
OS_INSTALLERS = None
PACKAGE_INSTALLERS = None
ADAPTERS = None
ADAPTERS_FLAVORS = None
ADAPTERS_ROLES = None


def _get_oses_from_configuration():
    """Get all os configs from os configuration dir.

    Example: {
        <os_name>: {
            'name': <os_name>,
            'id': <os_name>,
            'os_id': <os_name>,
            'deployable': True
        }
    }
    """
    configs = util.load_configs(setting.OS_DIR)
    systems = {}
    for config in configs:
        logging.info('get config %s', config)
        system_name = config['NAME']
        parent_name = config.get('PARENT', None)
        system = {
            'name': system_name,
            'id': system_name,
            'os_id': system_name,
            'parent': parent_name,
            'parent_id': parent_name,
            'deployable': config.get('DEPLOYABLE', False)
        }
        systems[system_name] = system
    parents = {}
    for name, system in systems.items():
        parent = system.get('parent', None)
        parents[name] = parent
    for name, system in systems.items():
        util.recursive_merge_dict(name, systems, parents)
    return systems


def _get_installers_from_configuration(configs):
    """Get installers from configurations.

    Example: {
        <installer_isntance>: {
            'alias': <instance_name>,
            'id': <instance_name>,
            'name': <name>,
            'settings': <dict pass to installer plugin>
        }
    }
    """
    installers = {}
    for config in configs:
        name = config['NAME']
        instance_name = config.get('INSTANCE_NAME', name)
        installers[instance_name] = {
            'alias': instance_name,
            'id': instance_name,
            'name': name,
            'settings': config.get('SETTINGS', {})
        }
    return installers


def _get_os_installers_from_configuration():
    """Get os installers from os installer config dir."""
    configs = util.load_configs(setting.OS_INSTALLER_DIR)
    return _get_installers_from_configuration(configs)


def _get_package_installers_from_configuration():
    """Get package installers from package installer config dir."""
    configs = util.load_configs(setting.PACKAGE_INSTALLER_DIR)
    return _get_installers_from_configuration(configs)


def _get_adapters_from_configuration():
    """Get adapters from adapter config dir."""
    configs = util.load_configs(setting.ADAPTER_DIR)
    adapters = {}
    for config in configs:
        logging.info('add config %s to adapter', config)
        if 'OS_INSTALLER' in config:
            os_installer = OS_INSTALLERS[config['OS_INSTALLER']]
        else:
            os_installer = None

        if 'PACKAGE_INSTALLER' in config:
            package_installer = PACKAGE_INSTALLERS[
                config['PACKAGE_INSTALLER']
            ]
        else:
            package_installer = None

        adapter_name = config['NAME']
        parent_name = config.get('PARENT', None)
        adapter = {
            'name': adapter_name,
            'id': adapter_name,
            'parent': parent_name,
            'parent_id': parent_name,
            'display_name': config.get('DISPLAY_NAME', adapter_name),
            'os_installer': os_installer,
            'package_installer': package_installer,
            'deployable': config.get('DEPLOYABLE', False),
            'health_check_cmd': config.get('HEALTH_CHECK_COMMAND', None),
            'supported_oses': [],
            'roles': [],
            'flavors': []
        }
        supported_os_patterns = [
            re.compile(supported_os_pattern)
            for supported_os_pattern in config.get('SUPPORTED_OS_PATTERNS', [])
        ]
        for os_name, os in OSES.items():
            if not os.get('deployable', False):
                continue
            for supported_os_pattern in supported_os_patterns:
                if supported_os_pattern.match(os_name):
                    adapter['supported_oses'].append(os)
                    break
        adapters[adapter_name] = adapter

    parents = {}
    for name, adapter in adapters.items():
        parent = adapter.get('parent', None)
        parents[name] = parent
    for name, adapter in adapters.items():
        util.recursive_merge_dict(name, adapters, parents)
    return adapters


def _add_roles_from_configuration():
    """Get roles from roles config dir and update to adapters."""
    configs = util.load_configs(setting.ADAPTER_ROLE_DIR)
    for config in configs:
        logging.info(
            'add config %s to role', config
        )
        adapter_name = config['ADAPTER_NAME']
        adapter = ADAPTERS[adapter_name]
        adapter_roles = ADAPTERS_ROLES.setdefault(adapter_name, {})
        for role_dict in config['ROLES']:
            role_name = role_dict['role']
            display_name = role_dict.get('display_name', role_name)
            adapter_roles[role_name] = {
                'name': role_name,
                'id': '%s:%s' % (adapter_name, role_name),
                'adapter_id': adapter_name,
                'adapter_name': adapter_name,
                'display_name': display_name,
                'description': role_dict.get('description', display_name),
                'optional': role_dict.get('optional', False)
            }
    parents = {}
    for name, adapter in ADAPTERS.items():
        parent = adapter.get('parent', None)
        parents[name] = parent
    for adapter_name, adapter_roles in ADAPTERS_ROLES.items():
        util.recursive_merge_dict(adapter_name, ADAPTERS_ROLES, parents)
    for adapter_name, adapter_roles in ADAPTERS_ROLES.items():
        adapter = ADAPTERS[adapter_name]
        adapter['roles'] = adapter_roles.values()


def _add_flavors_from_configuration():
    """Get flavors from flavor config dir and update to adapters."""
    configs = util.load_configs(setting.ADAPTER_FLAVOR_DIR)
    for config in configs:
        logging.info('add config %s to flavor', config)
        adapter_name = config['ADAPTER_NAME']
        adapter = ADAPTERS[adapter_name]
        adapter_flavors = ADAPTERS_FLAVORS.setdefault(adapter_name, {})
        adapter_roles = ADAPTERS_ROLES[adapter_name]
        for flavor_dict in config['FLAVORS']:
            flavor_name = flavor_dict['flavor']
            flavor_id = '%s:%s' % (adapter_name, flavor_name)
            flavor = {
                'name': flavor_name,
                'id': flavor_id,
                'adapter_id': adapter_name,
                'adapter_name': adapter_name,
                'display_name': flavor_dict.get('display_name', flavor_name),
                'template': flavor_dict.get('template', None)
            }
            flavor_roles = flavor_dict.get('roles', [])
            roles_in_flavor = []
            for flavor_role in flavor_roles:
                if isinstance(flavor_role, basestring):
                    role_name = flavor_role
                    role_in_flavor = {
                        'name': role_name,
                        'flavor_id': flavor_id
                    }
                else:
                    role_in_flavor = flavor_role
                    role_in_flavor['flavor_id'] = flavor_id
                    if 'role' in role_in_flavor:
                        role_in_flavor['name'] = role_in_flavor['role']
                        del role_in_flavor['role']
                    role_name = role_in_flavor['name']
                role = adapter_roles[role_name]
                util.merge_dict(role_in_flavor, role, override=False)
                roles_in_flavor.append(role_in_flavor)
            flavor['roles'] = roles_in_flavor
            adapter_flavors[flavor_name] = flavor
    parents = {}
    for name, adapter in ADAPTERS.items():
        parent = adapter.get('parent', None)
        parents[name] = parent
    for adapter_name, adapter_roles in ADAPTERS_FLAVORS.items():
        util.recursive_merge_dict(adapter_name, ADAPTERS_FLAVORS, parents)
    for adapter_name, adapter_flavors in ADAPTERS_FLAVORS.items():
        adapter = ADAPTERS[adapter_name]
        adapter['flavors'] = adapter_flavors.values()


def load_adapters_internal(force_reload=False):
    """Load adapter related configurations into memory.

    If force_reload, reload all configurations even it is loaded already.
    """
    global OSES
    if force_reload or OSES is None:
        OSES = _get_oses_from_configuration()
    global OS_INSTALLERS
    if force_reload or OS_INSTALLERS is None:
        OS_INSTALLERS = _get_os_installers_from_configuration()
    global PACKAGE_INSTALLERS
    if force_reload or PACKAGE_INSTALLERS is None:
        PACKAGE_INSTALLERS = _get_package_installers_from_configuration()
    global ADAPTERS
    if force_reload or ADAPTERS is None:
        ADAPTERS = _get_adapters_from_configuration()
    global ADAPTERS_ROLES
    if force_reload or ADAPTERS_ROLES is None:
        ADAPTERS_ROLES = {}
        _add_roles_from_configuration()
    global ADAPTERS_FLAVORS
    if force_reload or ADAPTERS_FLAVORS is None:
        ADAPTERS_FLAVORS = {}
        _add_flavors_from_configuration()


def get_adapters_internal(force_reload=False):
    """Get all deployable adapters."""
    load_adapters_internal(force_reload=force_reload)
    adapter_mapping = {}
    for adapter_name, adapter in ADAPTERS.items():
        if adapter.get('deployable'):
            # TODO(xicheng): adapter should be filtered before
            # return to caller.
            adapter_mapping[adapter_name] = adapter
        else:
            logging.info(
                'ignore adapter %s since it is not deployable',
                adapter_name
            )
    return adapter_mapping


def get_flavors_internal(force_reload=False):
    """Get all deployable flavors."""
    load_adapters_internal(force_reload=force_reload)
    adapter_flavor_mapping = {}
    for adapter_name, adapter_flavors in ADAPTERS_FLAVORS.items():
        adapter = ADAPTERS.get(adapter_name, {})
        for flavor_name, flavor in adapter_flavors.items():
            if adapter.get('deployable'):
                # TODO(xicheng): flavor dict should be filtered before
                # return to caller.
                adapter_flavor_mapping.setdefault(
                    adapter_name, {}
                )[flavor_name] = flavor
            else:
                logging.info(
                    'ignore adapter %s since it is not deployable',
                    adapter_name
                )

    return adapter_flavor_mapping
