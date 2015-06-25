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
import copy
import logging
import string

from compass.db.api import adapter as adapter_api
from compass.db.api import database
from compass.db.api import utils
from compass.db import callback as metadata_callback
from compass.db import exception
from compass.db import models
from compass.db import validator as metadata_validator


from compass.utils import setting_wrapper as setting
from compass.utils import util


OS_FIELDS = None
PACKAGE_FIELDS = None
FLAVOR_FIELDS = None
OSES_METADATA = None
PACKAGES_METADATA = None
FLAVORS_METADATA = None
OSES_METADATA_MAPPING = None
FLAVORS_METADATA_MAPPING = None


def _get_field(configs):
    fields = {}
    for config in configs:
        if not isinstance(config, dict):
            raise exception.InvalidParameter(
                'config %s is not dict' % config
            )
        field_name = config['NAME']
        fields[field_name] = {
            'name': field_name,
            'id': field_name,
            'field_type': config.get('FIELD_TYPE', basestring),
            'display_type': config.get('DISPLAY_TYPE', 'text'),
            'validator': config.get('VALIDATOR', None),
            'js_validator': config.get('JS_VALIDATOR', None),
            'description': config.get('DESCRIPTION', field_name)
        }
    return fields


def _get_os_fields():
    env_locals = {}
    env_locals.update(metadata_validator.VALIDATOR_LOCALS)
    env_locals.update(metadata_callback.CALLBACK_LOCALS)
    configs = util.load_configs(
        setting.OS_FIELD_DIR,
        env_locals=env_locals
    )
    return _get_field(
        configs
    )


def _get_package_fields():
    env_locals = {}
    env_locals.update(metadata_validator.VALIDATOR_LOCALS)
    env_locals.update(metadata_callback.CALLBACK_LOCALS)
    configs = util.load_configs(
        setting.PACKAGE_FIELD_DIR,
        env_locals=env_locals
    )
    return _get_field(
        configs
    )


def _get_flavor_fields():
    env_locals = {}
    env_locals.update(metadata_validator.VALIDATOR_LOCALS)
    env_locals.update(metadata_callback.CALLBACK_LOCALS)
    configs = util.load_configs(
        setting.FLAVOR_FIELD_DIR,
        env_locals=env_locals
    )
    return _get_field(
        configs
    )


def _get_metadata(
    path, name, config,
    fields, **kwargs
):
    if not isinstance(config, dict):
        raise exception.InvalidParameter(
            '%s config %s is not dict' % (path, config)
        )
    metadata_self = config.get('_self', {})
    if 'field' in metadata_self:
        field_name = metadata_self['field']
        field = fields[field_name]
    else:
        field = {}
    mapping_to_template = metadata_self.get('mapping_to', None)
    if mapping_to_template:
        mapping_to = string.Template(
            mapping_to_template
        ).safe_substitute(
            **kwargs
        )
    else:
        mapping_to = None
    self_metadata = {
        'name': name,
        'display_name': metadata_self.get('display_name', name),
        'field_type': field.get('field_type', dict),
        'display_type': field.get('display_type', None),
        'description': metadata_self.get(
            'description', field.get('description', None)
        ),
        'is_required': metadata_self.get('is_required', False),
        'required_in_whole_config': metadata_self.get(
            'required_in_whole_config', False),
        'mapping_to': mapping_to,
        'validator': metadata_self.get(
            'validator', field.get('validator', None)
        ),
        'js_validator': metadata_self.get(
            'js_validator', field.get('js_validator', None)
        ),
        'default_value': metadata_self.get('default_value', None),
        'default_callback': metadata_self.get('default_callback', None),
        'default_callback_params': metadata_self.get(
            'default_callback_params', {}),
        'options': metadata_self.get('options', None),
        'options_callback': metadata_self.get('options_callback', None),
        'options_callback_params': metadata_self.get(
            'options_callback_params', {}),
        'autofill_callback': metadata_self.get(
            'autofill_callback', None),
        'autofill_callback_params': metadata_self.get(
            'autofill_callback_params', {}),
        'required_in_options': metadata_self.get(
            'required_in_options', False)
    }
    self_metadata.update(kwargs)
    metadata = {'_self': self_metadata}
    key_extensions = metadata_self.get('key_extensions', {})
    general_keys = []
    for key, value in config.items():
        if key.startswith('_'):
            continue
        if key in key_extensions:
            if not key.startswith('$'):
                raise exception.InvalidParameter(
                    '%s subkey %s should start with $' % (
                        path, key
                    )
                )
            extended_keys = key_extensions[key]
            for extended_key in extended_keys:
                if extended_key.startswith('$'):
                    raise exception.InvalidParameter(
                        '%s extended key %s should not start with $' % (
                            path, extended_key
                        )
                    )
                sub_kwargs = dict(kwargs)
                sub_kwargs[key[1:]] = extended_key
                metadata[extended_key] = _get_metadata(
                    '%s/%s' % (path, extended_key), extended_key, value,
                    fields, **sub_kwargs
                )
        else:
            if key.startswith('$'):
                general_keys.append(key)
            metadata[key] = _get_metadata(
                '%s/%s' % (path, key), key, value,
                fields, **kwargs
            )
        if len(general_keys) > 1:
            raise exception.InvalidParameter(
                'foud multi general keys in %s: %s' % (
                    path, general_keys
                )
            )
    return metadata


def _get_oses_metadata():
    oses_metadata = {}
    env_locals = {}
    env_locals.update(metadata_validator.VALIDATOR_LOCALS)
    env_locals.update(metadata_callback.CALLBACK_LOCALS)
    configs = util.load_configs(
        setting.OS_METADATA_DIR,
        env_locals=env_locals
    )
    for config in configs:
        os_name = config['OS']
        os_metadata = oses_metadata.setdefault(os_name, {})
        for key, value in config['METADATA'].items():
            os_metadata[key] = _get_metadata(
                key, key, value, OS_FIELDS
            )

    oses = adapter_api.OSES
    parents = {}
    for os_name, os in oses.items():
        parent = os.get('parent', None)
        parents[os_name] = parent
    for os_name, os in oses.items():
        oses_metadata[os_name] = util.recursive_merge_dict(
            os_name, oses_metadata, parents
        )
    return oses_metadata


def _get_packages_metadata():
    packages_metadata = {}
    env_locals = {}
    env_locals.update(metadata_validator.VALIDATOR_LOCALS)
    env_locals.update(metadata_callback.CALLBACK_LOCALS)
    configs = util.load_configs(
        setting.PACKAGE_METADATA_DIR,
        env_locals=env_locals
    )
    for config in configs:
        adapter_name = config['ADAPTER']
        package_metadata = packages_metadata.setdefault(adapter_name, {})
        for key, value in config['METADATA'].items():
            package_metadata[key] = _get_metadata(
                key, key, value, PACKAGE_FIELDS
            )
    adapters = adapter_api.ADAPTERS
    parents = {}
    for adapter_name, adapter in adapters.items():
        parent = adapter.get('parent', None)
        parents[adapter_name] = parent
    for adapter_name, adapter in adapters.items():
        packages_metadata[adapter_name] = util.recursive_merge_dict(
            adapter_name, packages_metadata, parents
        )
    return packages_metadata


def _get_flavors_metadata():
    flavors_metadata = {}
    env_locals = {}
    env_locals.update(metadata_validator.VALIDATOR_LOCALS)
    env_locals.update(metadata_callback.CALLBACK_LOCALS)
    configs = util.load_configs(
        setting.FLAVOR_METADATA_DIR,
        env_locals=env_locals
    )
    for config in configs:
        adapter_name = config['ADAPTER']
        flavor_name = config['FLAVOR']
        flavor_metadata = flavors_metadata.setdefault(
            adapter_name, {}
        ).setdefault(flavor_name, {})
        for key, value in config['METADATA'].items():
            flavor_metadata[key] = _get_metadata(
                key, key, value, FLAVOR_FIELDS
            )

    packages_metadata = PACKAGES_METADATA
    adapters_flavors = adapter_api.ADAPTERS_FLAVORS
    for adapter_name, adapter_flavors in adapters_flavors.items():
        package_metadata = packages_metadata.get(adapter_name, {})
        for flavor_name, flavor in adapter_flavors.items():
            flavor_metadata = flavors_metadata.setdefault(
                adapter_name, {}
            ).setdefault(flavor_name, {})
            util.merge_dict(flavor_metadata, package_metadata, override=False)
    return flavors_metadata


def _filter_metadata(metadata, **kwargs):
    if not isinstance(metadata, dict):
        return metadata
    filtered_metadata = {}
    for key, value in metadata.items():
        if key == '_self':
            default_value = value.get('default_value', None)
            if default_value is None:
                default_callback_params = value.get(
                    'default_callback_params', {}
                )
                callback_params = dict(kwargs)
                if default_callback_params:
                    callback_params.update(default_callback_params)
                default_callback = value.get('default_callback', None)
                if default_callback:
                    default_value = default_callback(key, **callback_params)
            options = value.get('options', None)
            if options is None:
                options_callback_params = value.get(
                    'options_callback_params', {}
                )
                callback_params = dict(kwargs)
                if options_callback_params:
                    callback_params.update(options_callback_params)

                options_callback = value.get('options_callback', None)
                if options_callback:
                    options = options_callback(key, **callback_params)
            filtered_metadata[key] = value
            if default_value is not None:
                filtered_metadata[key]['default_value'] = default_value
            if options is not None:
                filtered_metadata[key]['options'] = options
        else:
            filtered_metadata[key] = _filter_metadata(value, **kwargs)
    return filtered_metadata


def add_metadata_internal(force=False):
    adapter_api.add_adapters_internal(force=force)
    global OS_FIELDS
    if force or OS_FIELDS is None:
        OS_FIELDS = _get_os_fields()
    global PACKAGE_FIELDS
    if force or PACKAGE_FIELDS is None:
        PACKAGE_FIELDS = _get_package_fields()
    global FLAVOR_FIELDS
    if force or FLAVOR_FIELDS is None:
        FLAVOR_FIELDS = _get_flavor_fields()
    global OSES_METADATA
    if force or OSES_METADATA is None:
        OSES_METADATA = _get_oses_metadata()
    global PACKAGES_METADATA
    if force or PACKAGES_METADATA is None:
        PACKAGES_METADATA = _get_packages_metadata()
    global FLAVORS_METADATA
    if force or FLAVORS_METADATA is None:
        FLAVORS_METADATA = _get_flavors_metadata()
    global OSES_METADATA_MAPPING
    if force or OSES_METADATA_MAPPING is None:
        OSES_METADATA_MAPPING = _get_oses_metadata_mapping()
    global FLAVORS_METADATA_MAPPING
    if force or FLAVORS_METADATA_MAPPING is None:
        FLAVORS_METADATA_MAPPING = _get_flavors_metadata_mapping()


def _get_oses_metadata_mapping():
    oses_metadata_mapping = {}
    configs = util.load_configs(setting.OS_MAPPING_DIR)
    for config in configs:
        os_name = config['OS']
        oses_metadata_mapping[os_name] = config.get('CONFIG_MAPPING', {})

    oses = adapter_api.OSES
    parents = {}
    for os_name, os in oses.items():
        parent = os.get('parent', None)
        parents[os_name] = parent
    for os_name, os in oses.items():
        oses_metadata_mapping[os_name] = util.recursive_merge_dict(
            os_name, oses_metadata_mapping, parents
        )
    return oses_metadata_mapping


def _get_flavors_metadata_mapping():
    flavors_metadata_mapping = {}
    configs = util.load_configs(setting.FLAVOR_MAPPING_DIR)
    for config in configs:
        adapter_name = config['ADAPTER']
        flavor_name = config['FLAVOR']
        flavors_metadata_mapping.setdefault(
            adapter_name, {}
        )[flavor_name] = config.get('CONFIG_MAPPING', {})
    adapters = adapter_api.ADAPTERS
    parents = {}
    for adapter_name, adapter in adapters.items():
        parent = adapter.get('parent', None)
        parents[adapter_name] = parent
    for adapter_name, adapter in adapters.items():
        flavors_metadata_mapping[adapter_name] = util.recursive_merge_dict(
            adapter_name, flavors_metadata_mapping, parents
        )
    return flavors_metadata_mapping


def get_packages_metadata_internal(force_reload=False):
    add_metadata_internal(force=force_reload)
    metadata_mapping = {}
    adapters = adapter_api.ADAPTERS
    for adapter_name, adapter in adapters.items():
        if adapter.get('deployable'):
            metadata_mapping[adapter_name] = _filter_metadata(
                PACKAGES_METADATA.get(adapter_name, {})
            )
        else:
            logging.info(
                'ignore metadata since its adapter %s is not deployable',
                adapter_name
            )
    return metadata_mapping


def get_flavors_metadata_internal(force_reload=False):
    add_metadata_internal(force=force_reload)
    metadata_mapping = {}
    adapters_flavors = adapter_api.ADAPTERS_FLAVORS
    for adapter_name, adapter_flavors in adapters_flavors.items():
        for flavor_name, flavor in adapter_flavors.items():
            flavor_metadata = FLAVORS_METADATA.get(
                adapter_name, {}
            ).get(flavor_name, {})
            metadata = _filter_metadata(flavor_metadata)
            metadata_mapping.setdefault(
                adapter_name, {}
            )[flavor_name] = metadata
    return metadata_mapping


def get_flavors_metadata_mapping_internal(force_reload=False):
    add_metadata_internal(force=force_reload)
    return FLAVORS_METADATA_MAPPING


def get_oses_metadata_internal(force_reload=False):
    add_metadata_internal(force=force_reload)
    metadata_mapping = {}
    oses = adapter_api.OSES
    for os_name, os in oses.items():
        if os.get('deployable'):
            metadata_mapping[os_name] = _filter_metadata(
                OSES_METADATA.get(os_name, {})
            )
        else:
            logging.info(
                'ignore metadata since its os %s is not deployable',
                os_name
            )
    return metadata_mapping


def get_oses_metadata_mapping_internal(force_reload=False):
    add_metadata_internal(force=force_reload)
    return OSES_METADATA_MAPPING


def _validate_self(
    config_path, config_key, config,
    metadata, whole_check,
    **kwargs
):
    logging.debug('validate config self %s', config_path)
    if '_self' not in metadata:
        if isinstance(config, dict):
            _validate_config(
                config_path, config, metadata, whole_check, **kwargs
            )
        return
    field_type = metadata['_self'].get('field_type', basestring)
    if not isinstance(config, field_type):
        raise exception.InvalidParameter(
            '%s config type is not %s: %s' % (config_path, field_type, config)
        )
    is_required = metadata['_self'].get(
        'is_required', False
    )
    required_in_whole_config = metadata['_self'].get(
        'required_in_whole_config', False
    )
    if isinstance(config, basestring):
        if config == '' and not is_required and not required_in_whole_config:
            # ignore empty config when it is optional
            return
    required_in_options = metadata['_self'].get(
        'required_in_options', False
    )
    options = metadata['_self'].get('options', None)
    if required_in_options:
        if field_type in [int, basestring, float, bool]:
            if options and config not in options:
                raise exception.InvalidParameter(
                    '%s config is not in %s: %s' % (
                        config_path, options, config
                    )
                )
        elif field_type in [list, tuple]:
            if options and not set(config).issubset(set(options)):
                raise exception.InvalidParameter(
                    '%s config is not in %s: %s' % (
                        config_path, options, config
                    )
                )
        elif field_type == dict:
            if options and not set(config.keys()).issubset(set(options)):
                raise exception.InvalidParameter(
                    '%s config is not in %s: %s' % (
                        config_path, options, config
                    )
                )
    validator = metadata['_self'].get('validator', None)
    logging.debug('validate by validator %s', validator)
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
    logging.debug('validate config %s', config_path)
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
                '%s/%s does not find but it is required' % (
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
                '%s/%s does not find but it is required in whole config' % (
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
        if not generals:
            raise exception.InvalidParameter(
                'key %s missing in metadata %s' % (
                    key, config_path
                )
            )
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
    logging.debug(
        'autofill %s by metadata %s', config_path, metadata['_self']
    )
    autofill_callback = metadata['_self'].get(
        'autofill_callback', None
    )
    autofill_callback_params = metadata['_self'].get(
        'autofill_callback_params', {}
    )
    callback_params = dict(kwargs)
    if autofill_callback_params:
        callback_params.update(autofill_callback_params)
    default_value = metadata['_self'].get(
        'default_value', None
    )
    if default_value is not None:
        callback_params['default_value'] = default_value
    options = metadata['_self'].get(
        'options', None
    )
    if options is not None:
        callback_params['options'] = options
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
