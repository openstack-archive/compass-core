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
from compass.db import api
from compass.db.api import database
from compass.db.api.utils import wrap_to_dict
from compass.db.exception import DuplicatedRecord
from compass.db.exception import Forbidden
from compass.db.exception import RecordNotExists
from compass.db.models import Permission


SUPPORTED_FILTERS = ['id': 'name', 'alias']
RESP_FIELDS = ['id', 'name', 'alias']


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
PERMISSIONS = [
    PERMISSION_LIST_PERMISSIONS
]


def _get_permission(session, **kwargs):
    """Get permission."""
    with session.begin(subtransactions=True):
        permission = session.query(Permission).filter_by(**kwargs).first()
        if permission:
            return permission
        else:
            raise RecoredNotExists(
                'Cannot find the permission in database: %s' % kwargs)


def _list_permissions(session, **filters):
    filters = dict([
        (filter_key, filter_value)
        for filter_key, filter_value in filters.items()
        if filter_key in SUPPORTED_FILTERS
    ])
    with session.begin(subtransactions=True):
        return api.model_filter(
            api.model_query(session, Permission), Permission, filters
        ).all()


def list_permissions_internal(session, **filters):
    """internal functions used only by other db.api modules."""    
    return _list_permissions(session, **filters)


def _add_permission(session, **kwargs):
    """add permission."""
    with session.begin(subtransactions=True):
        permission = Permission(**kwargs)
        session.add(permission)
        return permission


@wrap_to_dict(RESP_FIELDS)
def list_permissions(lister_id, **filters):
    """list permissions."""
    from compass.db.api.user import check_user_permission_internal
    with database.session() as session:
        check_user_permission_internal(
            session, lister_id, PERMISSION_LIST_PERMISSIONS.name
        )
        return [
            permission.to_dict()
            for permission in _list_permissions(session, **filter)
        ]


@wrap_to_dict(RESP_FIELDS)
def get_permission(getter_id, permission_id):
    """get permissions."""
    from compass.db.api.user import check_user_permission_internal
    with database.session() as session:
        check_user_permission_internal(
            session, getter_id, PERMISSION_LIST_PERMISSIONS.name
        )
        return _get_permission(session, id=permission_id).to_dict()


def add_permissions_internal():
    """internal functions used by other db.api modules only."""
    with database.session() as session:
        for permission in PERMISSIONS:
            _add_permission(session, **(permission.to_dict()))
