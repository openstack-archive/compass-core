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
import logging
import re

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
    """Check email is email format."""
    if '@' not in email:
        raise exception.InvalidParameter(
            'there is no @ in email address %s.' % email
        )


def _check_user_permission(user, permission, session=None):
    """Check user has permission."""
    if not user:
        logging.info('empty user means the call is from internal')
        return
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


def check_user_permission(permission):
    """Decorator to check user having permission."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            user = kwargs.get('user')
            if user is not None:
                session = kwargs.get('session')
                if session is None:
                    raise exception.DatabaseException(
                        'wrapper check_user_permission does not run in session'
                    )
                _check_user_permission(user, permission, session=session)
                return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator


def check_user_admin():
    """Decorator to check user is admin."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            user = kwargs.get('user')
            if user is not None:
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
    """Decorator to check user is admin or the owner of the resource."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(user_id, *args, **kwargs):
            user = kwargs.get('user')
            if user is not None:
                session = kwargs.get('session')
                if session is None:
                    raise exception.DatabaseException(
                        'wrapper check_user_admin_or_owner is '
                        'not called in session'
                    )
                check_user = _get_user(user_id, session=session)
                if not user.is_admin and user.id != check_user.id:
                    raise exception.Forbidden(
                        'User %s is not admin or the owner of user %s.' % (
                            user.email, check_user.email
                        )
                    )

                return func(
                    user_id, *args, **kwargs
                )
            else:
                return func(
                    user_id, *args, **kwargs
                )
        return wrapper
    return decorator


def _add_user_permissions(user, session=None, **permission_filters):
    """add permissions to a user."""
    from compass.db.api import permission as permission_api
    for api_permission in permission_api.list_permissions(
        session=session, **permission_filters
    ):
        utils.add_db_object(
            session, models.UserPermission, False,
            user.id, api_permission['id']
        )


def _remove_user_permissions(user, session=None, **permission_filters):
    """remove permissions from a user."""
    from compass.db.api import permission as permission_api
    permission_ids = [
        api_permission['id']
        for api_permission in permission_api.list_permissions(
            session=session, **permission_filters
        )
    ]
    utils.del_db_objects(
        session, models.UserPermission,
        user_id=user.id, permission_id=permission_ids
    )


def _set_user_permissions(user, session=None, **permission_filters):
    """set permissions to a user."""
    utils.del_db_objects(
        session, models.UserPermission,
        user_id=user.id
    )
    _add_user_permissions(session, user, **permission_filters)


class UserWrapper(UserMixin):
    """Wrapper class provided to flask."""

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
    """get user and convert to UserWrapper object."""
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


@database.run_in_session(exception_when_in_session=False)
def get_user_object_from_token(token, session=None):
    """Get user from token and convert to UserWrapper object.

    ::note:
       get_user_object_from_token may be called in session.
    """
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
    user_dict = _get_user(
        user_token.user_id, session=session
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


def _get_user(user_id, session=None, **kwargs):
    """Get user object by user id."""
    if isinstance(user_id, (int, long)):
        return utils.get_db_object(
            session, models.User, id=user_id, **kwargs
        )
    raise exception.InvalidParameter(
        'user id %s type is not int compatible' % user_id
    )


@utils.supported_filters()
@database.run_in_session()
@check_user_admin_or_owner()
@utils.wrap_to_dict(RESP_FIELDS)
def get_user(
    user_id, exception_when_missing=True,
    user=None, session=None, **kwargs
):
    """get a user."""
    return _get_user(
        user_id, session=session,
        exception_when_missing=exception_when_missing
    )


@utils.supported_filters()
@database.run_in_session()
@utils.wrap_to_dict(RESP_FIELDS)
def get_current_user(
    exception_when_missing=True, user=None,
    session=None, **kwargs
):
    """get current user."""
    return _get_user(
        user.id, session=session,
        exception_when_missing=exception_when_missing
    )


@utils.supported_filters(
    optional_support_keys=SUPPORTED_FIELDS
)
@database.run_in_session()
@check_user_admin()
@utils.wrap_to_dict(RESP_FIELDS)
def list_users(user=None, session=None, **filters):
    """List all users."""
    return utils.list_db_objects(
        session, models.User, **filters
    )


@utils.input_validates(email=_check_email)
@utils.supported_filters(
    ADDED_FIELDS,
    optional_support_keys=OPTIONAL_ADDED_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@check_user_admin()
@utils.wrap_to_dict(RESP_FIELDS)
def add_user(
    exception_when_existing=True, user=None,
    session=None, email=None, **kwargs
):
    """Create a user and return created user object."""
    add_user = utils.add_db_object(
        session, models.User,
        exception_when_existing, email,
        **kwargs)
    _add_user_permissions(
        add_user,
        session=session,
        name=setting.COMPASS_DEFAULT_PERMISSIONS
    )
    return add_user


@utils.supported_filters()
@database.run_in_session()
@check_user_admin()
@utils.wrap_to_dict(RESP_FIELDS)
def del_user(user_id, user=None, session=None, **kwargs):
    """delete a user and return the deleted user object."""
    del_user = _get_user(user_id, session=session)
    return utils.del_db_object(session, del_user)


@utils.supported_filters(
    optional_support_keys=UPDATED_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(email=_check_email)
@database.run_in_session()
@utils.wrap_to_dict(RESP_FIELDS)
def update_user(user_id, user=None, session=None, **kwargs):
    """Update a user and return the updated user object."""
    update_user = _get_user(
        user_id, session=session,
    )
    allowed_fields = set()
    if user.is_admin:
        allowed_fields |= set(ADMIN_UPDATED_FIELDS)
    if user.id == update_user.id:
        allowed_fields |= set(SELF_UPDATED_FIELDS)
    unsupported_fields = set(kwargs) - allowed_fields
    if unsupported_fields:
            # The user is not allowed to update a user.
        raise exception.Forbidden(
            'User %s has no permission to update user %s fields %s.' % (
                user.email, user.email, unsupported_fields
            )
        )
    return utils.update_db_object(session, update_user, **kwargs)


@utils.supported_filters(optional_support_keys=PERMISSION_SUPPORTED_FIELDS)
@database.run_in_session()
@check_user_admin_or_owner()
@utils.wrap_to_dict(PERMISSION_RESP_FIELDS)
def get_permissions(
    user_id, user=None, exception_when_missing=True,
    session=None, **kwargs
):
    """List permissions of a user."""
    get_user = _get_user(
        user_id, session=session,
        exception_when_missing=exception_when_missing
    )
    return utils.list_db_objects(
        session, models.UserPermission, user_id=get_user.id, **kwargs
    )


def _get_permission(user_id, permission_id, session=None, **kwargs):
    """Get user permission by user id and permission id."""
    user = _get_user(user_id, session=session)
    from compass.db.api import permission as permission_api
    permission = permission_api.get_permission_internal(
        permission_id, session=session
    )
    return utils.get_db_object(
        session, models.UserPermission,
        user_id=user.id, permission_id=permission.id,
        **kwargs
    )


@utils.supported_filters()
@database.run_in_session()
@check_user_admin_or_owner()
@utils.wrap_to_dict(PERMISSION_RESP_FIELDS)
def get_permission(
    user_id, permission_id, exception_when_missing=True,
    user=None, session=None, **kwargs
):
    """Get a permission of a user."""
    return _get_permission(
        user_id, permission_id,
        exception_when_missing=exception_when_missing,
        session=session,
        **kwargs
    )


@utils.supported_filters()
@database.run_in_session()
@check_user_admin_or_owner()
@utils.wrap_to_dict(PERMISSION_RESP_FIELDS)
def del_permission(user_id, permission_id, user=None, session=None, **kwargs):
    """Delete a permission from a user."""
    user_permission = _get_permission(
        user_id, permission_id,
        session=session, **kwargs
    )
    return utils.del_db_object(session, user_permission)


@utils.supported_filters(
    PERMISSION_ADDED_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@check_user_admin()
@utils.wrap_to_dict(PERMISSION_RESP_FIELDS)
def add_permission(
    user_id, permission_id=None, exception_when_existing=True,
    user=None, session=None
):
    """Add a permission to a user."""
    get_user = _get_user(user_id, session=session)
    from compass.db.api import permission as permission_api
    get_permission = permission_api.get_permission_internal(
        permission_id, session=session
    )
    return utils.add_db_object(
        session, models.UserPermission, exception_when_existing,
        get_user.id, get_permission.id
    )


def _get_permission_filters(permission_ids):
    """Helper function to filter permissions."""
    if permission_ids == 'all':
        return {}
    else:
        return {'id': permission_ids}


@utils.supported_filters(
    optional_support_keys=[
        'add_permissions', 'remove_permissions', 'set_permissions'
    ]
)
@database.run_in_session()
@check_user_admin()
@utils.wrap_to_dict(PERMISSION_RESP_FIELDS)
def update_permissions(
    user_id, add_permissions=[], remove_permissions=[],
    set_permissions=None, user=None, session=None, **kwargs
):
    """update user permissions."""
    update_user = _get_user(user_id, session=session)
    if remove_permissions:
        _remove_user_permissions(
            update_user, session=session,
            **_get_permission_filters(remove_permissions)
        )
    if add_permissions:
        _add_user_permissions(
            update_user, session=session,
            **_get_permission_filters(add_permissions)
        )
    if set_permissions is not None:
        _set_user_permissions(
            update_user, session=session,
            **_get_permission_filters(set_permissions)
        )
    return update_user.user_permissions
