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
import logging

from compass.db.api import database
from compass.db.api import user as user_api
from compass.db.api import utils
from compass.db import exception
from compass.db import models


SUPPORTED_FIELDS = ['user_email', 'timestamp']
USER_SUPPORTED_FIELDS = ['timestamp']
RESP_FIELDS = ['user_id', 'logs', 'timestamp']


@database.run_in_session()
def log_user_action(user_id, action, session=None):
    """Log user action."""
    utils.add_db_object(
        session, models.UserLog, True, user_id=user_id, action=action
    )


@utils.supported_filters(optional_support_keys=USER_SUPPORTED_FIELDS)
@user_api.check_user_admin_or_owner()
@database.run_in_session()
@utils.wrap_to_dict(RESP_FIELDS)
def list_user_actions(lister, user_id, session=None, **filters):
    """list user actions."""
    return utils.list_db_objects(
        session, models.UserLog, order_by=['timestamp'],
        user_id=user_id, **filters
    )


@utils.supported_filters(optional_support_keys=SUPPORTED_FIELDS)
@user_api.check_user_admin()
@database.run_in_session()
@utils.wrap_to_dict(RESP_FIELDS)
def list_actions(lister, session=None, **filters):
    """list actions."""
    return utils.list_db_objects(
        session, models.UserLog, order_by=['timestamp'], **filters
    )


@utils.supported_filters()
@user_api.check_user_admin_or_owner()
@database.run_in_session()
@utils.wrap_to_dict(RESP_FIELDS)
def del_user_actions(deleter, user_id, session=None, **filters):
    """delete user actions."""
    return utils.del_db_objects(
        session, models.UserLog, user_id=user_id, **filters
    )


@utils.supported_filters()
@user_api.check_user_admin()
@database.run_in_session()
@utils.wrap_to_dict(RESP_FIELDS)
def del_actions(deleter, session=None, **filters):
    """delete actions."""
    return utils.del_db_objects(
        session, models.UserLog, **filters
    )
