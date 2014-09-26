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
from compass.db import callback as metadata_callback
from compass.db import exception
from compass.db import models
from compass.db import validator as metadata_validator


from compass.utils import setting_wrapper as setting
from compass.utils import util


def _add_field_internal(session, model, configs):
    fields = []
    for config in configs:
        fields.append(utils.add_db_object(
            session, model, False,
            config['NAME'],
            field_type=config.get('FIELD_TYPE', basestring),
            display_type=config.get('DISPLAY_TYPE', 'text'),
            validator=config.get('VALIDATOR', None),
            js_validator=config.get('JS_VALIDATOR', None),
            description=config.get('DESCRIPTION', None)
        ))
    return fields


def add_os_field_internal(session):
    env_locals = {}
    env_locals.update(metadata_validator.VALIDATOR_LOCALS)
    env_locals.update(metadata_callback.CALLBACK_LOCALS)
    configs = util.load_configs(
        setting.OS_FIELD_DIR,
        env_locals=env_locals
    )
    return _add_field_internal(
        session, models.OSConfigField, configs
    )


def add_package_field_internal(session):
    env_locals = {}
    env_locals.update(metadata_validator.VALIDATOR_LOCALS)
    env_locals.update(metadata_callback.CALLBACK_LOCALS)
    configs = util.load_configs(
        setting.PACKAGE_FIELD_DIR,
        env_locals=env_locals
    )
    return _add_field_internal(
        session, models.PackageConfigField, configs
    )


def _add_metadata(
    session, field_model, metadata_model, id, path, name, config,
    exception_when_existing=True, parent=None, **kwargs
):
    metadata_self = config.get('_self', {})
    if 'field' in metadata_self:
        field = utils.get_db_object(
            session, field_model, field=metadata_self['field']
        )
    else:
        field = None
    metadata = utils.add_db_object(
        session, metadata_model, exception_when_existing,
        id, path, name=name, parent=parent, field=field,
        display_name=metadata_self.get('display_name', name),
        description=metadata_self.get('description', None),
        is_required=metadata_self.get('is_required', False),
        required_in_whole_config=metadata_self.get(
            'required_in_whole_config', False),
        mapping_to=metadata_self.get('mapping_to', None),
        validator=metadata_self.get('validator', None),
        js_validator=metadata_self.get('js_validator', None),
        default_value=metadata_self.get('default_value', None),
        default_callback=metadata_self.get('default_callback', None),
        default_callback_params=metadata_self.get(
            'default_callback_params', {}),
        options=metadata_self.get('options', None),
        options_callback=metadata_self.get('options_callback', None),
        options_callback_params=metadata_self.get(
            'options_callback_params', {}),
        autofill_callback=metadata_self.get(
            'autofill_callback', None),
        autofill_callback_params=metadata_self.get(
            'autofill_callback_params', {}),
        required_in_options=metadata_self.get(
            'required_in_options', False),
        **kwargs
    )
    for key, value in config.items():
        if key not in '_self':
            _add_metadata(
                session, field_model, metadata_model,
                id, '%s/%s' % (path, key), key, value,
                exception_when_existing=exception_when_existing,
                parent=metadata, **kwargs
            )
    return metadata


def add_os_metadata_internal(session, exception_when_existing=True):
    os_metadatas = []
    env_locals = {}
    env_locals.update(metadata_validator.VALIDATOR_LOCALS)
    env_locals.update(metadata_callback.CALLBACK_LOCALS)
    configs = util.load_configs(
        setting.OS_METADATA_DIR,
        env_locals=env_locals
    )
    for config in configs:
        os = utils.get_db_object(
            session, models.OperatingSystem, name=config['OS']
        )
        for key, value in config['METADATA'].items():
            os_metadatas.append(_add_metadata(
                session, models.OSConfigField,
                models.OSConfigMetadata,
                os.id, key, key, value,
                exception_when_existing=exception_when_existing,
                parent=None
            ))
    return os_metadatas


def add_package_metadata_internal(session, exception_when_existing=True):
    package_metadatas = []
    env_locals = {}
    env_locals.update(metadata_validator.VALIDATOR_LOCALS)
    env_locals.update(metadata_callback.CALLBACK_LOCALS)
    configs = util.load_configs(
        setting.PACKAGE_METADATA_DIR,
        env_locals=env_locals
    )
    for config in configs:
        adapter = utils.get_db_object(
            session, models.Adapter, name=config['ADAPTER']
        )
        for key, value in config['METADATA'].items():
            package_metadatas.append(_add_metadata(
                session, models.PackageConfigField,
                models.PackageConfigMetadata,
                adapter.id, key, key, value,
                exception_when_existing=exception_when_existing,
                parent=None
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
    config_path, config_key, config,
    metadata, whole_check,
    **kwargs
):
    if '_self' not in metadata:
        if isinstance(config, dict):
            _validate_config(
                config_path, config, metadata, whole_check, **kwargs
            )
        return
    field_type = metadata['_self'].get('field_type', 'basestring')
    if not isinstance(config, field_type):
        raise exception.InvalidParameter(
            '%s config type is not %s' % (config_path, field_type)
        )
    required_in_options = metadata['_self'].get(
        'required_in_options', False
    )
    options = metadata['_self'].get('options', None)
    if required_in_options:
        if field_type in [int, basestring, float, bool]:
            if options and config not in options:
                raise exception.InvalidParameter(
                    '%s config is not in %s' % (config_path, options)
                )
        elif field_type in [list, tuple]:
            if options and not set(config).issubset(set(options)):
                raise exception.InvalidParameter(
                    '%s config is not in %s' % (config_path, options)
                )
        elif field_type == dict:
            if options and not set(config.keys()).issubset(set(options)):
                raise exception.InvalidParameter(
                    '%s config is not in %s' % (config_path, options)
                )
    validator = metadata['_self'].get('validator', None)
    if validator:
        if not validator(config_key, config, **kwargs):
            raise exception.InvalidParameter(
                '%s config is invalid' % config_path
            )
    if isinstance(config, dict):
        _validate_config(
            config_path, config, metadata, whole_check, **kwargs
        )


def _validate_config(
    config_path, config, metadata, whole_check,
    **kwargs
):
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
            key, config[key], specified[key], whole_check,
            **kwargs
        )
    for key in not_found_keys:
        for general_key, general_value in generals.items():
            _validate_self(
                '%s/%s' % (config_path, key),
                key, config[key], general_value, whole_check,
                **kwargs
            )


def _autofill_self_config(
    config_path, config_key, config,
    metadata,
    **kwargs
):
    if '_self' not in metadata:
        if isinstance(config, dict):
            _autofill_config(
                config_path, config, metadata, **kwargs
            )
        return config
    autofill_callback = metadata['_self'].get(
        'autofill_callback', None
    )
    autofill_callback_params = metadata['_self'].get(
        'autofill_callback_params', {}
    )
    callback_params = dict(kwargs)
    if autofill_callback_params:
        callback_params.update(autofill_callback_params)
    if autofill_callback:
        config = autofill_callback(
            config_key, config, **callback_params
        )
    if config is None:
        new_config = {}
    else:
        new_config = config
    if isinstance(new_config, dict):
        _autofill_config(
            config_path, new_config, metadata, **kwargs
        )
        if new_config:
            config = new_config
    return config


def _autofill_config(
    config_path, config, metadata, **kwargs
):
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
        self_config = _autofill_self_config(
            '%s/%s' % (config_path, key),
            key, None, specified[key], **kwargs
        )
        if self_config is not None:
            config[key] = self_config
    for key in intersect_keys:
        config[key] = _autofill_self_config(
            '%s/%s' % (config_path, key),
            key, config[key], specified[key],
            **kwargs
        )
    for key in not_found_keys:
        for general_key, general_value in generals.items():
            config[key] = _autofill_self_config(
                '%s/%s' % (config_path, key),
                key, config[key], general_value,
                **kwargs
            )
    return config


def validate_config_internal(
    config, metadata, whole_check, **kwargs
):
    _validate_config('', config, metadata, whole_check, **kwargs)


def autofill_config_internal(
    config, metadata, **kwargs
):
    return _autofill_config('', config, metadata, **kwargs)
