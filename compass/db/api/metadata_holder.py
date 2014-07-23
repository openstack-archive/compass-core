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


@database.run_in_session()
def load_metadatas(session):
    global METADATA_MAPPING
    logging.info('load metadatas into memory')
    METADATA_MAPPING = metadata_api.get_metadatas_internal(session)


METADATA_MAPPING = {}


def _validate_config(
    config, adapter_id,
    metadata_mapping, metadata_field, whole_check
):
    if adapter_id not in metadata_mapping:
        raise exception.InvalidParameter(
            'adapter id %s is not found in metadata mapping' % adapter_id
        )
    metadatas = metadata_mapping[adapter_id]
    if metadata_field not in metadatas:
        return
    metadata_api.validate_config_internal(
        config, metadatas[metadata_field], whole_check
    )


def validate_os_config(config, adapter_id, whole_check=False):
    _validate_config(
        config, adapter_id, METADATA_MAPPING, 'os_config',
        whole_check
    )


def validate_package_config(config, adapter_id, whole_check=False):
    _validate_config(
        config, adapter_id, METADATA_MAPPING,
        'package_config', whole_check
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
                'is_required': value['is_required'],
                'required_in_whole_config': value['required_in_whole_config'],
                'js_validator': value.get('js_validator', None),
                'options': value.get('options', []),
                'required_in_options': value['required_in_options'],
                'field_type': value['field_type_data'],
                'display_type': value.get('display_type', None),
            }
        else:
            filtered_metadata[key] = _filter_metadata(value)
    return filtered_metadata


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_METADATAS
)
def get_metadata(session, getter, adapter_id, **kwargs):
    """get adapter."""
    if adapter_id not in METADATA_MAPPING:
        raise exception.RecordNotExists(
            'adpater %s does not exist' % adapter_id
        )
    return _filter_metadata(METADATA_MAPPING[adapter_id])
