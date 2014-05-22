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

from compass.db.models import login_serializer


def get_user_id_from_token(token, max_age):
    """Return user's ID and hased password from token."""

    user_id = None
    try:
        user_id = login_serializer.loads(token, max_age=max_age)

    except BadData as err:
        logging.error("[auth][get_user_info_from_token] Exception: %s", err)
        return None

    return user_id


def authenticate_user(email, pwd):
    """Authenticate a user by email and password."""

    from compass.db.models import User
    try:
        user = User.query.filter_by(email=email).first()
        if user and user.valid_password(pwd):
            return user
    except Exception as err:
        logging.info('[auth][authenticate_user]Exception: %s', err)

    return None
