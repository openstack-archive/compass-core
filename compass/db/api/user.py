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

"""User database operations."""
from itsdangerous import URLSafeTimedSerializer

from flask.ext.login import UserMixin

from compass.db import api
from compass.db.api import database
from compass.db.api.utils import wrap_to_dict
from compass.db.exception import DuplicatedRecord
from compass.db.exception import Forbidden
from compass.db.exception import RecordNotExists

from compass.db.models import Permission
from compass.db.models import User

from compass.utils import setting_wrapper as setting
from compass.utils import util


SUPPORTED_FILTERS = ['id', 'email', 'is_admin', 'active']
SELF_UPDATED_FIELDS = ['firstname', 'lastname', 'password']
ADMIN_UPDATED_FIELDS = ['is_admin', 'active']
RESP_FIELDS = ['id', 'email', 'is_admin', 'active', 'firstname',
               'lastname', 'created_at', 'updated_at',
               'last_login_at', 'permissions']
FIELD_SET_CALLBACK = {'password': 'set_password'}
FIELD_LIST_CALLBACK = {'password': 'get_masked_password'}


def _get_user(session, **kwargs):
    """Get user."""
    with session.begin(subtransactions=True):
        user = session.query(User).filter_by(**kwargs).first()
        if user:
            return user
        else:
            raise RecordNotExists(
                'Cannot find the user in database: %s' % kwargs)


def _has_user(session, **kwargs):
    """check user."""
    with session.begin(subtransactions=True):
        user = session.query(User).filter_by(**kwargs).first()
        print 'get user %s' % user
        if user:
            return True
        else:
            return False


def _list_users(session, **filters):
    """Get all users, optionally filtered by some fields."""
    filters = dict([
        (filter_key, filter_value)
        for filter_key, filter_value in filters.items()
        if filter_key in SUPPORTED_FILTERS
    ])
    with session.begin(subtransactions=True):
        return api.model_filter(
            api.model_query(session, User), User, filters
        ).all()


def _add_user(session, **kwargs):
    """Create a user."""
    with session.begin(subtransactions=True):
        user = User(**kwargs)
        session.add(user)
        _add_user_permissions(
            session, user,
            name=setting.COMPASS_DEFAULT_PERMISSIONS
        )
        return user


def add_user_internal(session, email, password, **kwargs):
    """internal function used only by other db.api modules."""
    return _add_user(session, email=email, password=password, **kwargs)


def _del_user(session, user):
    """Delete a user."""
    with session.begin(subtransactions=True):
        session.delete(user)


def _update_user(session, user, **kwargs):
    """Update a user."""
    with session.begin(subtransactions=True):
        for key, value in kwargs.items():
            if key in FIELD_SET_CALLBACK:
                getattr(user, FIELD_SET_CALLBACK[key])(value)
            else:
                setattr(user, key, value)


def _check_user_permission(session, user, permission_name):
    """Check user has permission"""
    with session.begin(subtransactions=True):
        if user.is_admin:
            return

        if not user.check_permission(permission_name):
            raise Forbidden(
                'user %s does not have permission %s' % (
                    user.email, permission_name
                )
            )


def check_user_permission_internal(session, user_id, permission_name):
    """internal function only used by other db.api modules."""
    user = _get_user(session, id=user_id)
    _check_user_permission(session, user, permission_name)


def _add_user_permissions(session, user, **permission_filters):
    """add permissions to a user."""
    from compass.db.api.permission import list_permissions_internal
    with session.begin(subtransactions=True):
        existing_permissions = dict([
            (permission.id, permission)
            for permission in user.get_permissions()
        ])
        add_permissions = {}
        for permission in list_permissions_internal(
            session, **permission_filters)
        ):
            add_permissions[permission.id] = permission

        add_permissions.update(existing_permissions)
        user.set_permissions(add_permissions.values())


def _remove_user_permissions(session, user, **permission_filters):
    """remove permissions to a user."""
    from compass.db.api.permission import list_permissions_internal
    with session.begin(subtransactions=True):
        existing_permissions = dict([
            (permission.id, permission)
            for permission in user.get_permissions()
        ])
        remove_permissions = {}
        for permission in list_permissions_internal(
            session, **permission_filters
        ):
            remove_permissions[permission.id] = permission

        for permission_id in remove_permissions:
            if permission_id in existing_permissions:
                del existing_permissions[permission_id]

        user.set_permissions(existing_permissions.values())


def _set_user_permissions(session, user, permissions):
    """set permissions to a user."""
    from compass.db.api.permission import list_permissions_internal
    with session.begin(subtransactions=True):
        existing_permissions = dict([
            (permission.id, permission)
            for permission in user.get_permissions()
        ])
        new_permissions = {}
        for permission in list_permissions_internal(
            session, **permission_filters
        ):
            new_permissions[permission.id] = permission

        user.set_permissions(new_permissions.values())


class UserWrapper(UserMixin):
    SERIALIZER = URLSafeTimedSerializer(setting.USER_SECRET_KEY)

    def __init__(self, id, email, password, active=True, **kwargs):
        super(UserWrapper, self).__init__()
        self.id = id
        self.email = email
        self.password = password
        self.active = active
        for key, value in kwargs.items():
            setattr(self, key, value)

    def authenticate(self, password):
        return util.encrypt(password, self.password) == self.password

    def get_auth_token(self):
        return self.SERIALIZER.dumps(self.id)

    @classmethod
    def get_user_id(cls, token, max_age):
        return cls.SERIALIZER.loads(token, max_age=max_age)
         
    def is_active(self):
        return self.active

    def is_authenticated(self):
        return self.active

    def __str__(self):
        return '%s[email:%s,password:%s]' % (
            self.__class__.__name__, self.email, self.password)


def get_user_object(**kwargs):
    with database.session() as session:
        return UserWrapper(**(_get_user(session, **kwargs).to_dict()))


@wrap_to_dict(RESP_FIELDS)
def get_user(getter_id, user_id):
    """get field dict of a user."""
    with database.session() as session:
        getter = _get_user(session, id=getter_id)
        user = _get_user(session, id=user_id)
        if not getter.is_admin or getter_id != user_id:
            # The user is not allowed to list users
            raise Forbidden(
                'User %s has no permission to list user %s.' % (
                    lister.email, user.email
                )
            )

        user_dict = {}
        for key, value in user.to_dict().items():
             if key in FIELD_LIST_CALLBACK:
                 user_dict[key] = getattr(user, FIELD_LIST_CALLBACK[key])()
             else:
                 user_dict[key] = value

        return user_dict


@wrap_to_dict(RESP_FIELDS)
def list_users(lister_id, **filters):
    """List fields of all users by some fields."""
    with database.session() as session:
        lister = _get_user(session, id=lister_id)
        if not lister.is_admin:
            # The user is not allowed to list users
            raise Forbidden(
                'User %s has no permission to list users.' % (
                    lister.email
                )
            )
        
        users = []
        for user in _list_users(session, **filters):
            user_dict = {}
            for key, value in user.to_dict().items():
                if key in FIELD_LIST_CALLBACK:
                    user_dict[key] = getattr(user, FIELD_LIST_CALLBACK[key])()
                else:
                    user_dict[key] = value

            users.append(user_dict)

        return users


@wrap_to_dict(RESP_FIELDS)
def add_user(creator_id, email, password, **kwargs):
    """Create a user and return created user object."""
    with database.session() as session:
        creator = _get_user(session, id=creator_id)
        if not creator.is_admin:
            # The user is not allowed to create a user.
            raise Forbidden(
                'User %s has no permission to create user.' % (
                    creator.email
                )
            )

        user_exist = _has_user(session, email=email)
        if user_exist:
            raise DuplicatedRecord('User %s exists in database' % email)

        user = _add_user(session, email=email, password=password, **kwargs)
        return user.to_dict()


@wrap_to_dict(RESP_FIELDS)
def del_user(deleter_id, user_id):
    """delete a user and return the deleted user object."""
    with database.session() as session:
        deleter = _get_user(session, id=deleter_id)
        if not deleter.is_admin:
            raise Forbidden(
                'User %s has no permission to delete user.' % (
                    deleter.email
                )
            )

        user = _get_user(session, id=user_id)
        _del_user(session, user)
        return user.to_dict()


@wrap_to_dict(RESP_FIELDS)
def update_user(updater_id, user_id, **kwargs):
    """Update a user and return the updated user object."""
    with database.session() as session:
        updater = _get_user(session, id=updater_id)
        user = _get_user(session, id=user_id)
        update_info = {}
        if updater.is_admin:
            update_info.update(dict([
                (key, value) for key, value in kwargs.items()
                if key in ADMIN_UPDATED_FIELDS
            ]))
            kwargs = dict([
                (key, value) for key, value in kwargs.items()
                if key not in ADMIN_UPDATED_FIELDS
            ])

        if updater_id == user_id:
            update_info.update(dict([
                (key, value) for key, value in kwargs.items()
                if key in SELF_UPDATED_FIELDS
            ]))
            kwargs = dict([
                (key, value) for key, value in kwargs.items()
                if key not in SELF_UPDATED_FIELDS
            ])

        if kwargs:
            # The user is not allowed to update a user.
            raise Forbidden(
                'User %s has no permission to update user %s: %s.' % (
                    updater.email, user.email, kwargs
                )
            )

        _update_user(session, user, **update_info)
        return user.to_dict()


@wrap_to_dict(RESP_FIELDS)
def get_permissions(getter_id, user_id):
    """List permissions of a user."""
    with database.session() as session:
        getter = _get_user(session, id=getter_id)
        user = _get_user(session, id=user_id)
        if not getter.is_admin and getter_id != user_id:
            # The user is not allowed to list permissions
            raise Forbidden(
                'User %s has no permission to list user %s permissions.' % (
                    getter.email, user.email
                )
            )

        return {
            'id': user.id,
            'permissions': [
                permission.to_dict() for permission in user.get_permissions()
            ]
        }


@wrap_to_dict(RESP_FIELDS)
def update_permissions(updater_id, user_id,
                      add_permissions=[], remove_permissions=[],
                      set_permissions=None):
    """update user permissions."""
    def get_permission_filters(permission_ids):
        if permission_ids == 'all':
            return {}
        else:
            return {'id': permission_ids}

    with database.session() as session:
        updater = _get_user(session, id=updater_id)
        user = _get_user(session, id=user_id)
        update_info = {}
        if not updater.is_admin:
            raise Forbidden(
                'User %s has no permission to update user %s: %s.' % (
                    updater.email, user.email, kwargs
                )
            )

        if remove_permissions:
            _remove_user_permissions(
                session, user,
                get_permission_filters(remove_permissions)
            )

        if add_permissions:
            _add_user_permissions(
                session, user,
                get_permission_filters(add_permissions)
            )

        if set_permissions is not None:
            _set_user_permissions(
                session, user,
                get_permission_filters(set_permissions)
            )

        return {
            'id': user.id,
            'permissions': [
                permission.to_dict()
                for permission in user.get_permissions()
            ]
        }
