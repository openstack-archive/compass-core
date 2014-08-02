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

"""Metadata related database operations."""
import logging

from compass.db.api import database
from compass.db.api import utils
from compass.db import exception
from compass.db import models
from compass.db import validator

from compass.utils import setting_wrapper as setting
from compass.utils import util


def _add_field_internal(session, model, configs):
    fields = []
    for config in configs:
        fields.append(utils.add_db_object(
            session, model, True,
            config['NAME'],
            field_type=config.get('FIELD_TYPE', basestring),
            display_type=config.get('DISPLAY_TYPE', 'text'),
            validator=config.get('VALIDATOR', None),
            js_validator=config.get('JS_VALIDATOR', None),
            description=config.get('DESCRIPTION', None)
        ))
    return fields


def add_os_field_internal(session):
    configs = util.load_configs(
        setting.OS_FIELD_DIR,
        env_locals=validator.VALIDATOR_LOCALS
    )
    return _add_field_internal(
        session, models.OSConfigField, configs
    )


def add_package_field_internal(session):
    configs = util.load_configs(
        setting.PACKAGE_FIELD_DIR,
        env_locals=validator.VALIDATOR_LOCALS
    )
    return _add_field_internal(
        session, models.PackageConfigField, configs
    )


def _add_metadata(
    session, field_model, metadata_model, path, name, config,
    parent=None, **kwargs
):
    metadata_self = config.get('_self', {})
    if 'field' in metadata_self:
        field = utils.get_db_object(
            session, field_model, field=metadata_self['field']
        )
    else:
        field = None
    metadata = utils.add_db_object(
        session, metadata_model, True,
        path, name=name, parent=parent, field=field,
        display_name=metadata_self.get('display_name', name),
        description=metadata_self.get('description', None),
        is_required=metadata_self.get('is_required', False),
        required_in_whole_config=metadata_self.get(
            'required_in_whole_config', False
        ),
        mapping_to=metadata_self.get('mapping_to', None),
        validator=metadata_self.get('validator', None),
        js_validator=metadata_self.get('js_validator', None),
        default_value=metadata_self.get('default_value', None),
        options=metadata_self.get('options', []),
        required_in_options=metadata_self.get('required_in_options', False),
        **kwargs
    )
    for key, value in config.items():
        if key not in '_self':
            _add_metadata(
                session, field_model, metadata_model,
                '%s/%s' % (path, key), key, value,
                parent=metadata, **kwargs
            )
    return metadata


def add_os_metadata_internal(session):
    os_metadatas = []
    configs = util.load_configs(
        setting.OS_METADATA_DIR,
        env_locals=validator.VALIDATOR_LOCALS
    )
    for config in configs:
        os = utils.get_db_object(
            session, models.OperatingSystem, name=config['OS']
        )
        for key, value in config['METADATA'].items():
            os_metadatas.append(_add_metadata(
                session, models.OSConfigField,
                models.OSConfigMetadata,
                key, key, value, parent=None,
                os=os
            ))
    return os_metadatas


def add_package_metadata_internal(session):
    package_metadatas = []
    configs = util.load_configs(
        setting.PACKAGE_METADATA_DIR,
        env_locals=validator.VALIDATOR_LOCALS
    )
    for config in configs:
        adapter = utils.get_db_object(
            session, models.Adapter, name=config['ADAPTER']
        )
        for key, value in config['METADATA'].items():
            package_metadatas.append(_add_metadata(
                session, models.PackageConfigField,
                models.PackageConfigMetadata,
                key, key, value, parent=None,
                adapter=adapter
            ))
    return package_metadatas


def get_package_metadatas_internal(session):
    metadata_mapping = {}
    adapters = utils.list_db_objects(
        session, models.Adapter
    )
    for adapter in adapters:
        if adapter.deployable:
            metadata_dict = adapter.metadata_dict()
            metadata_mapping[adapter.id] = metadata_dict
        else:
            logging.info(
                'ignore metadata since its adapter %s is not deployable',
                adapter.id
            )
    return metadata_mapping


def get_os_metadatas_internal(session):
    metadata_mapping = {}
    oses = utils.list_db_objects(
        session, models.OperatingSystem
    )
    for os in oses:
        if os.deployable:
            metadata_dict = os.metadata_dict()
            metadata_mapping[os.id] = metadata_dict
        else:
            logging.info(
                'ignore metadata since its os %s is not deployable',
                os.id
            )
    return metadata_mapping


def _validate_self(
    config_path, config_key, config, metadata, whole_check
):
    if '_self' not in metadata:
        return
    field_type = metadata['_self'].get('field_type', 'basestring')
    if not isinstance(config, field_type):
        raise exception.InvalidParameter(
            '%s config type is not %s' % (config_path, field_type)
        )
    required_in_options = metadata['_self'].get(
        'required_in_options', False
    )
    options = metadata['_self'].get('options', [])
    if required_in_options:
        if field_type in [int, basestring, float, bool]:
            if config not in options:
                raise exception.InvalidParameter(
                    '%s config is not in %s' % (config_path, options)
                )
        elif field_type in [list, tuple]:
            if not set(config).issubset(set(options)):
                raise exception.InvalidParameter(
                    '%s config is not in %s' % (config_path, options)
                )
        elif field_type == dict:
            if not set(config.keys()).issubset(set(options)):
                raise exception.InvalidParameter(
                    '%s config is not in %s' % (config_path, options)
                )
    validator = metadata['_self'].get('validator', None)
    if validator:
        if not validator(config_key, config):
            raise exception.InvalidParameter(
                '%s config is invalid' % config_path
            )
    if issubclass(field_type, dict):
        _validate_config(config_path, config, metadata, whole_check)


def _validate_config(config_path, config, metadata, whole_check):
    generals = {}
    specified = {}
    for key, value in metadata.items():
        if key.startswith('$'):
            generals[key] = value
        elif key.startswith('_'):
            pass
        else:
            specified[key] = value
    config_keys = set(config.keys())
    specified_keys = set(specified.keys())
    intersect_keys = config_keys & specified_keys
    not_found_keys = config_keys - specified_keys
    redundant_keys = specified_keys - config_keys
    for key in redundant_keys:
        if '_self' not in specified[key]:
            continue
        if specified[key]['_self'].get('is_required', False):
            raise exception.InvalidParameter(
                '%s/%s does not find is_required' % (
                    config_path, key
                )
            )
        if (
            whole_check and
            specified[key]['_self'].get(
                'required_in_whole_config', False
            )
        ):
            raise exception.InvalidParameter(
                '%s/%s does not find required_in_whole_config' % (
                    config_path, key
                )
            )
    for key in intersect_keys:
        _validate_self(
            '%s/%s' % (config_path, key),
            key, config[key], specified[key], whole_check
        )
    for key in not_found_keys:
        for general_key, general_value in generals.items():
            _validate_self(
                '%s/%s' % (config_path, key),
                key, config[key], general_value, whole_check
            )


def validate_config_internal(config, metadata, whole_check):
    _validate_config('', config, metadata, whole_check)
