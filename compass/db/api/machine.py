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

"""Switch database operations."""
import logging

from compass.db.api import database
from compass.db.api import permission
from compass.db.api import user as user_api
from compass.db.api import utils
from compass.db import exception
from compass.db import models

from compass.utils import setting_wrapper as setting
from compass.utils import util


SUPPORTED_FIELDS = ['mac']
UPDATED_FIELDS = ['ipmi_credentials', 'tag', 'location']
PATCHED_FIELDS = [
    'patched_ipmi_credentials', 'patched_tag',
    'patched_location'
]
RESP_FIELDS = [
    'id', 'mac', 'ipmi_credentials',
    'tag', 'location', 'created_at', 'updated_at'
]


def _check_ipmi_credentials_ip(ip):
    utils.check_ip(ip)


def _check_ipmi_credentials(ipmi_credentials):
    if not ipmi_credentials:
        return
    if not isinstance(ipmi_credentials, dict):
        raise exception.InvalidParameter(
            'invalid ipmi credentials %s' % ipmi_credentials

        )
    for key in ipmi_credentials:
        if key not in ['ip', 'username', 'password']:
            raise exception.InvalidParameter(
                'unrecognized field %s in ipmi credentials %s' % (
                    key, ipmi_credentials
                )
            )
    for key in ['ip', 'username', 'password']:
        if key not in ipmi_credentials:
            raise exception.InvalidParameter(
                'no field %s in ipmi credentials %s' % (
                    key, ipmi_credentials
                )
            )
        check_ipmi_credential_field = '_check_ipmi_credentials_%s' % key
        this_module = globals()
        if check_ipmi_credential_field in this_module:
            this_module[check_ipmi_credential_field](
                ipmi_credentials[key]
            )
        else:
            logging.debug(
                'function %s is not defined', check_ipmi_credential_field
            )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_MACHINES
)
@utils.wrap_to_dict(RESP_FIELDS)
def get_machine(session, getter, machine_id, **kwargs):
    """get field dict of a machine."""
    return utils.get_db_object(
        session, models.Machine, True, id=machine_id
    )


@utils.supported_filters(
    optional_support_keys=SUPPORTED_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_MACHINES
)
@utils.output_filters(
    tag=utils.general_filter_callback,
    location=utils.general_filter_callback
)
@utils.wrap_to_dict(RESP_FIELDS)
def list_machines(session, lister, **filters):
    """List machines."""
    return utils.list_db_objects(
        session, models.Machine, **filters
    )


@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_MACHINE
)
@utils.wrap_to_dict(RESP_FIELDS)
def _update_machine(session, updater, machine_id, **kwargs):
    """Update a machine."""
    machine = utils.get_db_object(session, models.Machine, id=machine_id)
    return utils.update_db_object(session, machine, **kwargs)


@utils.supported_filters(optional_support_keys=UPDATED_FIELDS)
@utils.input_validates(ipmi_credentials=_check_ipmi_credentials)
@database.run_in_session()
def update_machine(session, updater, machine_id, **kwargs):
    return _update_machine(
        session, updater, machine_id, **kwargs
    )


@utils.supported_filters(optional_support_keys=PATCHED_FIELDS)
@database.run_in_session()
@utils.output_validates(ipmi_credentials=_check_ipmi_credentials)
def patch_machine(session, updater, machine_id, **kwargs):
    return _update_machine(
        session, updater, machine_id, **kwargs
    )


@utils.supported_filters()
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_DEL_MACHINE
)
@utils.wrap_to_dict(RESP_FIELDS)
def del_machine(session, deleter, machine_id, **kwargs):
    """Delete a machine."""
    machine = utils.get_db_object(session, models.Switch, id=machine_id)
    return utils.del_db_object(session, machine)
