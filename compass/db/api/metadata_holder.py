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

from compass.db.api import adapter as adapter_api
from compass.db.api import adapter_holder as adapter_holder_api
from compass.db.api import database
from compass.db.api import metadata as metadata_api
from compass.db.api import permission
from compass.db.api import user as user_api
from compass.db.api import utils
from compass.db import exception
from compass.db import models
from compass.utils import setting_wrapper as setting
from compass.utils import util


RESP_METADATA_FIELDS = [
    'os_config', 'package_config'
]
RESP_UI_METADATA_FIELDS = [
    'os_global_config', 'flavor_config'
]


def load_metadatas(force_reload=False):
    """Load metadatas."""
    # TODO(xicheng): today we load metadata in memory as it original
    # format in files in metadata.py. We get these inmemory metadata
    # and do some translation, store the translated metadata into memory
    # too in metadata_holder.py. api can only access the global inmemory
    # data in metadata_holder.py.
    _load_os_metadatas(force_reload=force_reload)
    _load_package_metadatas(force_reload=force_reload)
    _load_flavor_metadatas(force_reload=force_reload)
    _load_os_metadata_ui_converters(force_reload=force_reload)
    _load_flavor_metadata_ui_converters(force_reload=force_reload)


def _load_os_metadata_ui_converters(force_reload=False):
    global OS_METADATA_UI_CONVERTERS
    if force_reload or OS_METADATA_UI_CONVERTERS is None:
        logging.info('load os metadatas ui converters into memory')
        OS_METADATA_UI_CONVERTERS = (
            metadata_api.get_oses_metadata_ui_converters_internal(
                force_reload=force_reload
            )
        )


def _load_os_metadatas(force_reload=False):
    """Load os metadata from inmemory db and map it by os_id."""
    global OS_METADATA_MAPPING
    if force_reload or OS_METADATA_MAPPING is None:
        logging.info('load os metadatas into memory')
        OS_METADATA_MAPPING = metadata_api.get_oses_metadata_internal(
            force_reload=force_reload
        )


def _load_flavor_metadata_ui_converters(force_reload=False):
    """Load flavor metadata ui converters from inmemory db.

    The loaded metadata is mapped by flavor id.
    """
    global FLAVOR_METADATA_UI_CONVERTERS
    if force_reload or FLAVOR_METADATA_UI_CONVERTERS is None:
        logging.info('load flavor metadata ui converters into memory')
        FLAVOR_METADATA_UI_CONVERTERS = {}
        adapters_flavors_metadata_ui_converters = (
            metadata_api.get_flavors_metadata_ui_converters_internal(
                force_reload=force_reload
            )
        )
        for adapter_name, adapter_flavors_metadata_ui_converters in (
            adapters_flavors_metadata_ui_converters.items()
        ):
            for flavor_name, flavor_metadata_ui_converter in (
                adapter_flavors_metadata_ui_converters.items()
            ):
                FLAVOR_METADATA_UI_CONVERTERS[
                    '%s:%s' % (adapter_name, flavor_name)
                ] = flavor_metadata_ui_converter


@util.deprecated
def _load_package_metadatas(force_reload=False):
    """Load deployable package metadata from inmemory db."""
    global PACKAGE_METADATA_MAPPING
    if force_reload or PACKAGE_METADATA_MAPPING is None:
        logging.info('load package metadatas into memory')
        PACKAGE_METADATA_MAPPING = (
            metadata_api.get_packages_metadata_internal(
                force_reload=force_reload
            )
        )


def _load_flavor_metadatas(force_reload=False):
    """Load flavor metadata from inmemory db.

    The loaded metadata are mapped by flavor id.
    """
    global FLAVOR_METADATA_MAPPING
    if force_reload or FLAVOR_METADATA_MAPPING is None:
        logging.info('load flavor metadatas into memory')
        FLAVOR_METADATA_MAPPING = {}
        adapters_flavors_metadata = (
            metadata_api.get_flavors_metadata_internal(
                force_reload=force_reload
            )
        )
        for adapter_name, adapter_flavors_metadata in (
            adapters_flavors_metadata.items()
        ):
            for flavor_name, flavor_metadata in (
                adapter_flavors_metadata.items()
            ):
                FLAVOR_METADATA_MAPPING[
                    '%s:%s' % (adapter_name, flavor_name)
                ] = flavor_metadata


OS_METADATA_MAPPING = None
PACKAGE_METADATA_MAPPING = None
FLAVOR_METADATA_MAPPING = None
OS_METADATA_UI_CONVERTERS = None
FLAVOR_METADATA_UI_CONVERTERS = None


def validate_os_config(
    config, os_id, whole_check=False, **kwargs
):
    """Validate os config."""
    load_metadatas()
    if os_id not in OS_METADATA_MAPPING:
        raise exception.InvalidParameter(
            'os %s is not found in os metadata mapping' % os_id
        )
    _validate_config(
        '', config, OS_METADATA_MAPPING[os_id],
        whole_check, **kwargs
    )


@util.deprecated
def validate_package_config(
    config, adapter_id, whole_check=False, **kwargs
):
    """Validate package config."""
    load_metadatas()
    if adapter_id not in PACKAGE_METADATA_MAPPING:
        raise exception.InvalidParameter(
            'adapter %s is not found in package metedata mapping' % adapter_id
        )
    _validate_config(
        '', config, PACKAGE_METADATA_MAPPING[adapter_id],
        whole_check, **kwargs
    )


def validate_flavor_config(
    config, flavor_id, whole_check=False, **kwargs
):
    """Validate flavor config."""
    load_metadatas()
    if not flavor_id:
        logging.info('There is no flavor, skipping flavor validation...')
    elif flavor_id not in FLAVOR_METADATA_MAPPING:
        raise exception.InvalidParameter(
            'flavor %s is not found in flavor metedata mapping' % flavor_id
        )
    else:
        _validate_config(
            '', config, FLAVOR_METADATA_MAPPING[flavor_id],
            whole_check, **kwargs
        )


def _filter_metadata(metadata, **kwargs):
    """Filter metadata before return it to api.

    Some metadata fields are not json compatible or
    only used in db/api internally.
    We should strip these fields out before return to api.
    """
    if not isinstance(metadata, dict):
        return metadata
    filtered_metadata = {}
    for key, value in metadata.items():
        if key == '_self':
            filtered_metadata[key] = {
                'name': value['name'],
                'description': value.get('description', None),
                'default_value': value.get('default_value', None),
                'is_required': value.get('is_required', False),
                'required_in_whole_config': value.get(
                    'required_in_whole_config', False),
                'js_validator': value.get('js_validator', None),
                'options': value.get('options', None),
                'required_in_options': value.get(
                    'required_in_options', False),
                'field_type': value.get(
                    'field_type_data', 'str'),
                'display_type': value.get('display_type', None),
                'mapping_to': value.get('mapping_to', None)
            }
        else:
            filtered_metadata[key] = _filter_metadata(value, **kwargs)
    return filtered_metadata


@util.deprecated
def _get_package_metadata(adapter_id):
    """get package metadata."""
    load_metadatas()
    if adapter_id not in PACKAGE_METADATA_MAPPING:
        raise exception.RecordNotExists(
            'adpater %s does not exist' % adapter_id
        )
    return _filter_metadata(
        PACKAGE_METADATA_MAPPING[adapter_id]
    )


@util.deprecated
@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_METADATAS
)
@utils.wrap_to_dict(RESP_METADATA_FIELDS)
def get_package_metadata(adapter_id, user=None, session=None, **kwargs):
    """Get package metadata from adapter."""
    return {
        'package_config': _get_package_metadata(adapter_id)
    }


def _get_flavor_metadata(flavor_id):
    """get flavor metadata."""
    load_metadatas()
    if not flavor_id:
        logging.info('There is no flavor id, skipping...')
    elif flavor_id not in FLAVOR_METADATA_MAPPING:
        raise exception.RecordNotExists(
            'flavor %s does not exist' % flavor_id
        )
    else:
        return _filter_metadata(FLAVOR_METADATA_MAPPING[flavor_id])


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_METADATAS
)
@utils.wrap_to_dict(RESP_METADATA_FIELDS)
def get_flavor_metadata(flavor_id, user=None, session=None, **kwargs):
    """Get flavor metadata by flavor."""
    return {
        'package_config': _get_flavor_metadata(flavor_id)
    }


def _get_os_metadata(os_id):
    """get os metadata."""
    load_metadatas()
    if os_id not in OS_METADATA_MAPPING:
        raise exception.RecordNotExists(
            'os %s does not exist' % os_id
        )
    return _filter_metadata(OS_METADATA_MAPPING[os_id])


def _get_os_metadata_ui_converter(os_id):
    """get os metadata ui converter."""
    load_metadatas()
    if os_id not in OS_METADATA_UI_CONVERTERS:
        raise exception.RecordNotExists(
            'os %s does not exist' % os_id
        )
    return OS_METADATA_UI_CONVERTERS[os_id]


def _get_flavor_metadata_ui_converter(flavor_id):
    """get flavor metadata ui converter."""
    load_metadatas()
    if flavor_id not in FLAVOR_METADATA_UI_CONVERTERS:
        raise exception.RecordNotExists(
            'flavor %s does not exist' % flavor_id
        )
    return FLAVOR_METADATA_UI_CONVERTERS[flavor_id]


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_METADATAS
)
@utils.wrap_to_dict(RESP_METADATA_FIELDS)
def get_os_metadata(os_id, user=None, session=None, **kwargs):
    """get os metadatas."""
    return {'os_config': _get_os_metadata(os_id)}


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_METADATAS
)
@utils.wrap_to_dict(RESP_UI_METADATA_FIELDS)
def get_os_ui_metadata(os_id, user=None, session=None, **kwargs):
    """Get os metadata ui converter by os."""
    metadata = _get_os_metadata(os_id)
    metadata_ui_converter = _get_os_metadata_ui_converter(os_id)
    return _get_ui_metadata(metadata, metadata_ui_converter)


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_METADATAS
)
@utils.wrap_to_dict(RESP_UI_METADATA_FIELDS)
def get_flavor_ui_metadata(flavor_id, user=None, session=None, **kwargs):
    """Get flavor ui metadata by flavor."""
    metadata = _get_flavor_metadata(flavor_id)
    metadata_ui_converter = _get_flavor_metadata_ui_converter(flavor_id)
    return _get_ui_metadata(metadata, metadata_ui_converter)


def _get_ui_metadata(metadata, metadata_ui_converter):
    """convert metadata to ui metadata.

     Args:
        metadata: metadata we defined in metadata files.
        metadata_ui_converter: metadata ui converter defined in metadata
                               mapping files. Used to convert orignal
                               metadata to ui understandable metadata.

     Returns:
        ui understandable metadata.
     """
    ui_metadata = {}
    ui_metadata[metadata_ui_converter['mapped_name']] = []
    for mapped_child in metadata_ui_converter['mapped_children']:
        data_dict = {}
        for ui_key, ui_value in mapped_child.items():
            for key, value in ui_value.items():
                if 'data' == key:
                    result_data = []
                    _get_ui_metadata_data(
                        metadata[ui_key], value, result_data
                    )
                    data_dict['data'] = result_data
                else:
                    data_dict[key] = value
        ui_metadata[metadata_ui_converter['mapped_name']].append(data_dict)
    return ui_metadata


def _get_ui_metadata_data(metadata, config, result_data):
    """Get ui metadata data and fill to result."""
    data_dict = {}
    for key, config_value in config.items():
        if isinstance(config_value, dict) and key != 'content_data':
            if key in metadata.keys():
                _get_ui_metadata_data(metadata[key], config_value, result_data)
            else:
                _get_ui_metadata_data(metadata, config_value, result_data)
        elif isinstance(config_value, list):
            option_list = []
            for item in config_value:
                if isinstance(item, dict):
                    option_list.append(item)
                    data_dict[key] = option_list
                else:
                    if isinstance(metadata['_self'][item], bool):
                        data_dict[item] = str(metadata['_self'][item]).lower()
                    else:
                        data_dict[item] = metadata['_self'][item]
        else:
            data_dict[key] = config_value
    if data_dict:
        result_data.append(data_dict)
    return result_data


@util.deprecated
@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_METADATAS
)
@utils.wrap_to_dict(RESP_METADATA_FIELDS)
def get_package_os_metadata(
    adapter_id, os_id,
    user=None, session=None, **kwargs
):
    """Get metadata by adapter and os."""
    adapter = adapter_holder_api.get_adapter(
        adapter_id, user=user, session=session
    )
    os_ids = [os['id'] for os in adapter['supported_oses']]
    if os_id not in os_ids:
        raise exception.InvalidParameter(
            'os %s is not in the supported os list of adapter %s' % (
                os_id, adapter_id
            )
        )
    metadatas = {}
    metadatas['os_config'] = _get_os_metadata(
        os_id
    )
    metadatas['package_config'] = _get_package_metadata(
        adapter_id
    )
    return metadatas


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_METADATAS
)
@utils.wrap_to_dict(RESP_METADATA_FIELDS)
def get_flavor_os_metadata(
    flavor_id, os_id,
    user=None, session=None, **kwargs
):
    """Get metadata by flavor and os."""
    flavor = adapter_holder_api.get_flavor(
        flavor_id, user=user, session=session
    )
    adapter_id = flavor['adapter_id']
    adapter = adapter_holder_api.get_adapter(
        adapter_id, user=user, session=session
    )
    os_ids = [os['id'] for os in adapter['supported_oses']]
    if os_id not in os_ids:
        raise exception.InvalidParameter(
            'os %s is not in the supported os list of adapter %s' % (
                os_id, adapter_id
            )
        )
    metadatas = {}
    metadatas['os_config'] = _get_os_metadata(
        session, os_id
    )
    metadatas['package_config'] = _get_flavor_metadata(
        session, flavor_id
    )
    return metadatas


def _validate_self(
    config_path, config_key, config,
    metadata, whole_check,
    **kwargs
):
    """validate config by metadata self section."""
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
    """validate config by metadata."""
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
    """Autofill config by metadata self section."""
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
    """autofill config by metadata."""
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


def autofill_os_config(
    config, os_id, **kwargs
):
    load_metadatas()
    if os_id not in OS_METADATA_MAPPING:
        raise exception.InvalidParameter(
            'os %s is not found in os metadata mapping' % os_id
        )

    return _autofill_config(
        '', config, OS_METADATA_MAPPING[os_id], **kwargs
    )


def autofill_package_config(
    config, adapter_id, **kwargs
):
    load_metadatas()
    if adapter_id not in PACKAGE_METADATA_MAPPING:
        raise exception.InvalidParameter(
            'adapter %s is not found in package metadata mapping' % adapter_id
        )

    return _autofill_config(
        '', config, PACKAGE_METADATA_MAPPING[adapter_id], **kwargs
    )


def autofill_flavor_config(
    config, flavor_id, **kwargs
):
    load_metadatas()
    if not flavor_id:
        logging.info('There is no flavor, skipping...')
    elif flavor_id not in FLAVOR_METADATA_MAPPING:
        raise exception.InvalidParameter(
            'flavor %s is not found in flavor metadata mapping' % flavor_id
        )
    else:
        return _autofill_config(
            '', config, FLAVOR_METADATA_MAPPING[flavor_id], **kwargs
        )
