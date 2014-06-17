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


def _copy_adapters_from_parent(session, model, parent, system_name):
    for child in parent.children:
        if not child.adapters:
            for adapter in parent.adapters:
                if adapter.children:
                    continue
                utils.add_db_object(
                    session, model,
                    True,
                    '%s(%s)' % (child.name, adapter.installer_name),
                    system_name=child, parent=adapter
                )
        _copy_adapters_from_parent(session, model, child, system_name)


def _complement_os_adapters(session):
    with session.begin(subtransactions=True):
        root_oses = utils.list_db_objects(
            session, models.OperatingSystem,
            parent_id=None
        )
        for root_os in root_oses:
            _copy_adapters_from_parent(
                session, models.OSAdapter, root_os, 'os'
            )


def _complement_distributed_system_adapters(session):
    with session.begin(subtransactions=True):
        root_dses = utils.list_db_objects(
            session, models.DistributedSystem,
            parent_id=None
        )
        for root_ds in root_dses:
            _copy_adapters_from_parent(
                session, models.PackageAdapter, root_ds, 'distributed_system'
            )


def _add_system(session, model, configs):
    parents = {}
    for config in configs:
        object = utils.add_db_object(
            session, model,
            True, config['NAME'],
            deployable=config.get('DEPLOYABLE', False)
        )
        parents[config['NAME']] = (
            object, config.get('PARENT', None)
        )
    for name, (object, parent_name) in parents.items():
        if parent_name:
            parent, _ = parents[parent_name]
        else:
            parent = None
        utils.update_db_object(session, object, parent=parent)


def add_oses_internal(session):
    configs = util.load_configs(setting.OS_DIR)
    with session.begin(subtransactions=True):
        _add_system(session, models.OperatingSystem, configs)


def add_distributed_systems_internal(session):
    configs = util.load_configs(setting.DISTRIBUTED_SYSTEM_DIR)
    with session.begin(subtransactions=True):
        _add_system(session, models.DistributedSystem, configs)


def add_os_adapters_internal(session):
    parents = {}
    configs = util.load_configs(setting.OS_ADAPTER_DIR)
    with session.begin(subtransactions=True):
        for config in configs:
            if 'OS' in config:
                os = utils.get_db_object(
                    session, models.OperatingSystem,
                    name=config['OS']
                )
            else:
                os = None
            if 'INSTALLER' in config:
                installer = utils.get_db_object(
                    session, models.OSInstaller,
                    name=config['INSTALLER']
                )
            else:
                installer = None
            object = utils.add_db_object(
                session, models.OSAdapter,
                True, config['NAME'], os=os, installer=installer
            )
            parents[config['NAME']] = (object, config.get('PARENT', None))
        for name, (object, parent_name) in parents.items():
            if parent_name:
                parent, _ = parents[parent_name]
            else:
                parent = None
            utils.update_db_object(
                session, object, parent=parent
            )

    _complement_os_adapters(session)


def add_package_adapters_internal(session):
    parents = {}
    configs = util.load_configs(setting.PACKAGE_ADAPTER_DIR)
    with session.begin(subtransactions=True):
        for config in configs:
            if 'DISTRIBUTED_SYSTEM' in config:
                distributed_system = utils.get_db_object(
                    session, models.DistributedSystem,
                    name=config['DISTRIBUTED_SYSTEM']
                )
            else:
                distributed_system = None
            if 'INSTALLER' in config:
                installer = utils.get_db_object(
                    session, models.PackageInstaller,
                    name=config['INSTALLER']
                )
            else:
                installer = None
            object = utils.add_db_object(
                session, models.PackageAdapter,
                True,
                config['NAME'],
                distributed_system=distributed_system,
                installer=installer,
                supported_os_patterns=config.get('SUPPORTED_OS_PATTERNS', [])
            )
            parents[config['NAME']] = (object, config.get('PARENT', None))
        for name, (object, parent_name) in parents.items():
            if parent_name:
                parent, _ = parents[parent_name]
            else:
                parent = None
            utils.update_db_object(session, object, parent=parent)

    _complement_distributed_system_adapters(session)


def add_roles_internal(session):
    configs = util.load_configs(setting.PACKAGE_ROLE_DIR)
    with session.begin(subtransactions=True):
        for config in configs:
            package_adapter = utils.get_db_object(
                session, models.PackageAdapter,
                name=config['ADAPTER_NAME']
            )
            for role_dict in config['ROLES']:
                utils.add_db_object(
                    session, models.PackageAdapterRole,
                    True, role_dict['role'], package_adapter.id,
                    description=role_dict['description'],
                    optional=role_dict.get('optional', False)
                )


def add_adapters_internal(session):
    with session.begin(subtransactions=True):
        package_adapters = [
            package_adapter
            for package_adapter in utils.list_db_objects(
                session, models.PackageAdapter
            )
            if package_adapter.deployable
        ]
        os_adapters = [
            os_adapter
            for os_adapter in utils.list_db_objects(
                session, models.OSAdapter
            )
            if os_adapter.deployable
        ]
        adapters = []
        for os_adapter in os_adapters:
            adapters.append(utils.add_db_object(
                session, models.Adapter, True,
                os_adapter.id, None
            ))
        for package_adapter in package_adapters:
            adapters.append(utils.add_db_object(
                session, models.Adapter, True,
                None, package_adapter.id
            ))
            for os_adapter in os_adapters:
                for os_pattern in (
                    package_adapter.adapter_supported_os_patterns
                ):
                    if re.match(os_pattern, os_adapter.name):
                        adapters.append(utils.add_db_object(
                            session, models.Adapter, True,
                            os_adapter.id, package_adapter.id
                        ))
                        break
        return adapters


def get_adapters_internal(session):
    adapter_mapping = {}
    with session.begin(subtransactions=True):
        adapters = utils.list_db_objects(
            session, models.Adapter
        )
        for adapter in adapters:
            adapter_dict = adapter.to_dict()
            adapter_mapping[adapter.id] = adapter_dict
    return adapter_mapping
