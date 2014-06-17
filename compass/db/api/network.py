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

from compass.db import exception
from compass.db import models
from compass.db.api import database
from compass.db.api import utils
from compass.db.api import user as user_api


SUPPORTED_FILTERS=['subnet']
RESP_FIELDS = ['id', 'subnet', 'created_at', 'updated_at']
ADDED_FIELDS = ['subnet']
UPDATED_FIELDS = ['subnet']


def _check_subnet(subnet):
    try:
        network = netaddr.Network(subnet)
    except Exception:
        raise exception.Invalidparameter(
            'subnet %s format unrecognized' % subnet)


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters(optional_support_keys=SUPPORTED_FIELDS)
def list_subnets(lister, **filters):
    """List subnets."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, lister, permission.PERMISSION_LIST_NETWORKS)
        return [
            network.to_dict()
            for network in utils.list_db_objects(
                session, models.Network, **filters
            )
        ]


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters([])
def get_subnet(getter, subnet_id, **kwargs):
    """Get subnet info."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_LIST_NETWORKS)
        return utils.get_db_object(session, models.Network, id=subnet_id
        ).to_dict()

 
@utils.wrap_to_dict(RESP_FIELDS)
@utils.input_validates(subnet=_check_subnet)
@utils.supported_filters(ADDED_FIELDS)
def add_subnet(creator, subnet, **kwargs):
    """Create a subnet."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, creator, permission.PERMISSION_ADD_NETWORK)
        network = utils.add_db_object(
            session, models.Network, True, subnet
        )
        return network.to_dict()


@utils.wrap_to_dict(RESP_FIELDS)
@utils.input_validates(subnet=_check_subnet)
@utils.supported_filters(UPDATED_FIELDS)
def update_subnet(updater, subnet_id, **kwargs):
     """Update a subnet."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_ADD_NETWORK)
        network = utils.get_db_object(
            session, models.Network, id=subnet_id
        )
        utils.update_db_object(session, network, **kwargs)
        return network.to_dict()


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters([])
def del_subnet(deleter, subnet_id, **kwargs):
    """Delete a subnet."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, deleter, permission.PERMISSION_DEL_NETWORK)
        network = utils.get_db_object(
            session, models.Network, id=subnet_id
        )
        utils.del_db_object(session, network)
        return network.to_dict()
