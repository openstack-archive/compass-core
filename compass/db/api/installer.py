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

"""Adapter database operations."""
import logging
import os

from compass.db.api import database
from compass.db.api import utils
from compass.db import exception
from compass.db import models

from compass.utils import setting_wrapper as setting
from compass.utils import util


def _add_installers(session, model, configs):
    installers = []
    for config in configs:
        installers.append(utils.add_db_object(
            session, model,
            True, config['NAME'],
            installer_type=config['TYPE'],
            config=config['CONFIG']
        ))
    return installers


def add_os_installers_internal(session):
    configs = util.load_configs(setting.OS_INSTALLER_DIR)
    return _add_installers(session, models.OSInstaller, configs)


def add_package_installers_internal(session):
    configs = util.load_configs(setting.PACKAGE_INSTALLER_DIR)
    return _add_installers(session, models.PackageInstaller, configs)
