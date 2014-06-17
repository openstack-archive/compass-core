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
from compass.db import exception
from compass.db.api import database
from compass.db.api import metadata as metadata_api
from compass.db.api import user as user_api
from compass.db.api import utils

def load_metadatas():
    with database.session() as session:
        return metadata_api.get_metadatas_internal(session)


METADATA_MAPPING = load_metadatas()


def _validate_config(config, adapter_id, metadata_mapping, whole_check):
    if adapter_id not in metadata_mapping:
        raise exception.InvalidParameter(
            'adapter id %s is not found in metadata mapping' % adapter_id
        )
    adapter_metadata = metadata_mapping[adapter_id]
    if metadata_key not in adapter_metadata:
        raise exception.InvalidParameter(
            '%s is not found in adapter %s metadata' % (metadata_key, adapter_id)
        )
    metadata = adapter_metadata[metadata_key]
    metadata_api.validate_config_internal(config, metadata, whole_check)
        

def validate_os_config(config, adapter_id, whole_check=False):
    _validate_config(config, adapter_id, METADATA_MAPPING['os_config'], whole_check)


def validate_package_config(config, adapter_id, whole_check=False):
    _validate_config(config, adapter_id, METADATA_MAPPING['package_config'], whole_check)


def _filter_metadata(metadata):
    if not isinstance(metadata, dict):
        return metadata
    filtered_metadata = {}
    for key, value in metadata.items():
        if key == '_self':
            filtered_metadata[key] = {
                'name': value['name'],
                'description': value['description'],
                'is_required': value['is_required'],
                'required_in_whole_config': value['required_in_whole_config'],
                'js_validator': value['js_validator'],
                'options': value['options'],
                'required_in_options': value['required_in_options'],
                'field_type': value['field_type_data'],
                'display_type': value.get('display_type', None),
            } 
        else:
            filtered_metadata[key] = _filter_metadata(value)
    return filtered_metadata


@utils.supported_filters([])
def get_metadata(getter, adapter_id, **kwargs):
    """get adapter."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, lister, permission.PERMISSION_LIST_METADATAS)
        if adapter_id not in METADATA_MAPPING:
            raise excedption.RecordNotExists(
                'adpater %s does not exist' % adapter_id
            )
        return _filter_metadata(METADATA_MAPPING[adapter_id])
