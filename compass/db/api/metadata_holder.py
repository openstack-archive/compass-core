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
RESP_FLAVORS_FIELDS = [
    'id', 'name', 'display_name', 'template', 'roles'
]


def load_metadatas(force_reload=False):
    load_os_metadatas_internal(force=force_reload)
    load_package_metadatas_internal(force=force_reload)
    load_flavor_metadatas_internal(force=force_reload)
    load_os_metadatas_ui_internal(force=force_reload)
    load_flavor_metadatas_ui_internal(force=force_reload)


def load_flavors(force_reload=False):
    load_flavors_internal(force=force_reload)


def load_os_metadatas_ui_internal(force=False):
    global OS_METADATA_UI_MAPPING
    if force or not OS_METADATA_UI_MAPPING:
        logging.info('load os metadatas ui converter into memory')
        OS_METADATA_UI_MAPPING = (
            metadata_api.get_oses_metadata_mapping_internal(force_reload=force)
        )


def load_os_metadatas_internal(force=False):
    global OS_METADATA_MAPPING
    if force or not OS_METADATA_MAPPING:
        logging.info('load os metadatas into memory')
        OS_METADATA_MAPPING = metadata_api.get_oses_metadata_internal(
            force_reload=force
        )


def load_flavor_metadatas_ui_internal(force=False):
    global FLAVOR_METADATA_UI_MAPPING
    if force or not FLAVOR_METADATA_UI_MAPPING:
        logging.info('load flavor metadatas ui converter into memory')
        adapters_flavors_metadata_mapping = (
            metadata_api.get_flavors_metadata_mapping_internal(
                force_reload=force
            )
        )
        for adapter_name, adapter_flavors_metadata_mapping in (
            adapters_flavors_metadata_mapping.items()
        ):
            for flavor_name, flavor_metadata_mapping in (
                adapter_flavors_metadata_mapping.items()
            ):
                FLAVOR_METADATA_UI_MAPPING[
                    '%s:%s' % (adapter_name, flavor_name)
                ] = flavor_metadata_mapping


def load_package_metadatas_internal(force=False):
    global PACKAGE_METADATA_MAPPING
    if force or not PACKAGE_METADATA_MAPPING:
        logging.info('load package metadatas into memory')
        PACKAGE_METADATA_MAPPING = (
            metadata_api.get_packages_metadata_internal(force_reload=force)
        )


def load_flavor_metadatas_internal(force=False):
    global FLAVOR_METADATA_MAPPING
    if force or not FLAVOR_METADATA_MAPPING:
        logging.info('load flavor metadatas into memory')
        adapters_flavors_metadata = (
            metadata_api.get_flavors_metadata_internal(force_reload=force)
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


def load_flavors_internal(force=False):
    global FLAVOR_MAPPING
    if force or not FLAVOR_MAPPING:
        logging.info('load flavors into memory')
        adapters_flavors = adapter_api.get_flavors_internal(force_reload=force)
        for adapter_name, adapter_flavors in adapters_flavors.items():
            for flavor_name, flavor in adapter_flavors.items():
                FLAVOR_MAPPING['%s:%s' % (adapter_name, flavor_name)] = flavor


OS_METADATA_MAPPING = {}
PACKAGE_METADATA_MAPPING = {}
FLAVOR_METADATA_MAPPING = {}
OS_METADATA_UI_MAPPING = {}
FLAVOR_METADATA_UI_MAPPING = {}
FLAVOR_MAPPING = {}


def _validate_config(
    config, metadata, whole_check, **kwargs
):
    metadata_api.validate_config_internal(
        config, metadata, whole_check, **kwargs
    )


def validate_os_config(
    config, os_id, whole_check=False, **kwargs
):
    load_os_metadatas_internal()
    if os_id not in OS_METADATA_MAPPING:
        raise exception.InvalidParameter(
            'os %s is not found in os metadata mapping' % os_id
        )
    _validate_config(
        config, OS_METADATA_MAPPING[os_id],
        whole_check, **kwargs
    )


def validate_package_config(
    config, adapter_id, whole_check=False, **kwargs
):
    load_package_metadatas_internal()
    if adapter_id not in PACKAGE_METADATA_MAPPING:
        raise exception.InvalidParameter(
            'adapter %s is not found in package metedata mapping' % adapter_id
        )
    _validate_config(
        config, PACKAGE_METADATA_MAPPING[adapter_id],
        whole_check, **kwargs
    )


def validate_flavor_config(
    config, adapter_name, flavor_name, whole_check=False, **kwargs
):
    load_flavor_metadatas_internal()
    flavor_id = '%s:%s' % (adapter_name, flavor_name)
    if flavor_id not in FLAVOR_METADATA_MAPPING:
        raise exception.InvalidParameter(
            'flavor %s is not found in flavor metedata mapping' % flavor_id
        )
    _validate_config(
        config, FLAVOR_METADATA_MAPPING[flavor_id],
        whole_check, **kwargs
    )


def _filter_metadata(metadata, **kwargs):
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


def get_package_metadata_internal(adapter_id):
    """get package metadata internal."""
    load_package_metadatas_internal()
    if adapter_id not in PACKAGE_METADATA_MAPPING:
        raise exception.RecordNotExists(
            'adpater %s does not exist' % adapter_id
        )
    return _filter_metadata(
        PACKAGE_METADATA_MAPPING[adapter_id]
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_METADATAS
)
@utils.wrap_to_dict(RESP_METADATA_FIELDS)
def get_package_metadata(adapter_id, user=None, session=None, **kwargs):
    return {
        'package_config': get_package_metadata_internal(adapter_id)
    }


def get_flavor_metadata_internal(flavor_id):
    """get flavor metadata internal."""
    load_flavor_metadatas_internal()
    if flavor_id not in FLAVOR_METADATA_MAPPING:
        raise exception.RecordNotExists(
            'flavor %s does not exist' % flavor_id
        )
    return _filter_metadata(FLAVOR_METADATA_MAPPING[flavor_id])


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_METADATAS
)
@utils.wrap_to_dict(RESP_METADATA_FIELDS)
def get_flavor_metadata(flavor_id, user=None, session=None, **kwargs):
    return {
        'package_config': get_flavor_metadata_internal(flavor_id)
    }


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_METADATAS
)
@utils.wrap_to_dict(RESP_FLAVORS_FIELDS)
def list_flavors(user=None, session=None, **filters):
    """List flavors."""
    load_flavors_internal()
    return FLAVOR_MAPPING.values()


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_METADATAS
)
@utils.wrap_to_dict(RESP_FLAVORS_FIELDS)
def get_flavor(flavor_id, user=None, session=None, **kwargs):
    """Get flavor."""
    load_flavors_internal()
    if flavor_id not in FLAVOR_MAPPING:
        raise exception.RecordNotExists(
            'flavor %s does not exist' % flavor_id
        )
    return FLAVOR_MAPPING[flavor_id]


def get_os_metadata_internal(os_id):
    """get os metadata internal."""
    load_os_metadatas_internal()
    if os_id not in OS_METADATA_MAPPING:
        raise exception.RecordNotExists(
            'os %s does not exist' % os_id
        )
    return _filter_metadata(OS_METADATA_MAPPING[os_id])


def get_os_metadata_ui_internal(os_id):
    """get os ui metadata internal."""
    load_os_metadatas_ui_internal()
    if os_id not in OS_METADATA_UI_MAPPING:
        raise exception.RecordNotExists(
            'os %s does not exist' % os_id
        )
    return OS_METADATA_UI_MAPPING[os_id]


def get_flavor_metadata_ui_internal(flavor_id):
    """get flavor ui metadata internal."""
    load_flavor_metadatas_ui_internal()
    if flavor_id not in FLAVOR_METADATA_UI_MAPPING:
        raise exception.RecordNotExists(
            'flavor %s does not exist' % flavor_id
        )
    return FLAVOR_METADATA_UI_MAPPING[flavor_id]


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_METADATAS
)
@utils.wrap_to_dict(RESP_METADATA_FIELDS)
def get_os_metadata(os_id, user=None, session=None, **kwargs):
    """get os metadatas."""
    return {'os_config': get_os_metadata_internal(os_id)}


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_METADATAS
)
@utils.wrap_to_dict(RESP_UI_METADATA_FIELDS)
def get_os_ui_metadata(os_id, user=None, session=None, **kwargs):
    metadata = get_os_metadata(
        os_id, user=user, session=session
    )
    metadata_ui = get_os_metadata_ui_internal(os_id)
    return _get_ui_metadata(metadata.get('os_config', {}), metadata_ui)


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_METADATAS
)
@utils.wrap_to_dict(RESP_UI_METADATA_FIELDS)
def get_flavor_ui_metadata(flavor_id, user=None, session=None, **kwargs):
    metadata = get_flavor_metadata(
        flavor_id, user=user, session=session
    )
    metadata_ui = get_flavor_metadata_ui_internal(flavor_id)
    return _get_ui_metadata(metadata.get('package_config', {}), metadata_ui)


def _get_ui_metadata(metadata, config):
    """convert os_metadata to ui os_metadata."""
    result_config = {}
    result_config[config['mapped_name']] = []
    for mapped_child in config['mapped_children']:
        data_dict = {}
        for config_key, config_value in mapped_child.items():
            for key, value in config_value.items():
                if 'data' == key:
                    result_data = []
                    _get_data(metadata[config_key], value, result_data)
                    data_dict['data'] = result_data
                else:
                    data_dict[key] = value
        result_config[config['mapped_name']].append(data_dict)
    return result_config


def _get_data(metadata, config, result_data):
    data_dict = {}
    for key, config_value in config.items():
        if isinstance(config_value, dict) and key != 'content_data':
            if key in metadata.keys():
                _get_data(metadata[key], config_value, result_data)
            else:
                _get_data(metadata, config_value, result_data)
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
    metadatas['os_config'] = get_os_metadata_internal(
        os_id
    )
    metadatas['package_config'] = get_package_metadata_internal(
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
    flavor = get_flavor(flavor_id, user=user, session=session)
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
    metadatas['os_config'] = get_os_metadata_internal(
        session, os_id
    )
    metadatas['package_config'] = get_flavor_metadata_internal(
        session, flavor_id
    )
    return metadatas


def _autofill_config(
    config, metadatas, **kwargs
):
    return metadata_api.autofill_config_internal(
        config, metadatas, **kwargs
    )


def autofill_os_config(
    config, os_id, **kwargs
):
    load_os_metadatas_internal()
    if os_id not in OS_METADATA_MAPPING:
        raise exception.InvalidParameter(
            'os %s is not found in os metadata mapping' % os_id
        )

    return _autofill_config(
        config, OS_METADATA_MAPPING[os_id], **kwargs
    )


def autofill_package_config(
    config, adapter_id, **kwargs
):
    load_package_metadatas_internal()
    if adapter_id not in PACKAGE_METADATA_MAPPING:
        raise exception.InvalidParameter(
            'adapter %s is not found in package metadata mapping' % adapter_id
        )

    return _autofill_config(
        config, PACKAGE_METADATA_MAPPING[adapter_id], **kwargs
    )


def autofill_flavor_config(
    config, adapter_name, flavor_name, **kwargs
):
    load_flavor_metadatas_internal()
    flavor_id = '%s:%s' % (adapter_name, flavor_name)
    if flavor_id not in FLAVOR_METADATA_MAPPING:
        raise exception.InvalidParameter(
            'flavor %s is not found in flavor metadata mapping' % flavor_id
        )

    return _autofill_config(
        config, FLAVOR_METADATA_MAPPING[flavor_id], **kwargs
    )
