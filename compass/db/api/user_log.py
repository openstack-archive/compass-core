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

"""UserLog database operations."""
from compass.db.api import database
from compass.db.api import user as user_api
from compass.db.api import utils
from compass.db import exception
from compass.db import models


SUPPORTED_FIELDS = ['user_email', 'timestamp']
USER_SUPPORTED_FIELDS = ['timestamp']
RESP_FIELDS = ['user_id', 'logs', 'timestamp']


def log_user_action(user_id, action):
    """Log user action."""
    with database.session() as session:
        utils.add_db_object(
            session, models.UserLog, user_id=user_id, action=action
        )


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters(optional_support_keys=USER_SUPPORTED_FIELDS)
def list_user_actions(lister, user_id, **filters):
    """list user actions."""
    with database.session() as session:
        user = user_api.get_user_internal(session, id=user_id)
        if not lister.is_admin and lister_id != user_id:
            # The user is not allowed to list users actions.
            raise Forbidden(
                'User %s has no permission to list user %s actions.' % (
                    lister.email, user.email
                )
            )

        user_actions = []
        for action in utils.list_db_objects(
                session, models.UserLog, user_id=user_id, **filters
        ):
            action_dict = action.to_dict()
            del action_dict['user_id']
            user_actions.append(action_dict)

        return {'user_id': user_id, 'logs': user_actions}


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters(optional_support_keys=SUPPORTED_FIELDS)
def list_actions(lister, **filters):
    """list actions."""
    with database.session() as session:
        if not lister.is_admin:
             # The user is not allowed to list users actions.
            raise Forbidden(
                'User %s has no permission to list all users actions.' % (
                    lister.email, user.email
                )
            )

        actions = {}
        for action in utils.list_db_objects(
            session, models.UserLog, **filters
        ):
            action_dict = action.to_dict()
            user_id = action_dict['user_id']
            del action_dict['user_id']
            actions.setdefault(user_id, []).append(action_dict)

        return [
            {'user_id': user_id, 'logs': user_actions}
            for user_id, user_actions in actions.items()
        ]


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters(optional_support_keys=USER_SUPPORTED_FIELDS)
def del_user_actions(deleter, user_id, **filters):
    """delete user actions."""
    with database.session() as session:
        user = user_api.get_user_internal(session, id=user_id)
        if not deleter.is_admin and deleter_id != user_id:
            # The user is not allowed to delete users actions.
            raise Forbidden(
                'User %s has no permission to delete user %s actions.' % (
                    deleter.email, user.email
                )
            )

        user_actions = []
        for action in utils.del_db_objects(
                session, models.UserLog, user_id=user_id, **filters
        ):
            action_dict = action.to_dict()
            del action_dict['user_id']
            user_actions.append(action_dict)

        return {'user_id': user_id, 'logs': user_actions}


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters(optional_support_keys=SUPPORTED_FIELDS)
def del_actions(deleter, **filters):
    """delete actions."""
    with database.session() as session:
        if not deleter.is_admin:
            # The user is not allowed to delete users actions.
            raise Forbidden(
                'User %s has no permission to delete all users actions.' % (
                    deleter.email, user.email
                )
            )

        actions = {}
        for action in utils.del_db_objects(
            session, models.UserLog, **filters
        ):
            action_dict = action.to_dict()
            user_id = action_dict['user_id']
            del action_dict['user_id']
            actions.setdefault(user_id, []).append(action_dict)

        return [
            {'user_id': user_id, 'logs': user_actions}
            for user_id, user_action in actions.items()
        ]
