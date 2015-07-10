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
import re

from compass.db.api import database
from compass.db.api import permission
from compass.db.api import user as user_api
from compass.db.api import utils
from compass.db import exception
from compass.db import models

from compass.utils import setting_wrapper as setting
from compass.utils import util


SUPPORTED_FIELDS = ['mac', 'tag', 'location']
IGNORE_FIELDS = ['id', 'created_at', 'updated_at']
UPDATED_FIELDS = ['ipmi_credentials', 'tag', 'location']
PATCHED_FIELDS = [
    'patched_ipmi_credentials', 'patched_tag',
    'patched_location'
]
RESP_FIELDS = [
    'id', 'mac', 'ipmi_credentials', 'switches', 'switch_ip',
    'port', 'vlans',
    'tag', 'location', 'created_at', 'updated_at'
]
RESP_DEPLOY_FIELDS = [
    'status', 'machine'
]


def _get_machine(machine_id, session=None, **kwargs):
    """Get machine by id."""
    if isinstance(machine_id, (int, long)):
        return utils.get_db_object(
            session, models.Machine,
            id=machine_id, **kwargs
        )
    raise exception.InvalidParameter(
        'machine id %s type is not int compatible' % machine_id
    )


def get_machine_internal(machine_id, session=None, **kwargs):
    """Helper function to other files under db/api."""
    return _get_machine(machine_id, session=session, **kwargs)


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_MACHINES
)
@utils.wrap_to_dict(RESP_FIELDS)
def get_machine(
    machine_id, exception_when_missing=True,
    user=None, session=None, **kwargs
):
    """get a machine."""
    return _get_machine(
        machine_id, session=session,
        exception_when_missing=exception_when_missing
    )


@utils.supported_filters(
    optional_support_keys=SUPPORTED_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_MACHINES
)
@utils.output_filters(
    tag=utils.general_filter_callback,
    location=utils.general_filter_callback
)
@utils.wrap_to_dict(RESP_FIELDS)
def list_machines(user=None, session=None, **filters):
    """List machines."""
    return utils.list_db_objects(
        session, models.Machine, **filters
    )


@utils.wrap_to_dict(RESP_FIELDS)
def _update_machine(machine_id, session=None, **kwargs):
    """Update a machine."""
    machine = _get_machine(machine_id, session=session)
    return utils.update_db_object(session, machine, **kwargs)


@utils.supported_filters(
    optional_support_keys=UPDATED_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(ipmi_credentials=utils.check_ipmi_credentials)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_MACHINE
)
def update_machine(machine_id, user=None, session=None, **kwargs):
    """Update a machine."""
    return _update_machine(
        machine_id, session=session, **kwargs
    )


# replace [ipmi_credentials, tag, location] to
# [patched_ipmi_credentials, patched_tag, patched_location]
# in kwargs. It tells db these fields will be patched.
@utils.replace_filters(
    ipmi_credentials='patched_ipmi_credentials',
    tag='patched_tag',
    location='patched_location'
)
@utils.supported_filters(
    optional_support_keys=PATCHED_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@utils.output_validates(ipmi_credentials=utils.check_ipmi_credentials)
@user_api.check_user_permission(
    permission.PERMISSION_ADD_MACHINE
)
def patch_machine(machine_id, user=None, session=None, **kwargs):
    """Patch a machine."""
    return _update_machine(
        machine_id, session=session, **kwargs
    )


def _check_machine_deletable(machine):
    """Check a machine deletable."""
    if machine.host:
        host = machine.host
        raise exception.NotAcceptable(
            'machine %s has host %s on it' % (
                machine.mac, host.name
            )
        )


@utils.supported_filters()
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_DEL_MACHINE
)
@utils.wrap_to_dict(RESP_FIELDS)
def del_machine(machine_id, user=None, session=None, **kwargs):
    """Delete a machine."""
    machine = _get_machine(machine_id, session=session)
    _check_machine_deletable(machine)
    return utils.del_db_object(session, machine)


@utils.supported_filters(optional_support_keys=['poweron'])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_DEPLOY_HOST
)
@utils.wrap_to_dict(
    RESP_DEPLOY_FIELDS,
    machine=RESP_FIELDS
)
def poweron_machine(
    machine_id, poweron={}, user=None, session=None, **kwargs
):
    """power on machine."""
    from compass.tasks import client as celery_client
    machine = _get_machine(
        machine_id, session=session
    )
    celery_client.celery.send_task(
        'compass.tasks.poweron_machine',
        (machine_id,)
    )
    return {
        'status': 'poweron %s action sent' % machine.mac,
        'machine': machine
    }


@utils.supported_filters(optional_support_keys=['poweroff'])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_DEPLOY_HOST
)
@utils.wrap_to_dict(
    RESP_DEPLOY_FIELDS,
    machine=RESP_FIELDS
)
def poweroff_machine(
    machine_id, poweroff={}, user=None, session=None, **kwargs
):
    """power off machine."""
    from compass.tasks import client as celery_client
    machine = _get_machine(
        machine_id, session=session
    )
    celery_client.celery.send_task(
        'compass.tasks.poweroff_machine',
        (machine_id,)
    )
    return {
        'status': 'poweroff %s action sent' % machine.mac,
        'machine': machine
    }


@utils.supported_filters(optional_support_keys=['reset'])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_DEPLOY_HOST
)
@utils.wrap_to_dict(
    RESP_DEPLOY_FIELDS,
    machine=RESP_FIELDS
)
def reset_machine(
    machine_id, reset={}, user=None, session=None, **kwargs
):
    """reset machine."""
    from compass.tasks import client as celery_client
    machine = _get_machine(
        machine_id, session=session
    )
    celery_client.celery.send_task(
        'compass.tasks.reset_machine',
        (machine_id,)
    )
    return {
        'status': 'reset %s action sent' % machine.mac,
        'machine': machine
    }
