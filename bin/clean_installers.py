#!/usr/bin/env python
#
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

"""Scripts to delete cluster and it hosts"""
import logging
import os
import os.path
import sys


current_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(current_dir)


import switch_virtualenv

from compass.actions import clean
from compass.db.api import adapter_holder as adapter_api
from compass.db.api import database
from compass.db.api import user as user_api
from compass.tasks.client import celery
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import setting_wrapper as setting


flags.add_bool('async',
               help='run in async mode',
               default=True)

flags.add('os_installers',
          help='comma seperated os installers',
          default='')
flags.add('package_installers',
          help='comma separated package installers',
          default='')


def clean_installers():
    os_installers = [
        os_installer
        for os_installer in flags.OPTIONS.os_installers.split(',')
        if os_installer
    ]
    package_installers = [
        package_installer
        for package_installer in flags.OPTIONS.package_installers.split(',')
        if package_installer
    ]
    user = user_api.get_user_object(setting.COMPASS_ADMIN_EMAIL)
    adapters = adapter_api.list_adapters(user=user)
    filtered_os_installers = {}
    filtered_package_installers = {}
    for adapter in adapters:
        logging.info(
            'got adapter: %s', adapter
        )
        if 'os_installer' in adapter:
            os_installer = adapter['os_installer']
            os_installer_name = os_installer['alias']
            if not os_installers or os_installer_name in os_installers:
                filtered_os_installers[os_installer_name] = os_installer
            else:
                logging.info(
                    'ignore os installer %s', os_installer_name
                )
        else:
            logging.info(
                'cannot find os installer in adapter %s',
                adapter['name']
            )
        if 'package_installer' in adapter:
            package_installer = adapter['package_installer']
            package_installer_name = package_installer['alias']
            if (
                not package_installers or
                package_installer_name in package_installers
            ):
                filtered_package_installers[package_installer_name] = (
                    package_installer
                )
            else:
                logging.info(
                    'ignore package installer %s', package_installer_name
                )
        else:
            logging.info(
                'cannot find package installer in adapter %s',
                adapter['name']
            )
    logging.info(
        'clean os installers: %s', filtered_os_installers.keys()
    )
    logging.info(
        'clean package installers: %s', filtered_package_installers.keys()
    )
    if flags.OPTIONS.async:
        for os_installer_name, os_installer in filtered_os_installers.items():
            celery.send_task(
                'compass.tasks.clean_os_installer',
                (
                    os_installer['name'],
                    os_installer['settings']
                )
            )
        for package_installer_name, package_installer in (
            filtered_package_installers.items()
        ):
            celery.send_task(
                'compass.tasks.clean_package_installer',
                (
                    package_installer['name'],
                    package_installer['settings']
                )
            )
    else:
        for os_installer_name, os_installer in (
            filtered_os_installers.items()
        ):
            try:
                clean.clean_os_installer(
                    os_installer['name'],
                    os_installer['settings']
                )
            except Exception as error:
                logging.error(
                    'failed to clean os installer %s', os_installer_name
                )
                logging.exception(error)
        for package_installer_name, package_installer in (
            filtered_package_installers.items()
        ):
            try:
                clean.clean_package_installer(
                    package_installer['name'],
                    package_installer['settings']
                )
            except Exception as error:
                logging.error(
                    'failed to clean package installer %s',
                    package_installer_name
                )
                logging.exception(error)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    database.init()
    clean_installers()
