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
import sys

from flask import flash
from flask import redirect
from flask import request
from flask import session as app_session
from flask import url_for

from compass.api import app
from compass.api import auth
from compass.api import exception
from compass.api import login_manager
from compass.api import utils

from flask.ext.login import current_user
from flask.ext.login import login_required
from flask.ext.login import login_user
from flask.ext.login import logout_user


@login_manager.header_loader
def load_user_from_token(token):
    """Return a user object from token."""

    duration = app.config['REMEMBER_COOKIE_DURATION']
    max_age = 0
    if sys.version_info > (2, 6):
        max_age = duration.total_seconds()
    else:
        max_age = (duration.microseconds + (
            duration.seconds + duration.days * 24 * 3600) * 1e6) / 1e6

    user_id = auth.get_user_id_from_token(token, max_age)
    if not user_id:
        logging.info("No user can be found from the token!")
        return None

    user = _get_user(user_id)
    return user


@login_manager.user_loader
def load_user(user_id):
    """Load user from user ID."""
    return _get_user(user_id)


@app.route('/logout')
@login_required
def logout():
    """User logout."""
    logout_user()
    flash('You have logged out!')
    return redirect('/login.html')


@app.route('/')
def index():
    """Index page."""
    return redirect('/login.html')


@app.route('/token', methods=['POST'])
def get_token():
    """Get token from email and passowrd after user authentication."""
    data = json.loads(request.data)
    email = data['email']
    password = data['password']

    user = auth.authenticate_user(email, password)
    if not user:
        error_msg = "User cannot be found or email and password do not match!"
        return exception.handle_invalid_user(
            exception.Unauthorized(error_msg)
        )

    token = user.get_auth_token()
    login_user(user)

    return utils.make_json_response(
        200, {"status": "OK", "token": token}
    )


@app.route("/login", methods=['GET', 'POST'])
def login():
    """User login."""
    if current_user.is_authenticated():
        return redirect(url_for('index'))
    else:
        if request.method == 'POST':
            if request.form['email'] and request.form['password']:
                email = request.form['email']
                password = request.form['password']

                user = auth.authenticate_user(email, password)
                if not user:
                    flash('Wrong username or password!', 'error')
                    next_url = '/login.html?next=' % request.args.get('next')
                    return redirect(next_url)

                if login_user(user, remember=request.form['remember']):
                    # Enable session expiration if user didnot choose to be
                    # remembered.
                    app_session.permanent = not request.form['remember']
                    flash('Logged in successfully!', 'success')
                    return redirect(
                        request.args.get('next') or url_for('index'))
                else:
                    flash('This username is disabled!', 'error')

        return redirect('/login.html')


def _get_user(user_id):

    from compass.db.models import User
    try:
        user = User.query.filter_by(id=user_id).first()
        return user

    except Exception as err:
        logging.info('Failed to get user from id %d! Error: %s', (id, err))
        return None


if __name__ == '__main__':
    app.run(debug=True)
