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
from compass.db.api import database
from compass.db.api import permission
from compass.db.api import user as user_api
from compass.db.api import utils
from compass.db import models

from compass.utils import setting_wrapper as setting
from compass.utils import util


SUPPORTED_FIELDS = ['mac', 'tag']
ADDED_FIELDS = ['mac']
OPTIONAL_ADDED_FIELDS = ['ipmi_credentials', 'tag']
UPDATED_FIELDS = ['ipmi_credentials', 'tag']
PATCHED_FIELDS = ['patched_ipmi_credentials']
RESP_FIELDS = [
    'id', 'mac', 'ipmi_credentials',
    'tag', 'created_at', 'updated_at'
]


def _check_ipmi_credentials_ip(ip):
    utils.check_ip(ip)


def _check_ipmi_credentials(ipmi_credentials):
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
        if hasattr(this_module, check_ipmi_credential_field):
            getattr(this_module, check_ipmi_credential_field)(
                ipmi_credentials[key]
            )
        else:
            logging.debug(
                'function %s is not defined', check_ipmi_credential_field
            )
    

@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters([])
def get_machine(getter, machine_id, **kwargs):
    """get field dict of a machine."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_LIST_MACHINES)
        return utils.get_db_object(
            session, models.Machine, True, id=machine_id
        ).to_dict()


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters(optional_support_keys=SUPPORTED_FIELDS)
def list_machines(lister, **filters):
    """List machines."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, lister, permission.PERMISSION_LIST_MACHINES)
        return [
            machine.to_dict()
            for machine in utils.list_db_objects(
                 session, models.Machine, **filters
            )
        ]


@utils.wrap_to_dict(RESP_FIELDS)
@utils.input_validates(ipmi_credentials=_check_ipmi_credentials)
@utils.supported_filters(optional_support_keys=UPDATED_FIELDS)
def update_machine(updater, machine_id, **kwargs):
    """Update a machine."""
    with database.session() as session:
         user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_UPDATE_MACHINE)
         machine = utils.get_db_object(session, models.Machine, id=machine_id)
         utils.update_db_object(session, machine, **kwargs)
         return machine.to_dict()


@utils.wrap_to_dict(RESP_FIELDS)
@utils.input_validates(ipmi_credentials=_check_ipmi_credentials)
@utils.supported_filters(optional_support_keys=PATCHED_FIELDS)
def patch_machine(updater, machine_id, **kwargs):
    """Update a switch."""
    with database.session() as session:
         user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_UDPATE_MACHINE)
         machine = utils.get_db_object(session, models.Machine, id=machine_id)
         utils.update_db_object(session, machine, **kwargs)
         machine_dict = machine.to_dict()
         utils.validates(
             [], {'ipmi_credentials': _check_ipmi_credentials},
             **machine_dict
         )
         return machine_dict


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters()
def del_machine(deleter, machine_id, **kwargs):
    """Delete a machine."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, deleter, permission.PERMISSION_DEL_MACHINE)
        machine = utils.get_db_object(session, models.Switch, id=machine_id)
        utils.del_db_object(session, machine)
        return machine.to_dict()
