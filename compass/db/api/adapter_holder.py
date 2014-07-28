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
import logging

from compass.db.api import adapter as adapter_api
from compass.db.api import database
from compass.db.api import permission
from compass.db.api import user as user_api
from compass.db.api import utils
from compass.db import exception


SUPPORTED_FIELDS = [
    'name',
    'distributed_system_name',
]
RESP_FIELDS = [
    'id', 'name', 'roles',
    'distributed_system_name',
    'supported_oses', 'display_name'
]
RESP_OS_FIELDS = [
    'id', 'os_id', 'name'
]
RESP_ROLES_FIELDS = [
    'id', 'name', 'display_name', 'description', 'optional'
]


@database.run_in_session()
def load_adapters(session):
    global ADAPTER_MAPPING
    logging.info('load adapters into memory')
    ADAPTER_MAPPING = adapter_api.get_adapters_internal(session)


ADAPTER_MAPPING = {}


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
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_ADAPTERS
)
@utils.output_filters(
    name=utils.general_filter_callback,
    distributed_system_name=utils.general_filter_callback,
    os_installer_name=utils.general_filter_callback,
    package_installer_name=utils.general_filter_callback
)
@utils.wrap_to_dict(
    RESP_FIELDS,
    supported_oses=RESP_OS_FIELDS
)
def list_adapters(session, lister, **filters):
    """list adapters."""
    return ADAPTER_MAPPING.values()


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_ADAPTERS
)
@utils.wrap_to_dict(
    RESP_FIELDS,
    supported_oses=RESP_OS_FIELDS
)
def get_adapter(session, getter, adapter_id, **kwargs):
    """get adapter."""
    if adapter_id not in ADAPTER_MAPPING:
        raise exception.RecordNotExists(
            'adpater %s does not exist' % adapter_id
        )
    return ADAPTER_MAPPING[adapter_id]


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_ADAPTERS
)
@utils.wrap_to_dict(RESP_ROLES_FIELDS)
def get_adapter_roles(session, getter, adapter_id, **kwargs):
    """get adapter roles."""
    if adapter_id not in ADAPTER_MAPPING:
        raise exception.RecordNotExists(
            'adpater %s does not exist' % adapter_id
        )
    return ADAPTER_MAPPING[adapter_id].get('roles', [])
