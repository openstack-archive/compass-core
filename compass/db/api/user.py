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

from flask.ext.login import UserMixin

from compass.db.api import database
from compass.db.api import permission
from compass.db.api import utils
from compass.db import exception
from compass.db import models

from compass.utils import setting_wrapper as setting
from compass.utils import util


SUPPORTED_FIELDS = ['email', 'is_admin', 'active']
PERMISSION_SUPPORTED_FIELDS = ['name']
SELF_UPDATED_FIELDS = ['email', 'firstname', 'lastname', 'password']
ADMIN_UPDATED_FIELDS = ['is_admin', 'active']
UPDATED_FIELDS = ['email', 'firstname', 'lastname', 'password', 'is_admin', 'active']
ADDED_FIELDS = ['email', 'password']
OPTIONAL_ADDED_FIELDS = ['is_admin', 'active']
PERMISSION_ADDED_FIELDS = ['name']
RESP_FIELDS = [
    'id', 'email', 'is_admin', 'active', 'firstname',
    'lastname', 'created_at', 'updated_at'
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
    """Check user has permission"""
    with session.begin(subtransactions=True):
        if user.is_admin:
            return

        user_permission = utils.get_db_object(
            session, models.UserPermission,
            False, user_id=user.id, name=permission.name
        )
        if not usr_permission:
            raise exception.Forbidden(
                'user %s does not have permission %s' % (
                    user.email, permission_name
                )
            )


def check_user_permission_internal(session, user, permission):
    """internal function only used by other db.api modules."""
    _check_user_permission(session, user, permission)

def _add_user_permissions(session, user, **permission_filters):
    """add permissions to a user."""
    from compass.db.api import permission as permission_api
    with session.begin(subtransactions=True):
        for permission in permission_api.list_permissions_internal(
            session, **permission_filters
        ):
            utils.add_db_object(
                session, models.UserPermission, False,
                user.id, permission.id
            )


def _remove_user_permissions(session, user, **permission_filters):
    """remove permissions to a user."""
    from compass.db.api import permission as permission_api
    with session.begin(subtransactions=True):
        for permission in permission_api.list_permissions_internal(
            session, **permission_filters
        ):
            utils.del_db_objects(
                session, models.UserPermission,
                user_id=user.id, permission_id=permission.id
            )


def _set_user_permissions(session, user, **permission_filters):
    """set permissions to a user."""
    from compass.db.api import permission as permission_api
    with session.begin(subtransactions=True):
        utils.del_db_objects(
                session, models.UserPermission,
                user_id=user.id, permission_id=permission.id
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
        super(UserWrapper, self).__init__()

    def authenticate(self, password):
        if not util.encrypt(password, self.password) == self.password:
            raise exception.Forbidden('%s password mismatch' % self.email)

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


def get_user_object(email, **kwargs):
    with database.session() as session:
        user_dict = utils.get_db_object(
            session, models.User, email=email
        ).to_dict()
        user_dict.update(kwargs)
        return UserWrapper(**user_dict)


def get_user_object_from_token(token):
    expire_timestamp = {
        'ge': datetime.datetime.now()
    }
    with database.session() as session:
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


def record_user_token(user, token, expire_timestamp):
    """record user token in database."""
    with database.session() as session:
        utils.add_db_object(
            session, models.UserToken, True,
            token, user_id=user.id,
            expire_timestamp=expire_timestamp
        )


def clean_user_token(user, token):
    """clean user token in database."""
    with database.session() as session:
        utils.del_db_objects(
            session, models.UserToken,
            user_id=user.id, token=token
        )



@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters()
def get_user(getter, user_id, **kwargs):
    """get field dict of a user."""
    with database.session() as session:
        user = utils.get_db_object(session, models.User, id=user_id)
        if not getter.is_admin and getter_id != user_id:
            # The user is not allowed to get user
            raise exception.Forbidden(
                'User %s has no permission to list user %s.' % (
                    getter.email, user.email
                )
            )

        return user.to_dict()


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters(
    optional_support_keys=SUPPORTED_FIELDS
)
def list_users(lister, **filters):
    """List fields of all users by some fields."""
    with database.session() as session:
        if not lister.is_admin:
            # The user is not allowed to list users
            raise exception.Forbidden(
                'User %s has no permission to list users.' % (
                    lister.email
                )
            )
        
        return [
            user.to_dict()
            for user in utils.list_db_objects(
                session, models.User, **filters
            )
        ]


@utils.wrap_to_dict(RESP_FIELDS)
@utils.input_validates(email=_check_email)
@utils.supported_filters(
    ADDED_FIELDS, optional_support_keys=OPTIONAL_ADDED_FIELDS
) 
def add_user(creator, email, password, **kwargs):
    """Create a user and return created user object."""
    with database.session() as session:
        if not creator.is_admin:
            # The user is not allowed to create a user.
            raise exception.Forbidden(
                'User %s has no permission to create user.' % (
                    creator.email
                )
            )

        return add_user_internal(
            session, email, password, **kwargs
        ).to_dict()


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters()
def del_user(deleter, user_id, **kwargs):
    """delete a user and return the deleted user object."""
    with database.session() as session:
        if not deleter.is_admin:
            raise exception.Forbidden(
                'User %s has no permission to delete user.' % (
                    deleter.email
                )
            )

        user = utils.get_db_object(session, models.User, id=user_id)
        utils.del_db_object(session, user)
        return user.to_dict()


@utils.wrap_to_dict(RESP_FIELDS)
@utils.input_validates(email=_check_email)
@utils.supported_filters(optional_support_keys=UPDATED_FIELDS)
def update_user(updater, user_id, **kwargs):
    """Update a user and return the updated user object."""
    with database.session() as session:
        user = utils.get_db_object(session, models.User, id=user_id)
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

        if updater.id == user_id:
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
            raise exception.Forbidden(
                'User %s has no permission to update user %s: %s.' % (
                    updater.email, user.email, kwargs
                )
            )

        utils.update_db_object(session, user, **update_info)
        return user.to_dict()


@utils.wrap_to_dict(PERMISSION_RESP_FIELDS)
@utils.supported_filters(optional_support_keys=PERMISSION_SUPPORTED_FIELDS)
def get_permissions(getter, user_id, **kwargs):
    """List permissions of a user."""
    with database.session() as session:
        if not getter.is_admin and getter_id != user_id:
            # The user is not allowed to list permissions
            raise exception.Forbidden(
                'User %s has no permission to list user %s permissions.' % (
                    getter.email, user.email
                )
            )
        user_permissions = utils.list_db_objects(
            session, models.UserPermission, user_id=user_id, **kwargs
        )
        return [
            user_permission.to_dict()
            for user_permission in user_permissions
        ]


@utils.wrap_to_dict(PERMISSION_RESP_FIELDS)
@utils.supported_filters()
def get_permission(getter, user_id, permission_id, **kwargs):
    """Get a specific user permission."""
    with database.session() as session:
        if not getter.is_admin and getter_id != user_id:
            # The user is not allowed to get permission
            raise exception.Forbidden(
                'User %s has no permission to get user %s permission.' % (
                    getter.email, user.email
                )
            )

        user_permission = utils.get_db_object(
            session, models.UserPermission,
            user_id=user_id, permission_id=permission_id,
            **kwargs
        )
        return user_permission.to_dict()


@utils.wrap_to_dict(PERMISSION_RESP_FIELDS)
@utils.supported_filters()
def del_permission(deleter, user_id, permission_id, **kwargs):
    """Delete a specific user permission."""
    with database.session() as session:
        if not deleter.is_admin and deleter_id != user_id:
            # The user is not allowed to delete permission
            raise exception.Forbidden(
                'User %s has no permission to delete user %s permission.' % (
                    getter.email, user.email
                )
            )

        user_permission = utils.get_db_object(
            session, models.UserPermission,
            user_id=user_id, permission_id=permission_id,
            **kwargs
        )
        utils.del_db_object(session, user_permission)
        return user_permission.to_dict()


@utils.wrap_to_dict(PERMISSION_RESP_FIELDS)
@utils.supported_filters(
    PERMISSION_ADDED_FIELDS
) 
def add_permission(creator, user_id, name):
    """Add an user permission."""
    with database.session() as session:
        if not creator.is_admin:
            # The user is not allowed to add a permission.
            raise exception.Forbidden(
                'User %s has no permission to add a permission.' % (
                    creator.email
                )
            )

        permission = utils.get_db_object(
            session, models.Permission, name=name
        )
        user_permission = utils.add_db_object(
            session, models.UserPermission, True,
            user_id, permission.id
        )
        return user_permission.to_dict() 
            

@utils.wrap_to_dict(PERMISSION_RESP_FIELDS)
@utils.supported_filters(
    optional_support_keys=[
        'add_permissions', 'remove_permissions', 'set_permissions'
    ]
)
def update_permissions(updater, user_id,
                      add_permissions=[], remove_permissions=[],
                      set_permissions=None, **kwargs):
    """update user permissions."""
    def get_permission_filters(permission_ids):
        if permission_ids == 'all':
            return {}
        else:
            return {'id': permission_ids}

    with database.session() as session:
        if not updater.is_admin:
            raise exception.Forbidden(
                'User %s has no permission to update user %s: %s.' % (
                    updater.email, user.email, kwargs
                )
            )
        user = utils.get_db_object(session, models.User, id=user_id)
        if remove_permissions:
            _remove_user_permissions(
                session, user,
                **get_permission_filters(remove_permissions)
            )

        if add_permissions:
            _add_user_permissions(
                session, user,
                **get_permission_filters(add_permissions)
            )

        if set_permissions is not None:
            _set_user_permissions(
                session, user,
                **get_permission_filters(set_permissions)
            )

        return [
            user_permission.to_dict()
            for user_permission in user.user_permissions
        ]
