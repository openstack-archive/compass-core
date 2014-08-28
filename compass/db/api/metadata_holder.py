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

"""Metadata related object holder."""
import logging

from compass.db.api import database
from compass.db.api import metadata as metadata_api
from compass.db.api import permission
from compass.db.api import user as user_api
from compass.db.api import utils
from compass.db import exception


RESP_METADATA_FIELDS = [
    'os_config', 'package_config'
]


@database.run_in_session()
def load_metadatas(session):
    global OS_METADATA_MAPPING
    global PACKAGE_METADATA_MAPPING
    logging.info('load metadatas into memory')
    OS_METADATA_MAPPING = metadata_api.get_os_metadatas_internal(session)
    PACKAGE_METADATA_MAPPING = (
        metadata_api.get_package_metadatas_internal(session)
    )


OS_METADATA_MAPPING = {}
PACKAGE_METADATA_MAPPING = {}


def _validate_config(
    config, id, metadata_mapping, whole_check
):
    if id not in metadata_mapping:
        raise exception.InvalidParameter(
            'adapter id %s is not found in metadata mapping' % id
        )
    metadatas = metadata_mapping[id]
    metadata_api.validate_config_internal(
        config, metadatas, whole_check
    )


def validate_os_config(config, os_id, whole_check=False):
    _validate_config(
        config, os_id, OS_METADATA_MAPPING,
        whole_check
    )


def validate_package_config(config, adapter_id, whole_check=False):
    _validate_config(
        config, adapter_id, PACKAGE_METADATA_MAPPING,
        whole_check
    )


def _filter_metadata(metadata):
    if not isinstance(metadata, dict):
        return metadata
    filtered_metadata = {}
    for key, value in metadata.items():
        if key == '_self':
            filtered_metadata[key] = {
                'name': value['name'],
                'description': value.get('description', None),
                'default_value': value.get('default_value', None),
                'is_required': value.get(
                    'is_required', False),
                'required_in_whole_config': value.get(
                    'required_in_whole_config', False),
                'js_validator': value.get('js_validator', None),
                'options': value.get('options', []),
                'required_in_options': value.get(
                    'required_in_options', False),
                'field_type': value.get(
                    'field_type_data', 'str'),
                'display_type': value.get('display_type', None),
                'mapping_to': value.get('mapping_to', None)
            }
        else:
            filtered_metadata[key] = _filter_metadata(value)
    return filtered_metadata


def get_package_metadata_internal(adapter_id):
    """get package metadata internal."""
    if adapter_id not in PACKAGE_METADATA_MAPPING:
        raise exception.RecordNotExists(
            'adpater %s does not exist' % adapter_id
        )
    return _filter_metadata(PACKAGE_METADATA_MAPPING[adapter_id])


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_METADATAS
)
@utils.wrap_to_dict(RESP_METADATA_FIELDS)
def get_package_metadata(session, getter, adapter_id, **kwargs):
    return {'package_config': get_package_metadata_internal(adapter_id)}


def get_os_metadata_internal(os_id):
    """get os metadata internal."""
    if os_id not in OS_METADATA_MAPPING:
        raise exception.RecordNotExists(
            'os %s does not exist' % os_id
        )
    return _filter_metadata(OS_METADATA_MAPPING[os_id])


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_METADATAS
)
@utils.wrap_to_dict(RESP_METADATA_FIELDS)
def get_os_metadata(session, getter, os_id, **kwargs):
    """get os metadatas."""
    return {'os_config': get_os_metadata_internal(os_id)}


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_METADATAS
)
@utils.wrap_to_dict(RESP_METADATA_FIELDS)
def get_package_os_metadata(session, getter, adapter_id, os_id, **kwargs):
    from compass.db.api import adapter_holder as adapter_api
    adapter = adapter_api.get_adapter_internal(adapter_id)
    os_ids = [os['os_id'] for os in adapter['supported_oses']]
    if os_id not in os_ids:
        raise exception.InvalidParameter(
            'os %s is not in the supported os list of adapter %s' % (
                os_id, adapter_id
            )
        )
    metadatas = {}
    metadatas['os_config'] = get_os_metadata_internal(
        os_id
    )
    metadatas['package_config'] = get_package_metadata_internal(
        adapter_id
    )
    return metadatas
