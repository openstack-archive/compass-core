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
IGNORE_FIELDS = ['id', 'created_at', 'updated_at']
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
    session, exception_when_existing=True,
    email=None, **kwargs
):
    """internal function used only by other db.api modules."""
    user = utils.add_db_object(
        session, models.User,
        exception_when_existing, email,
        **kwargs)
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
        def wrapper(*args, **kwargs):
            if 'user' in kwargs.keys() and 'session' in kwargs.keys():
                session = kwargs['session']
                user = kwargs['user']
                _check_user_permission(session, user, permission)
                return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator


def check_user_admin():
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if 'user' in kwargs.keys():
                user = kwargs['user']
                if not user.is_admin:
                    raise exception.Forbidden(
                        'User %s is not admin.' % (
                            user.email
                        )
                    )
                return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator


def check_user_admin_or_owner():
    def decorator(func):
        @functools.wraps(func)
        def wrapper(user_id, *args, **kwargs):
            if 'user' in kwargs.keys():
                user = kwargs['user']
                if not user.is_admin and user.id != user_id:
                    raise exception.Forbidden(
                        'User %s is not admin or the owner of user id %s.' % (
                            user.email, user_id
                        )
                    )
                return func(user_id, *args, **kwargs)
            else:
                return func(user_id, *args, **kwargs)
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
        active=True, is_admin=False,
        expire_timestamp=None, token='', **kwargs
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
        return (
            not self.expire_timestamp or
            current_time < self.expire_timestamp
        )

    def __str__(self):
        return '%s[email:%s,password:%s]' % (
            self.__class__.__name__, self.email, self.password)


@database.run_in_session()
def get_user_object(email, session=None, **kwargs):
    user = utils.get_db_object(
        session, models.User, False, email=email
    )
    if not user:
        raise exception.Unauthorized(
            '%s unauthorized' % email
        )
    user_dict = user.to_dict()
    user_dict.update(kwargs)
    return UserWrapper(**user_dict)


@database.run_in_session()
def get_user_object_from_token(token, session=None):
    expire_timestamp = {
        'ge': datetime.datetime.now()
    }
    user_token = utils.get_db_object(
        session, models.UserToken, False,
        token=token, expire_timestamp=expire_timestamp
    )
    if not user_token:
        raise exception.Unauthorized(
            'invalid user token: %s' % token
        )
    user_dict = utils.get_db_object(
        session, models.User, id=user_token.user_id
    ).to_dict()
    user_dict['token'] = token
    expire_timestamp = user_token.expire_timestamp
    user_dict['expire_timestamp'] = expire_timestamp
    return UserWrapper(**user_dict)


@utils.supported_filters()
@database.run_in_session()
@utils.wrap_to_dict(RESP_TOKEN_FIELDS)
def record_user_token(
    token, expire_timestamp, user=None, session=None
):
    """record user token in database."""
    user_token = utils.get_db_object(
        session, models.UserToken, False,
        user_id=user.id, token=token
    )
    if not user_token:
        return utils.add_db_object(
            session, models.UserToken, True,
            token, user_id=user.id,
            expire_timestamp=expire_timestamp
        )
    elif expire_timestamp > user_token.expire_timestamp:
        return utils.update_db_object(
            session, user_token, expire_timestamp=expire_timestamp
        )
    return user_token


@utils.supported_filters()
@database.run_in_session()
@utils.wrap_to_dict(RESP_TOKEN_FIELDS)
def clean_user_token(token, user=None, session=None):
    """clean user token in database."""
    return utils.del_db_objects(
        session, models.UserToken,
        token=token, user_id=user.id
    )


@utils.supported_filters()
@check_user_admin_or_owner()
@database.run_in_session()
@utils.wrap_to_dict(RESP_FIELDS)
def get_user(
    user_id, exception_when_missing=True,
    user=None, session=None, **kwargs
):
    """get field dict of a user."""
    return utils.get_db_object(
        session, models.User, exception_when_missing, id=user_id
    )


@utils.supported_filters()
@database.run_in_session()
@utils.wrap_to_dict(RESP_FIELDS)
def get_current_user(
    exception_when_missing=True, user=None,
    session=None, **kwargs
):
    """get field dict of a user."""
    return utils.get_db_object(
        session, models.User, exception_when_missing, id=user.id
    )


@utils.supported_filters(
    optional_support_keys=SUPPORTED_FIELDS
)
@check_user_admin()
@database.run_in_session()
@utils.wrap_to_dict(RESP_FIELDS)
def list_users(user=None, session=None, **filters):
    """List fields of all users by some fields."""
    return utils.list_db_objects(
        session, models.User, **filters
    )


@utils.input_validates(email=_check_email)
@utils.supported_filters(
    ADDED_FIELDS,
    optional_support_keys=OPTIONAL_ADDED_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@check_user_admin()
@database.run_in_session()
@utils.wrap_to_dict(RESP_FIELDS)
def add_user(
    exception_when_existing=True, user=None,
    session=None, **kwargs
):
    """Create a user and return created user object."""
    return add_user_internal(
        session, exception_when_existing, **kwargs
    )


@utils.supported_filters()
@check_user_admin()
@database.run_in_session()
@utils.wrap_to_dict(RESP_FIELDS)
def del_user(user_id, user=None, session=None, **kwargs):
    """delete a user and return the deleted user object."""
    user = utils.get_db_object(session, models.User, id=user_id)
    return utils.del_db_object(session, user)


@utils.supported_filters(
    optional_support_keys=UPDATED_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(email=_check_email)
@database.run_in_session()
@utils.wrap_to_dict(RESP_FIELDS)
def update_user(user_id, user=None, session=None, **kwargs):
    """Update a user and return the updated user object."""
    user = utils.get_db_object(
        session, models.User, id=user_id
    )
    allowed_fields = set()
    if user.is_admin:
        allowed_fields |= set(ADMIN_UPDATED_FIELDS)
    if user.id == user_id:
        allowed_fields |= set(SELF_UPDATED_FIELDS)
    unsupported_fields = set(kwargs) - allowed_fields
    if unsupported_fields:
            # The user is not allowed to update a user.
        raise exception.Forbidden(
            'User %s has no permission to update user %s fields %s.' % (
                user.email, user.email, unsupported_fields
            )
        )
    return utils.update_db_object(session, user, **kwargs)


@utils.supported_filters(optional_support_keys=PERMISSION_SUPPORTED_FIELDS)
@check_user_admin_or_owner()
@database.run_in_session()
@utils.wrap_to_dict(PERMISSION_RESP_FIELDS)
def get_permissions(user_id, user=None, session=None, **kwargs):
    """List permissions of a user."""
    return utils.list_db_objects(
        session, models.UserPermission, user_id=user_id, **kwargs
    )


@utils.supported_filters()
@check_user_admin_or_owner()
@database.run_in_session()
@utils.wrap_to_dict(PERMISSION_RESP_FIELDS)
def get_permission(
    user_id, permission_id, exception_when_missing=True,
    user=None, session=None, **kwargs
):
    """Get a specific user permission."""
    return utils.get_db_object(
        session, models.UserPermission,
        exception_when_missing,
        user_id=user_id, permission_id=permission_id,
        **kwargs
    )


@utils.supported_filters()
@check_user_admin_or_owner()
@database.run_in_session()
@utils.wrap_to_dict(PERMISSION_RESP_FIELDS)
def del_permission(user_id, permission_id, user=None, session=None, **kwargs):
    """Delete a specific user permission."""
    user_permission = utils.get_db_object(
        session, models.UserPermission,
        user_id=user_id, permission_id=permission_id,
        **kwargs
    )
    return utils.del_db_object(session, user_permission)


@utils.supported_filters(
    PERMISSION_ADDED_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@check_user_admin()
@database.run_in_session()
@utils.wrap_to_dict(PERMISSION_RESP_FIELDS)
def add_permission(
    user_id, exception_when_missing=True,
    permission_id=None, user=None, session=None
):
    """Add an user permission."""
    return utils.add_db_object(
        session, models.UserPermission, exception_when_missing,
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
    user_id, add_permissions=[], remove_permissions=[],
    set_permissions=None, user=None, session=None, **kwargs
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
