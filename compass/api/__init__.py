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

import datetime
from flask import Blueprint
from flask.ext.login import LoginManager
from flask import Flask

# from compass.api.v1.api import v1_app
from compass.utils import setting_wrapper as setting
from compass.utils import util


app = Flask(__name__)
app.debug = True
# blueprint = Blueprint('v2_app', __name__)
# app.register_blueprint(v1_app, url_prefix='/v1.0')
# app.register_blueprint(blueprint, url_prefix='/api')


app.config['SECRET_KEY'] = 'abcd'
app.config['AUTH_HEADER_NAME'] = setting.USER_AUTH_HEADER_NAME
app.config['REMEMBER_COOKIE_DURATION'] = (
    datetime.timedelta(
        seconds=util.parse_time_interval(setting.USER_TOKEN_DURATION)
    )
)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)
