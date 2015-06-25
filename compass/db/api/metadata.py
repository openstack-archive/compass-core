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
OSES_METADATA_UI_CONVERTERS = None
FLAVORS_METADATA_UI_CONVERTERS = None


def _get_field_from_configuration(configs):
    """Get fields from configurations."""
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


def _get_os_fields_from_configuration():
    """Get os fields from os field config dir."""
    env_locals = {}
    env_locals.update(metadata_validator.VALIDATOR_LOCALS)
    env_locals.update(metadata_callback.CALLBACK_LOCALS)
    configs = util.load_configs(
        setting.OS_FIELD_DIR,
        env_locals=env_locals
    )
    return _get_field_from_configuration(
        configs
    )


def _get_package_fields_from_configuration():
    """Get package fields from package field config dir."""
    env_locals = {}
    env_locals.update(metadata_validator.VALIDATOR_LOCALS)
    env_locals.update(metadata_callback.CALLBACK_LOCALS)
    configs = util.load_configs(
        setting.PACKAGE_FIELD_DIR,
        env_locals=env_locals
    )
    return _get_field_from_configuration(
        configs
    )


def _get_flavor_fields_from_configuration():
    """Get flavor fields from flavor field config dir."""
    env_locals = {}
    env_locals.update(metadata_validator.VALIDATOR_LOCALS)
    env_locals.update(metadata_callback.CALLBACK_LOCALS)
    configs = util.load_configs(
        setting.FLAVOR_FIELD_DIR,
        env_locals=env_locals
    )
    return _get_field_from_configuration(
        configs
    )


def _get_metadata_from_configuration(
    path, name, config,
    fields, **kwargs
):
    """Recursively get metadata from configuration.

    Args:
       path: used to indicate the path to the root element.
             mainly for trouble shooting.
       name: the key of the metadata section.
       config: the value of the metadata section.
       fields: all fields defined in os fields or package fields dir.
    """
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
    # mapping to may contain $ like $partition. Here we replace the
    # $partition to the key of the correspendent config. The backend then
    # can use this kind of feature to support multi partitions when we
    # only declare the partition metadata in one place.
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
    # Key extension used to do two things:
    # one is to return the extended metadata that $<something>
    # will be replace to possible extensions.
    # The other is to record the $<something> to extended value
    # and used in future mapping_to subsititution.
    # TODO(grace): select proper name instead of key_extensions if
    # you think it is better.
    # Suppose key_extension is {'$partition': ['/var', '/']} for $partition
    # the metadata for $partition will be mapped to {
    # '/var': ..., '/': ...} and kwargs={'partition': '/var'} and
    # kwargs={'partition': '/'} will be parsed to recursive metadata parsing
    # for sub metadata under '/var' and '/'. Then in the metadata parsing
    # for the sub metadata, this kwargs will be used to substitute mapping_to.
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
                metadata[extended_key] = _get_metadata_from_configuration(
                    '%s/%s' % (path, extended_key), extended_key, value,
                    fields, **sub_kwargs
                )
        else:
            if key.startswith('$'):
                general_keys.append(key)
            metadata[key] = _get_metadata_from_configuration(
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


def _get_oses_metadata_from_configuration():
    """Get os metadata from os metadata config dir."""
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
            os_metadata[key] = _get_metadata_from_configuration(
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


def _get_packages_metadata_from_configuration():
    """Get package metadata from package metadata config dir."""
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
            package_metadata[key] = _get_metadata_from_configuration(
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


def _get_flavors_metadata_from_configuration():
    """Get flavor metadata from flavor metadata config dir."""
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
            flavor_metadata[key] = _get_metadata_from_configuration(
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


def _load_metadata(force_reload=False):
    """Load metadata information into memory.

    If force_reload, the metadata information will be reloaded
    even if the metadata is already loaded.
    """
    adapter_api.load_adapters_internal(force_reload=force_reload)
    global OS_FIELDS
    if force_reload or OS_FIELDS is None:
        OS_FIELDS = _get_os_fields_from_configuration()
    global PACKAGE_FIELDS
    if force_reload or PACKAGE_FIELDS is None:
        PACKAGE_FIELDS = _get_package_fields_from_configuration()
    global FLAVOR_FIELDS
    if force_reload or FLAVOR_FIELDS is None:
        FLAVOR_FIELDS = _get_flavor_fields_from_configuration()
    global OSES_METADATA
    if force_reload or OSES_METADATA is None:
        OSES_METADATA = _get_oses_metadata_from_configuration()
    global PACKAGES_METADATA
    if force_reload or PACKAGES_METADATA is None:
        PACKAGES_METADATA = _get_packages_metadata_from_configuration()
    global FLAVORS_METADATA
    if force_reload or FLAVORS_METADATA is None:
        FLAVORS_METADATA = _get_flavors_metadata_from_configuration()
    global OSES_METADATA_UI_CONVERTERS
    if force_reload or OSES_METADATA_UI_CONVERTERS is None:
        OSES_METADATA_UI_CONVERTERS = (
            _get_oses_metadata_ui_converters_from_configuration()
        )
    global FLAVORS_METADATA_UI_CONVERTERS
    if force_reload or FLAVORS_METADATA_UI_CONVERTERS is None:
        FLAVORS_METADATA_UI_CONVERTERS = (
            _get_flavors_metadata_ui_converters_from_configuration()
        )


def _get_oses_metadata_ui_converters_from_configuration():
    """Get os metadata ui converters from os metadata mapping config dir.

    os metadata ui converter is used to convert os metadata to
    the format UI can understand and show.
    """
    oses_metadata_ui_converters = {}
    configs = util.load_configs(setting.OS_MAPPING_DIR)
    for config in configs:
        os_name = config['OS']
        oses_metadata_ui_converters[os_name] = config.get('CONFIG_MAPPING', {})

    oses = adapter_api.OSES
    parents = {}
    for os_name, os in oses.items():
        parent = os.get('parent', None)
        parents[os_name] = parent
    for os_name, os in oses.items():
        oses_metadata_ui_converters[os_name] = util.recursive_merge_dict(
            os_name, oses_metadata_ui_converters, parents
        )
    return oses_metadata_ui_converters


def _get_flavors_metadata_ui_converters_from_configuration():
    """Get flavor metadata ui converters from flavor mapping config dir."""
    flavors_metadata_ui_converters = {}
    configs = util.load_configs(setting.FLAVOR_MAPPING_DIR)
    for config in configs:
        adapter_name = config['ADAPTER']
        flavor_name = config['FLAVOR']
        flavors_metadata_ui_converters.setdefault(
            adapter_name, {}
        )[flavor_name] = config.get('CONFIG_MAPPING', {})
    adapters = adapter_api.ADAPTERS
    parents = {}
    for adapter_name, adapter in adapters.items():
        parent = adapter.get('parent', None)
        parents[adapter_name] = parent
    for adapter_name, adapter in adapters.items():
        flavors_metadata_ui_converters[adapter_name] = (
            util.recursive_merge_dict(
                adapter_name, flavors_metadata_ui_converters, parents
            )
        )
    return flavors_metadata_ui_converters


def get_packages_metadata_internal(force_reload=False):
    """Get deployable package metadata."""
    _load_metadata(force_reload=force_reload)
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
    """Get deployable flavor metadata."""
    _load_metadata(force_reload=force_reload)
    metadata_mapping = {}
    adapters_flavors = adapter_api.ADAPTERS_FLAVORS
    for adapter_name, adapter_flavors in adapters_flavors.items():
        adapter = adapter_api.ADAPTERS[adapter_name]
        if not adapter.get('deployable'):
            logging.info(
                'ignore metadata since its adapter %s is not deployable',
                adapter_name
            )
            continue
        for flavor_name, flavor in adapter_flavors.items():
            flavor_metadata = FLAVORS_METADATA.get(
                adapter_name, {}
            ).get(flavor_name, {})
            metadata = _filter_metadata(flavor_metadata)
            metadata_mapping.setdefault(
                adapter_name, {}
            )[flavor_name] = metadata
    return metadata_mapping


def get_flavors_metadata_ui_converters_internal(force_reload=False):
    """Get usable flavor metadata ui converters."""
    _load_metadata(force_reload=force_reload)
    return FLAVORS_METADATA_UI_CONVERTERS


def get_oses_metadata_internal(force_reload=False):
    """Get deployable os metadata."""
    _load_metadata(force_reload=force_reload)
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


def get_oses_metadata_ui_converters_internal(force_reload=False):
    """Get usable os metadata ui converters."""
    _load_metadata(force_reload=force_reload)
    return OSES_METADATA_UI_CONVERTERS
