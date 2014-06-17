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

"""Permission database operations."""
from compass.db.api import database
from compass.db.api import utils
from compass.db import exception
from compass.db import models


SUPPORTED_FIELDS = ['name', 'alias', 'description']
RESP_FIELDS = ['id', 'name', 'alias', 'description']


class PermissionWrapper(object):
    def __init__(self, name, alias, description):
        self.name = name
        self.alias = alias
        self.description = description

    def to_dict(self):
        return {
            'name': self.name,
            'alias': self.alias,
            'description': self.description
        }


PERMISSION_LIST_PERMISSIONS = PermissionWrapper(
    'list_permissions', 'list permissions', 'list all permissions')
PERMISSION_LIST_SWITCHES = PermissionWrapper(
    'list_switches', 'list switches', 'list all switches')
PERMISSION_ADD_SWITCH = PermissionWrapper(
    'add_switch', 'add switch', 'add switch')
PERMISSION_DEL_SWITCH = PermissionWrapper(
    'delete_switch', 'delete switch', 'delete switch')
PERMISSION_LIST_MACHINES = PermissionWrapper(
    'list_machines', 'list machines', 'list machines')
PERMISSION_ADD_MACHINE = PermissionWrapper(
    'add_machine', 'add machine', 'add machine')
PERMISSION_DEL_MACHINE = PermissionWrapper(
    'delete_machine', 'delete machine', 'delete machine')
PERMISSIONS = [
    PERMISSION_LIST_PERMISSIONS,
    PERMISSION_LIST_SWITCHES,
    PERMISSION_ADD_SWITCH,
    PERMISSION_DEL_SWITCH,
    PERMISSION_LIST_MACHINES,
    PERMISSION_ADD_MACHINE,
    PERMISSION_DEL_MACHINE
]


def list_permissions_internal(session, **filters):
    """internal functions used only by other db.api modules."""    
    return utils.list_db_objects(session, models.Permission, **filters)


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters(optional_support_keys=SUPPORTED_FIELDS)
def list_permissions(lister, **filters):
    """list permissions."""
    from compass.db.api import user as user_api
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, lister, PERMISSION_LIST_PERMISSIONS.name
        )
        return [
            permission.to_dict()
            for permission in utils.list_db_objects(
                session, models.Permission, **filters
            )
        ]


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters()
def get_permission(getter, permission_id, **kwargs):
    """get permissions."""
    from compass.db.api import user as user_api
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, PERMISSION_LIST_PERMISSIONS.name
        )
        permission = utils.get_db_object(
            session, models.Permission, id=permission_id
        )
        return permission.to_dict()


def add_permissions_internal(session, exception_when_existing=True):
    """internal functions used by other db.api modules only."""
    permissions = []
    with session.begin(subtransactions=True):
        for permission in PERMISSIONS:
            permissions.append(
                utils.add_db_object(
                    session, models.Permission,
                    exception_when_existing,
                    permission.name,
                    alias=permission.alias,
                    description=permission.description
                )
            )

    return permissions
