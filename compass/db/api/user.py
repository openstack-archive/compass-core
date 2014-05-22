from compass.db import api
from compass.db.api import database
from compass.db.api.utils import wrap_to_dict
from compass.db.exception import *
from compass.db.models import User


SUPPORTED_FILTERS = ['email', 'admin']
UPDATED_FIELDS = ['firstname', 'lastname', 'password']
RESP_FIELDS = ['id', 'email', 'is_admin', 'active', 'firstname',
               'lastname', 'created_at', 'last_login_at']

ERROR_MSG = {
    'findNoUser': 'Cannot find the user, ID is %d',
    'duplicatedUser': 'User already exists!',
    'forbidden': 'User has no permission to make this request.'
}


@wrap_to_dict(RESP_FIELDS)
def get_user(user_id):
    with database.session() as session:
        try:
            user = _get_user(session, user_id)
        except RecordNotExists as ex:
            raise RecordNotExists(ex.message)

        user_info = user.to_dict()

    return user_info


@wrap_to_dict(RESP_FIELDS)
def list_users(filters=None):
    """List all users, optionally filtered by some fields"""
    with database.session() as session:
        users = _list_users(session, filters)
        users_list = [user.to_dict() for user in users]

    return users_list


@wrap_to_dict(RESP_FIELDS)
def add_user(creator_id, email, password, firstname=None, lastname=None):
    """Create a user"""
    REQUIRED_PERM = 'create_user'

    with database.session() as session:

        try:
            creator = _get_user(session, admin_id)
        except RecordNotExists as ex:
            raise RecordNotExists(ex.message)

        if not creator.is_admin or REQUIRED_PERM not in creator.permissions:
            # The user is not allowed to create a user.
            err_msg = ERROR_MSG['forbidden']
            raise Forbidden(err_msg)

        if session.query(User).filter_by(email=email).first():
            # The user already exists!
            err_msg = ERROR_MSG['duplicatedUser']
            raise DuplicatedRecord(err_msg)

        new_user = _add_user(email, password, firstname, lastname)
        new_user_info = new_user.to_dict()

    return new_user_info


@wrap_to_dict(RESP_FIELDS)
def update_user(user_id, **kwargs):
    """Update a user"""
    with database.session() as session:
        user = _get_user(session, user_id)
        try:
            user = _get_user(session, user_id)
        except RecordNotExists as ex:
            raise RecordNotExists(ex.message)

        update_info = {}
        for key in kwargs:
            if key in UPDATED_FIELDS:
                update_info[key] = kwargs[key]

        user = _update_user(**update_info)
        user_info = user.to_dict()

    return user_info


def _get_user(session, user_id):
    """Get the user by ID"""
    with session.begin(subtransactions=True):
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            err_msg = ERROR_MSG['findNoUser'] % user_id
            raise RecordNotExists(err_msg)

    return user


def _list_users(session, filters=None):
    """Get all users, optionally filtered by some fields"""

    filters = filters if filters else {}

    with session.begin(subtransactions=True):
        query = api.model_query(session, User)
        users = api.model_filter(query, User, filters, SUPPORTED_FILTERS).all()

    return users


def _add_user(session, email, password, firstname=None, lastname=None):
    """Create a user"""
    with session.begin(subtransactions=True):
        user = User(email=email, password=password,
                    firstname=firstname, lastname=lastname)
        session.add(user)

    return user


def _update_user(session, user_id, **kwargs):
    """Update user information"""
    with session.begin(subtransactions=True):
        session.query(User).filter_by(id=user_id).update(kwargs)
        user = _get_user(session, user_id)

    return user


def _add_permission(session, user_id, permissions):
    """Add permissions for the user"""
    pass


def _remove_permission(session, user_id, permissions):
    """Remove permissions for the user"""
    pass


def _delete_user(session, user_id):
    """Delete a user"""
    pass


def _list_permissions(session, user_id):
    """Get all permissions for the user"""
    pass


def _get_token(session, user_id):
    """Generate a token for the user"""
    pass
