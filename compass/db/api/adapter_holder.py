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
]
RESP_FIELDS = [
    'id', 'name', 'roles', 'flavors',
    'os_installer', 'package_installer',
    'supported_oses', 'display_name', 'health_check_cmd'
]
RESP_OS_FIELDS = [
    'id', 'name', 'os_id'
]
RESP_ROLES_FIELDS = [
    'id', 'name', 'display_name', 'description', 'optional'
]
RESP_FLAVORS_FIELDS = [
    'id', 'adapter_id', 'adapter_name', 'name', 'display_name',
    'template', 'roles'
]


ADAPTER_MAPPING = None
FLAVOR_MAPPING = None


def load_adapters(force_reload=False):
    global ADAPTER_MAPPING
    if force_reload or ADAPTER_MAPPING is None:
        logging.info('load adapters into memory')
        ADAPTER_MAPPING = adapter_api.get_adapters_internal(
            force_reload=force_reload
        )


def load_flavors(force_reload=False):
    global FLAVOR_MAPPING
    if force_reload or FLAVOR_MAPPING is None:
        logging.info('load flavors into memory')
        FLAVOR_MAPPING = {}
        adapters_flavors = adapter_api.get_flavors_internal(
            force_reload=force_reload
        )
        for adapter_name, adapter_flavors in adapters_flavors.items():
            for flavor_name, flavor in adapter_flavors.items():
                FLAVOR_MAPPING['%s:%s' % (adapter_name, flavor_name)] = flavor


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
@user_api.check_user_permission(
    permission.PERMISSION_LIST_ADAPTERS
)
@utils.output_filters(name=utils.general_filter_callback)
@utils.wrap_to_dict(
    RESP_FIELDS,
    supported_oses=RESP_OS_FIELDS,
    roles=RESP_ROLES_FIELDS,
    flavors=RESP_FLAVORS_FIELDS
)
def list_adapters(user=None, session=None, **filters):
    """list adapters."""
    load_adapters()
    return ADAPTER_MAPPING.values()


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_ADAPTERS
)
@utils.wrap_to_dict(
    RESP_FIELDS,
    supported_oses=RESP_OS_FIELDS,
    roles=RESP_ROLES_FIELDS,
    flavors=RESP_FLAVORS_FIELDS
)
def get_adapter(adapter_id, user=None, session=None, **kwargs):
    """get adapter."""
    load_adapters()
    if adapter_id not in ADAPTER_MAPPING:
        raise exception.RecordNotExists(
            'adpater %s does not exist' % adapter_id
        )
    return ADAPTER_MAPPING[adapter_id]


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_METADATAS
)
@utils.wrap_to_dict(RESP_FLAVORS_FIELDS)
def list_flavors(user=None, session=None, **filters):
    """List flavors."""
    load_flavors()
    return FLAVOR_MAPPING.values()


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_METADATAS
)
@utils.wrap_to_dict(RESP_FLAVORS_FIELDS)
def get_flavor(flavor_id, user=None, session=None, **kwargs):
    """Get flavor."""
    load_flavors()
    if flavor_id not in FLAVOR_MAPPING:
        raise exception.RecordNotExists(
            'flavor %s does not exist' % flavor_id
        )
    return FLAVOR_MAPPING[flavor_id]
