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


def authenticate_user(email, password, **kwargs):
    """Authenticate a user by email and password."""
    user = user_api.get_user_object(
        email, **kwargs
    )
    user.authenticate(password)
    return user


@login_manager.token_loader
def load_user_from_token(token):
    return user_api.get_user_object_from_token(token)


@login_manager.header_loader
def load_user_from_header(header):
    """Return a user object from token."""
    return user_api.get_user_object_from_token(header)


@login_manager.user_loader
def load_user(token):
    return user_api.get_user_object_from_token(token)
