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

"""comapss setting wrapper.

   .. moduleauthor:: Xiaodong Wang ,xiaodongwang@huawei.com>
"""
import datetime
import logging
import os


# default setting
PROVIDER_NAME = 'mix'
GLOBAL_CONFIG_PROVIDER = 'file'
CLUSTER_CONFIG_PROVIDER = 'db'
HOST_CONFIG_PROVIDER = 'db'
CONFIG_DIR = '/etc/compass'
GLOBAL_CONFIG_FILENAME = 'global_config'
CONFIG_FILE_FORMAT = 'python'
DATABASE_TYPE = 'file'
DATABASE_FILE = ''
SQLALCHEMY_DATABASE_URI = 'sqlite://'
INSTALLATION_LOGDIR = ''
DEFAULT_LOGLEVEL = 'info'
DEFAULT_LOGDIR = '/tmp'
DEFAULT_LOGINTERVAL = 1
DEFAULT_LOGINTERVAL_UNIT = 'h'
DEFAULT_LOGFORMAT = (
    '%(asctime)s - %(filename)s - %(lineno)d - %(levelname)s - %(message)s')
WEB_LOGFILE = ''
CELERY_LOGFILE = ''
CELERYCONFIG_DIR = ''
CELERYCONFIG_FILE = ''
PROGRESS_UPDATE_INTERVAL = 30
POLLSWITCH_INTERVAL = 60
SWITCHES = [
]

USER_SECRET_KEY = datetime.datetime.now().isoformat()
USER_AUTH_HEADER_NAME = 'X-Auth-Token'
USER_TOKEN_DURATION = '2h'
COMPASS_ADMIN_EMAIL = 'admin@abc.com'
COMPASS_ADMIN_PASSWORD = 'admin'
COMPASS_DEFAULT_PERMISSIONS = [
    'list_permissions',
]
SWITCHES_DEFAULT_FILTERS = []
DEFAULT_SWITCH_IP = '0.0.0.0'
DEFAULT_SWITCH_PORT = 0
OS_INSTALLER_DIR = '/etc/compass/os_installer'
PACKAGE_INSTALLER_DIR = '/etc/compass/package_installer'
OS_DIR = '/etc/compass/os'
DISTRIBUTED_SYSTEM_DIR = '/etc/compass/distributed_system'
ADAPTER_DIR = '/etc/compass/adapter'
OS_METADATA_DIR = '/etc/compass/os_metadata'
PACKAGE_METADATA_DIR = '/etc/compass/package_metadata'
OS_FIELD_DIR = '/etc/compass/os_field'
PACKAGE_FIELD_DIR = '/etc/compass/package_field'
ADAPTER_ROLE_DIR = '/etc/compass/role'
VALIDATOR_DIR = '/etc/compass/validator'
TMPL_DIR = '/etc/compass/templates'
if (
    'COMPASS_IGNORE_SETTING' in os.environ and
    os.environ['COMPASS_IGNORE_SETTING']
):
    pass
else:
    if 'COMPASS_SETTING' in os.environ:
        SETTING = os.environ['COMPASS_SETTING']
    else:
        SETTING = '/etc/compass/setting'

    try:
        logging.info('load setting from %s', SETTING)
        execfile(SETTING, globals(), locals())
    except Exception as error:
        logging.exception(error)
        raise error
