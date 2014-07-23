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
import datetime
import functools

from flask.ext.login import UserMixin

from compass.db.api import database
from compass.db.api import utils
from compass.db import exception
from compass.db import models

from compass.utils import setting_wrapper as setting
from compass.utils import util


SUPPORTED_FIELDS = ['email', 'is_admin', 'active']
PERMISSION_SUPPORTED_FIELDS = ['name']
SELF_UPDATED_FIELDS = ['email', 'firstname', 'lastname', 'password']
ADMIN_UPDATED_FIELDS = ['is_admin', 'active']
UPDATED_FIELDS = [
    'email', 'firstname', 'lastname', 'password', 'is_admin', 'active'
]
ADDED_FIELDS = ['email', 'password']
OPTIONAL_ADDED_FIELDS = ['is_admin', 'active']
PERMISSION_ADDED_FIELDS = ['permission_id']
RESP_FIELDS = [
    'id', 'email', 'is_admin', 'active', 'firstname',
    'lastname', 'created_at', 'updated_at'
]
RESP_TOKEN_FIELDS = [
    'id', 'user_id', 'token', 'expire_timestamp'
]
PERMISSION_RESP_FIELDS = [
    'id', 'user_id', 'permission_id', 'name', 'alias', 'description',
    'created_at', 'updated_at'
]


def _check_email(email):
    if '@' not in email:
        raise exception.InvalidParameter(
            'there is no @ in email address %s.' % email
        )


def get_user_internal(session, exception_when_missing=True, **kwargs):
    """internal function used only by other db.api modules."""
    return utils.get_db_object(
        session, models.User, exception_when_missing, **kwargs
    )


def add_user_internal(
    session, email, password,
    exception_when_existing=True, **kwargs
):
    """internal function used only by other db.api modules."""
    user = utils.add_db_object(session, models.User,
                               exception_when_existing, email,
                               password=password, **kwargs)
    _add_user_permissions(
        session, user,
        name=setting.COMPASS_DEFAULT_PERMISSIONS
    )
    return user


def _check_user_permission(session, user, permission):
    """Check user has permission."""
    if user.is_admin:
        return

    user_permission = utils.get_db_object(
        session, models.UserPermission,
        False, user_id=user.id, name=permission.name
    )
    if not user_permission:
        raise exception.Forbidden(
            'user %s does not have permission %s' % (
                user.email, permission.name
            )
        )


def check_user_permission_in_session(permission):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(session, user, *args, **kwargs):
            _check_user_permission(session, user, permission)
            return func(session, user, *args, **kwargs)
        return wrapper
    return decorator


def check_user_admin():
    def decorator(func):
        @functools.wraps(func)
        def wrapper(user, *args, **kwargs):
            if not user.is_admin:
                raise exception.Forbidden(
                    'User %s is not admin.' % (
                        user.email
                    )
                )
            return func(user, *args, **kwargs)
        return wrapper
    return decorator


def check_user_admin_or_owner():
    def decorator(func):
        @functools.wraps(func)
        def wrapper(user, user_id, *args, **kwargs):
            if not user.is_admin and user.id != user_id:
                raise exception.Forbidden(
                    'User %s is not admin or the owner of user id %s.' % (
                        user.email, user_id
                    )
                )
            return func(user, user_id, *args, **kwargs)
        return wrapper
    return decorator


def check_user_permission_internal(session, user, permission):
    """internal function only used by other db.api modules."""
    _check_user_permission(session, user, permission)


def _add_user_permissions(session, user, **permission_filters):
    """add permissions to a user."""
    from compass.db.api import permission as permission_api
    for api_permission in permission_api.list_permissions_internal(
        session, **permission_filters
    ):
        utils.add_db_object(
            session, models.UserPermission, False,
            user.id, api_permission.id
        )


def _remove_user_permissions(session, user, **permission_filters):
    """remove permissions to a user."""
    from compass.db.api import permission as permission_api
    permission_ids = [
        api_permission.id
        for api_permission in permission_api.list_permissions_internal(
            session, **permission_filters
        )
    ]
    utils.del_db_objects(
        session, models.UserPermission,
        user_id=user.id, permission_id=permission_ids
    )


def _set_user_permissions(session, user, **permission_filters):
    """set permissions to a user."""
    utils.del_db_objects(
        session, models.UserPermission,
        user_id=user.id
    )
    _add_user_permissions(session, user, **permission_filters)


class UserWrapper(UserMixin):
    def __init__(
        self, id, email, crypted_password,
        active, is_admin, expire_timestamp, token='', **kwargs
    ):
        self.id = id
        self.email = email
        self.password = crypted_password
        self.active = active
        self.is_admin = is_admin
        self.expire_timestamp = expire_timestamp
        if not token:
            self.token = self.get_auth_token()
        else:
            self.token = token
        super(UserWrapper, self).__init__()

    def authenticate(self, password):
        if not util.encrypt(password, self.password) == self.password:
            raise exception.Unauthorized('%s password mismatch' % self.email)

    def get_auth_token(self):
        return util.encrypt(self.email)

    def is_active(self):
        return self.active

    def get_id(self):
        return self.token

    def is_authenticated(self):
        current_time = datetime.datetime.now()
        return current_time < self.expire_timestamp

    def __str__(self):
        return '%s[email:%s,password:%s]' % (
            self.__class__.__name__, self.email, self.password)


@database.run_in_session()
def get_user_object(session, email, **kwargs):
    user_dict = utils.get_db_object(
        session, models.User, email=email
    ).to_dict()
    user_dict.update(kwargs)
    return UserWrapper(**user_dict)


@database.run_in_session()
def get_user_object_from_token(session, token):
    expire_timestamp = {
        'ge': datetime.datetime.now()
    }
    user_token = utils.get_db_object(
        session, models.UserToken,
        token=token, expire_timestamp=expire_timestamp
    )
    user_dict = utils.get_db_object(
        session, models.User, id=user_token.user_id
    ).to_dict()
    user_dict['token'] = token
    user_dict['expire_timestamp'] = user_token.expire_timestamp
    return UserWrapper(**user_dict)


@utils.supported_filters()
@database.run_in_session()
@utils.wrap_to_dict(RESP_TOKEN_FIELDS)
def record_user_token(session, user, token, expire_timestamp):
    """record user token in database."""
    return utils.add_db_object(
        session, models.UserToken, True,
        token, user_id=user.id,
        expire_timestamp=expire_timestamp
    )


@utils.supported_filters()
@database.run_in_session()
@utils.wrap_to_dict(RESP_TOKEN_FIELDS)
def clean_user_token(session, user, token):
    """clean user token in database."""
    return utils.del_db_objects(
        session, models.UserToken,
        token=token, user_id=user.id
    )


@utils.supported_filters()
@check_user_admin_or_owner()
@database.run_in_session()
@utils.wrap_to_dict(RESP_FIELDS)
def get_user(session, getter, user_id, **kwargs):
    """get field dict of a user."""
    return utils.get_db_object(session, models.User, id=user_id)


@utils.supported_filters(
    optional_support_keys=SUPPORTED_FIELDS
)
@check_user_admin()
@database.run_in_session()
@utils.wrap_to_dict(RESP_FIELDS)
def list_users(session, lister, **filters):
    """List fields of all users by some fields."""
    return utils.list_db_objects(
        session, models.User, **filters
    )


@utils.input_validates(email=_check_email)
@utils.supported_filters(
    ADDED_FIELDS, optional_support_keys=OPTIONAL_ADDED_FIELDS
)
@check_user_admin()
@database.run_in_session()
@utils.wrap_to_dict(RESP_FIELDS)
def add_user(session, creator, email, password, **kwargs):
    """Create a user and return created user object."""
    return add_user_internal(
        session, email, password, **kwargs
    )


@utils.supported_filters()
@database.run_in_session()
@check_user_admin()
@utils.wrap_to_dict(RESP_FIELDS)
def del_user(session, deleter, user_id, **kwargs):
    """delete a user and return the deleted user object."""
    user = utils.get_db_object(session, models.User, id=user_id)
    return utils.del_db_object(session, user)


@utils.supported_filters(optional_support_keys=UPDATED_FIELDS)
@utils.input_validates(email=_check_email)
@database.run_in_session()
@utils.wrap_to_dict(RESP_FIELDS)
def update_user(session, updater, user_id, **kwargs):
    """Update a user and return the updated user object."""
    user = utils.get_db_object(
        session, models.User, id=user_id
    )
    allowed_fields = set()
    if updater.is_admin:
        allowed_fields |= set(ADMIN_UPDATED_FIELDS)
    if updater.id == user_id:
        allowed_fields |= set(SELF_UPDATED_FIELDS)
    unsupported_fields = allowed_fields - set(kwargs)
    if unsupported_fields:
            # The user is not allowed to update a user.
        raise exception.Forbidden(
            'User %s has no permission to update user %s fields %s.' % (
                updater.email, user.email, unsupported_fields
            )
        )
    return utils.update_db_object(session, user, **kwargs)


@utils.supported_filters(optional_support_keys=PERMISSION_SUPPORTED_FIELDS)
@check_user_admin_or_owner()
@database.run_in_session()
@utils.wrap_to_dict(PERMISSION_RESP_FIELDS)
def get_permissions(session, getter, user_id, **kwargs):
    """List permissions of a user."""
    return utils.list_db_objects(
        session, models.UserPermission, user_id=user_id, **kwargs
    )


@utils.supported_filters()
@check_user_admin_or_owner()
@database.run_in_session()
@utils.wrap_to_dict(PERMISSION_RESP_FIELDS)
def get_permission(session, getter, user_id, permission_id, **kwargs):
    """Get a specific user permission."""
    return utils.get_db_object(
        session, models.UserPermission,
        user_id=user_id, permission_id=permission_id,
        **kwargs
    )


@utils.supported_filters()
@check_user_admin_or_owner()
@database.run_in_session()
@utils.wrap_to_dict(PERMISSION_RESP_FIELDS)
def del_permission(session, deleter, user_id, permission_id, **kwargs):
    """Delete a specific user permission."""
    user_permission = utils.get_db_object(
        session, models.UserPermission,
        user_id=user_id, permission_id=permission_id,
        **kwargs
    )
    return utils.del_db_object(session, user_permission)


@utils.supported_filters(PERMISSION_ADDED_FIELDS)
@check_user_admin()
@database.run_in_session()
@utils.wrap_to_dict(PERMISSION_RESP_FIELDS)
def add_permission(session, creator, user_id, permission_id):
    """Add an user permission."""
    return utils.add_db_object(
        session, models.UserPermission, True,
        user_id, permission_id
    )


def _get_permission_filters(permission_ids):
    if permission_ids == 'all':
        return {}
    else:
        return {'id': permission_ids}


@utils.supported_filters(
    optional_support_keys=[
        'add_permissions', 'remove_permissions', 'set_permissions'
    ]
)
@check_user_admin()
@database.run_in_session()
@utils.wrap_to_dict(PERMISSION_RESP_FIELDS)
def update_permissions(
    session, updater, user_id,
    add_permissions=[], remove_permissions=[],
    set_permissions=None, **kwargs
):
    """update user permissions."""
    user = utils.get_db_object(session, models.User, id=user_id)
    if remove_permissions:
        _remove_user_permissions(
            session, user,
            **_get_permission_filters(remove_permissions)
        )
    if add_permissions:
        _add_user_permissions(
            session, user,
            **_get_permission_filters(add_permissions)
        )
    if set_permissions is not None:
        _set_user_permissions(
            session, user,
            **_get_permission_filters(set_permissions)
        )
    return user.user_permissions
