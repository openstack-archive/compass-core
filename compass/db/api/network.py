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

from compass.db.api import database
from compass.db.api import permission
from compass.db.api import user as user_api
from compass.db.api import utils
from compass.db import exception
from compass.db import models


SUPPORTED_FIELDS = ['subnet']
RESP_FIELDS = ['id', 'subnet', 'created_at', 'updated_at']
ADDED_FIELDS = ['subnet']
UPDATED_FIELDS = ['subnet']


def _check_subnet(subnet):
    try:
        netaddr.IPNetwork(subnet)
    except Exception as error:
        logging.exception(error)
        raise exception.InvalidParameter(
            'subnet %s format unrecognized' % subnet)


@utils.supported_filters(optional_support_keys=SUPPORTED_FIELDS)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_NETWORKS
)
@utils.wrap_to_dict(RESP_FIELDS)
def list_subnets(session, lister, **filters):
    """List subnets."""
    return utils.list_db_objects(
        session, models.Network, **filters
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_NETWORKS
)
@utils.wrap_to_dict(RESP_FIELDS)
def get_subnet(session, getter, subnet_id, **kwargs):
    """Get subnet info."""
    return utils.get_db_object(
        session, models.Network, id=subnet_id
    )


@utils.supported_filters(ADDED_FIELDS)
@utils.input_validates(subnet=_check_subnet)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_NETWORK
)
@utils.wrap_to_dict(RESP_FIELDS)
def add_subnet(session, creator, subnet, **kwargs):
    """Create a subnet."""
    return utils.add_db_object(
        session, models.Network, True, subnet
    )


@utils.supported_filters(UPDATED_FIELDS)
@utils.input_validates(subnet=_check_subnet)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_NETWORK
)
@utils.wrap_to_dict(RESP_FIELDS)
def update_subnet(session, updater, subnet_id, **kwargs):
    """Update a subnet."""
    network = utils.get_db_object(
        session, models.Network, id=subnet_id
    )
    return utils.update_db_object(session, network, **kwargs)


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_DEL_NETWORK
)
@utils.wrap_to_dict(RESP_FIELDS)
def del_subnet(session, deleter, subnet_id, **kwargs):
    """Delete a subnet."""
    network = utils.get_db_object(
        session, models.Network, id=subnet_id
    )
    return utils.del_db_object(session, network)
