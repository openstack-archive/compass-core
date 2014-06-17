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

from itsdangerous import BadData
import logging
import sys

from compass.api import app
from compass.api import exception_handler
from compass.api import login_manager

from compass.db.api import user as user_api
from compass.db.api.user import UserWrapper


def _get_user_from_token(token):
    """Return user object from token."""
    duration = app.config['REMEMBER_COOKIE_DURATION']
    max_age = 0
    if sys.version_info[0:2] > (2, 6):
        max_age = duration.total_seconds()
    else:
        max_age = (duration.microseconds + (
            duration.seconds + duration.days * 24 * 3600) * 1e6) / 1e6

    try:
        user_id = UserWrapper.get_user_id(token, max_age=max_age)
    except BadData as err:
        raise exception_handler.Unauthorized('invalid token %s' % token)

    return user_api.get_user_object(id=user_id)


def authenticate_user(email, pwd):
    """Authenticate a user by email and password."""
    user = user_api.get_user_object(email=email)
    if user.authenticate(pwd):
        return user
    else:
        raise exception_handler.BadRequest('invalid password or email: %s' % email)


@login_manager.token_loader
def load_user_from_token(token):
    print 'get user from token: %s' % token
    return _get_user_from_token(token)


@login_manager.header_loader
def load_user_from_header(header):
    """Return a user object from token."""
    return _get_user_from_token(header)


@login_manager.user_loader
def load_user(user_id):
    """Load user from user ID."""
    return user_api.get_user_object(id=user_id)
