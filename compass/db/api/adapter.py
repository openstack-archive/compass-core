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


OSES = {}
OS_INSTALLERS = {}
PACKAGE_INSTALLERS = {}
ADAPTERS = {}
ADAPTERS_FLAVORS = {}
ADAPTERS_ROLES = {}


def _get_oses():
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


def _get_installers(configs):
    installers = {}
    for config in configs:
        instance_name = config['INSTANCE_NAME']
        installers[instance_name] = {
            'alias': instance_name,
            'id': instance_name,
            'name': config['NAME'],
            'settings': config.get('SETTINGS', {})
        }
    return installers


def _get_os_installers():
    configs = util.load_configs(setting.OS_INSTALLER_DIR)
    return _get_installers(configs)


def _get_package_installers():
    configs = util.load_configs(setting.PACKAGE_INSTALLER_DIR)
    return _get_installers(configs)


def _get_adapters():
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
            'display_name': config.get('DISPLAY_NAME', None),
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


def _add_roles():
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
            adapter_roles[role_name] = {
                'name': role_name,
                'id': '%s:%s' % (adapter_name, role_name),
                'adapter_id': adapter_name,
                'display_name': role_dict.get('display_name', None),
                'description': role_dict.get('description', None),
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


def _add_flavors():
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
                'display_name': flavor_dict.get('display_name', None),
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


def add_adapters_internal(force=False):
    global OSES
    if force or not OSES:
        OSES = _get_oses()
    global OS_INSTALLERS
    if force or not OS_INSTALLERS:
        OS_INSTALLERS = _get_os_installers()
    global PACKAGE_INSTALLERS
    if force or not PACKAGE_INSTALLERS:
        PACKAGE_INSTALLERS = _get_package_installers()
    global ADAPTERS
    if force or not ADAPTERS:
        ADAPTERS = _get_adapters()
    global ADAPTERS_ROLES
    if force or not ADAPTERS_ROLES:
        _add_roles()
    global ADAPTERS_FLAVORS
    if force or not ADAPTERS_FLAVORS:
        _add_flavors()


def get_adapters_internal(force_reload=False):
    add_adapters_internal(force=force_reload)
    adapter_mapping = {}
    for adapter_name, adapter in ADAPTERS.items():
        if adapter.get('deployable'):
            adapter_mapping[adapter_name] = adapter
        else:
            logging.info(
                'ignore adapter %s since it is not deployable',
                adapter_name
            )
    return adapter_mapping


def get_flavors_internal(force_reload=False):
    add_adapters_internal(force=force_reload)
    adapter_flavor_mapping = {}
    for adapter_name, adapter_flavors in ADAPTERS_FLAVORS.items():
        adapter = ADAPTERS.get(adapter_name, {})
        for flavor_name, flavor in adapter_flavors.items():
            if adapter.get('deployable'):
                adapter_flavor_mapping.setdefault(
                    adapter_name, {}
                )[flavor_name] = flavor
            else:
                logging.info(
                    'ignore adapter %s since it is not deployable',
                    adapter_name
                )

    return adapter_flavor_mapping
