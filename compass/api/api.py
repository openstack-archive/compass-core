#!/usr/bin/python
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

"""Define all the RestfulAPI entry points."""
import logging
import simplejson as json

from flask import flash
from flask import redirect
from flask import request
from flask import session as app_session
from flask import url_for

from flask.ext.login import current_user
from flask.ext.login import login_required
from flask.ext.login import login_user
from flask.ext.login import logout_user

from compass.api import app
from compass.api import auth_handler
from compass.api import exception_handler
from compass.api import utils

from compass.db.api import user as user_api

from compass.utils import flags
from compass.utils import logsetting


@app.route('/users/logout', methods=['POST'])
@login_required
def logout():
    """User logout."""
    logout_user()


def _login(data, use_cookie):
    """User login helper function."""
    data = json.loads(data)
    email = data['email']
    password = data['password']
    user = auth_handler.authenticate_user(email, password)
    remember = data.get('remember', False)
    if login_user(user, remember=remember):
        app_session.permanent = remember
    else:
        raise exception_handler.UserDisabled('failed to login: %s' % user)

    response_data = {'id': user.id}
    if not use_cookie:
        response_data['token'] = user.get_auth_token()

    return utils.make_json_response(200, response_data)


@app.route('/users/token', methods=['POST'])
def get_token():
    """Get token from email and password after user authentication."""
    return _login(request.data, False)


@app.route("/users/login", methods=['POST'])
def login():
    """User login"""
    return _login(request.data, True)


@app.route("/users", methods=['GET'])
@login_required
def list_users():
    """list users"""
    data = request.args
    users = user_api.list_users(current_user.id, **data)
    return utils.make_json_response(
        200, users
    )


@app.route("/users", methods=['POST'])
@login_required
def add_user():
    """add user."""
    data = json.loads(request.data)
    email = data['email']
    del data['email']
    password = data['password']
    del data['password']
    return utils.make_json_response(
        201,
        user_api.add_user(current_user.id, email, password, **data)
    )


@app.route("/users/<int:user_id>", methods=['GET'])
@login_required
def show_user(user_id):
    return utils.make_json_response(
        200, user_api.get_user(current_user.id, user_id)
    )


@app.route("/users/<int:user_id>", methods=['PUT'])
@login_required
def update_user(user_id):
    return utils.make_json_response(
        200,
        user_api.update_user(
            current_user.id,
            user_id,
            **(json.loads(request.data))
        )
    )

@app.route("/users/<int:user_id>", methods=['DELETE'])
@login_required
def delete_user(user_id):
    return utils.make_json_response(
        200,
        user_api.del_user(
            current_user.id, user_id
        )
    )


@app.route("/users/<int:user_id>/permissions", methods=['GET'])
@login_required
def get_permissions(user_id):
    return utils.make_json_response(
        200, user_api.get_permissions(current_user.id, user_id)
    )


@app.route("/users/<int:user_id>/permissions", methods=['POST'])
@login_required
def update_permissions(user_id):
    data = json.loads(request.data)
    return utils.make_json_response(
        200,
        user_api.update_permissions(
            current_user.id, user_id,
            add_permissions=data.get('add', []),
            remove_permissions=data.get('remove', []),
            set_permissions=data.get('set', None)
        )
    )


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    app.run(host='0.0.0.0')
