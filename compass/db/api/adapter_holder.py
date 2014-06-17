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

"""Adapter related object holder."""
from compass.db import exception
from compass.db.api import database
from compass.db.api import adapter as adapter_api
from compass.db.api import user as user_api
from compass.db.api import utils


SUPPORTED_FIELDS = ['name', 'os', 'distributed_system', 'os_installer', 'package_installer']
OS_FIELD_MAPPING = {
    'os': 'os_name',
    'os_installer': 'installer_type'
}
PACKAGE_FIELD_MAPPING = {
    'distributed_system': 'distributed_system_name',
    'package_installer': 'installer_type'
}

def load_adapters():
    with database.session() as session:
        return adapter_api.get_adapters_internal(session)


ADAPTER_MAPPING = load_adapters()


def _filter_adapters(adapter_config, filter_name, filter_value):
    if filter_name not in adapter_config:
        return False
    if isinstance(filter_value, list):
        return bool(
            adapter_config[filter_name] in filter_value
        )
    elif isinstance(filter_value, dict):
        return all([
            _filter_adapters(
                adapter_config[filter_name],
                sub_filter_key, sub_filter_value
            )
            for sub_filter_key, sub_filter_value in filter_value.items()
        ])
    else:
        return adapter_config[filter_name] == filter_value


@utils.supported_filters(optional_support_keys=SUPPORTED_FIELDS)
def list_adpaters(lister, **filters):
    """list adapters."""
    translated_filters = {}
    for filter_name, filter_value in filters:
        if filter_name in OS_FIELD_MAPPING:
            translated_filters.setdefault('os_adapter', {})[
                OS_FIELD_MAPPING[filter_name]
            ] = filter_value
        elif filter_name in PACKAGE_FIELD_MAPPING:
            translated_filters.setdefault('package-adapter', {})[
                PACKAGE_FIELD_MAPPING[filter_name]
            ] = filter_value
        else:
            translated_filters[filter_name] = filter_value
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, lister, permission.PERMISSION_LIST_ADAPTER)
        filtered_adapter_dicts = []
        adapter_dicts = ADAPTER_MAPPING.values()
        for adapter_dict in adapter_dicts:
            if all([
                _filter_adapters(adapter_dict, filter_name, filter_value)
                for filter_name, filter_value in translated_filters.items()
            ]):
                filtered_adapter_dicts.append(adapter_dicts)
        return filtered_adapter_dicts


@utils.supported_filters([])
def get_adapter(getter, adapter_id, **kwargs):
    """get adapter."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, lister, permission.PERMISSION_LIST_ADAPTER)
        if adapter_id not in ADAPTER_MAPPING:
            raise excedption.RecordNotExists(
                'adpater %s does not exist' % adapter_id
            )
        return ADAPTER_MAPPING[adapter_id]


@utils.supported_filters([])
def get_adapter_roles(getter, adapter_id, **kwargs):
    """get adapter roles."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, lister, permission.PERMISSION_LIST_ADAPTER)
        if adapter_id not in ADAPTER_MAPPING:
            raise excedption.RecordNotExists(
                'adpater %s does not exist' % adapter_id
            )
        adapter_dict = ADAPTER_MAPPING[adapter_id]
        if 'package_adapter' not in adapter_dict:
            raise excedption.RecordNotExists(
                'adapter %s does not contain package_adapter' % adapter_id
            )
        return ADAPTER_MAPPING[adapter_id]['package_adapter']['roles']
