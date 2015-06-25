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

"""Network related database operations."""
import logging
import netaddr
import re

from compass.db.api import database
from compass.db.api import permission
from compass.db.api import user as user_api
from compass.db.api import utils
from compass.db import exception
from compass.db import models


SUPPORTED_FIELDS = ['subnet', 'name']
RESP_FIELDS = [
    'id', 'name', 'subnet', 'created_at', 'updated_at'
]
ADDED_FIELDS = ['subnet']
OPTIONAL_ADDED_FIELDS = ['name']
IGNORE_FIELDS = [
    'id', 'created_at', 'updated_at'
]
UPDATED_FIELDS = ['subnet', 'name']


def _check_subnet(subnet):
    """Check subnet format is correct."""
    try:
        netaddr.IPNetwork(subnet)
    except Exception as error:
        logging.exception(error)
        raise exception.InvalidParameter(
            'subnet %s format unrecognized' % subnet)


@utils.supported_filters(optional_support_keys=SUPPORTED_FIELDS)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_SUBNETS
)
@utils.wrap_to_dict(RESP_FIELDS)
def list_subnets(user=None, session=None, **filters):
    """List subnets."""
    return utils.list_db_objects(
        session, models.Subnet, **filters
    )


def _get_subnet(subnet_id, session=None, **kwargs):
    """Get subnet by subnet id."""
    if isinstance(subnet_id, (int, long)):
        return utils.get_db_object(
            session, models.Subnet,
            id=subnet_id, **kwargs
        )
    raise exception.InvalidParameter(
        'subnet id %s type is not int compatible' % subnet_id
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_SUBNETS
)
@utils.wrap_to_dict(RESP_FIELDS)
def get_subnet(
    subnet_id, exception_when_missing=True,
    user=None, session=None, **kwargs
):
    """Get subnet info."""
    return _get_subnet(
        subnet_id, session=session,
        exception_when_missing=exception_when_missing
    )


@utils.supported_filters(
    ADDED_FIELDS, optional_support_keys=OPTIONAL_ADDED_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(subnet=_check_subnet)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_SUBNET
)
@utils.wrap_to_dict(RESP_FIELDS)
def add_subnet(
    exception_when_existing=True, subnet=None,
    user=None, session=None, **kwargs
):
    """Create a subnet."""
    return utils.add_db_object(
        session, models.Subnet,
        exception_when_existing, subnet, **kwargs
    )


@utils.supported_filters(
    optional_support_keys=UPDATED_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(subnet=_check_subnet)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_SUBNET
)
@utils.wrap_to_dict(RESP_FIELDS)
def update_subnet(subnet_id, user=None, session=None, **kwargs):
    """Update a subnet."""
    subnet = _get_subnet(
        subnet_id, session=session
    )
    return utils.update_db_object(session, subnet, **kwargs)


def _check_subnet_deletable(subnet):
    """Check a subnet deletable."""
    if subnet.host_networks:
        host_networks = [
            '%s:%s=%s' % (
                host_network.host.name, host_network.interface,
                host_network.ip
            )
            for host_network in subnet.host_networks
        ]
        raise exception.NotAcceptable(
            'subnet %s contains host networks %s' % (
                subnet.subnet, host_networks
            )
        )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_DEL_SUBNET
)
@utils.wrap_to_dict(RESP_FIELDS)
def del_subnet(subnet_id, user=None, session=None, **kwargs):
    """Delete a subnet."""
    subnet = _get_subnet(
        subnet_id, session=session
    )
    _check_subnet_deletable(subnet)
    return utils.del_db_object(session, subnet)
