# Copyright 2014 Huawei Technologies Co. Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__all__ = ['Flask', 'SQLAlchemy', 'compass_api']
import datetime
from flask import Flask
from flask.ext.login import LoginManager
from compass.db.model import SECRET_KEY

app = Flask(__name__)
app.debug = True

app.secret_key = SECRET_KEY
app.config['AUTH_HEADER_NAME'] = 'X-Auth-Token'
app.config['REMEMBER_COOKIE_DURATION'] = datetime.timedelta(minutes=30)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

from compass.api import api as compass_api
