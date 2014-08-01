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


def _add_system(session, model, configs):
    parents = {}
    for config in configs:
        logging.info(
            'add config %s to %s',
            config, model
        )
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
    _add_system(session, models.OperatingSystem, configs)


def add_distributed_systems_internal(session):
    configs = util.load_configs(setting.DISTRIBUTED_SYSTEM_DIR)
    _add_system(session, models.DistributedSystem, configs)


def add_adapters_internal(session):
    parents = {}
    configs = util.load_configs(setting.ADAPTER_DIR)
    for config in configs:
        logging.info('add config %s to adapter', config)
        if 'DISTRIBUTED_SYSTEM' in config:
            distributed_system = utils.get_db_object(
                session, models.DistributedSystem,
                name=config['DISTRIBUTED_SYSTEM']
            )
        else:
            distributed_system = None
        if 'OS_INSTALLER' in config:
            os_installer = utils.get_db_object(
                session, models.OSInstaller,
                instance_name=config['OS_INSTALLER']
            )
        else:
            os_installer = None
        if 'PACKAGE_INSTALLER' in config:
            package_installer = utils.get_db_object(
                session, models.PackageInstaller,
                instance_name=config['PACKAGE_INSTALLER']
            )
        else:
            package_installer = None
        adapter = utils.add_db_object(
            session, models.Adapter,
            True,
            config['NAME'],
            display_name=config.get('DISPLAY_NAME', None),
            distributed_system=distributed_system,
            os_installer=os_installer,
            package_installer=package_installer,
            deployable=config.get('DEPLOYABLE', False)
        )
        supported_os_patterns = [
            re.compile(supported_os_pattern)
            for supported_os_pattern in config.get('SUPPORTED_OS_PATTERNS', [])
        ]
        oses = utils.list_db_objects(
            session, models.OperatingSystem
        )
        for os in oses:
            if not os.deployable:
                continue
            os_name = os.name
            for supported_os_pattern in supported_os_patterns:
                if supported_os_pattern.match(os_name):
                    utils.add_db_object(
                        session, models.AdapterOS,
                        True,
                        os.id, adapter.id
                    )
                    break
            parents[config['NAME']] = (adapter, config.get('PARENT', None))

    for name, (adapter, parent_name) in parents.items():
            if parent_name:
                parent, _ = parents[parent_name]
            else:
                parent = None
            utils.update_db_object(session, adapter, parent=parent)


def add_roles_internal(session):
    configs = util.load_configs(setting.ADAPTER_ROLE_DIR)
    for config in configs:
        logging.info(
            'add config to role', config
        )
        adapter = utils.get_db_object(
            session, models.Adapter,
            name=config['ADAPTER_NAME']
        )
        for role_dict in config['ROLES']:
            utils.add_db_object(
                session, models.AdapterRole,
                True, role_dict['role'], adapter.id,
                display_name=role_dict.get('display_name', None),
                description=role_dict.get('description', None),
                optional=role_dict.get('optional', False)
            )


def get_adapters_internal(session):
    adapter_mapping = {}
    adapters = utils.list_db_objects(
        session, models.Adapter
    )
    for adapter in adapters:
        if adapter.deployable:
            adapter_dict = adapter.to_dict()
            adapter_mapping[adapter.id] = adapter_dict
        else:
            logging.info(
                'ignore adapter %s since it is not deployable',
                adapter_dict
            )
    return adapter_mapping
