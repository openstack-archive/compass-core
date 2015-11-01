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
import lazypy
import logging
import os
import os.path


# default setting
CONFIG_DIR = os.environ.get('COMPASS_CONFIG_DIR', '/etc/compass')
SQLALCHEMY_DATABASE_URI = 'sqlite://'
SQLALCHEMY_DATABASE_POOL_TYPE = 'static'
COBBLER_INSTALLATION_LOGDIR = '/var/log/cobbler/anamon'
CHEF_INSTALLATION_LOGDIR = '/var/log/chef'
INSTALLATION_LOGDIR = {
    'CobblerInstaller': COBBLER_INSTALLATION_LOGDIR,
    'ChefInstaller': CHEF_INSTALLATION_LOGDIR
}
CLUSTERHOST_INATALLATION_LOGDIR_NAME = 'name'
HOST_INSTALLATION_LOGDIR_NAME = 'name'
DEFAULT_LOGLEVEL = 'debug'
DEFAULT_LOGDIR = '/tmp'
DEFAULT_LOGINTERVAL = 1
DEFAULT_LOGINTERVAL_UNIT = 'h'
DEFAULT_LOGFORMAT = (
    '%(asctime)s - %(filename)s - %(lineno)d - %(levelname)s - %(message)s')
DEFAULT_LOGBACKUPCOUNT = 5
WEB_LOGFILE = ''
CELERY_LOGFILE = ''
CELERYCONFIG_DIR = lazypy.delay(lambda: CONFIG_DIR)
CELERYCONFIG_FILE = ''
PROGRESS_UPDATE_INTERVAL = 30
POLLSWITCH_INTERVAL = 60
SWITCHES = [
]

USER_AUTH_HEADER_NAME = 'X-Auth-Token'
USER_TOKEN_DURATION = '2h'
COMPASS_ADMIN_EMAIL = 'admin@huawei.com'
COMPASS_ADMIN_PASSWORD = 'admin'
COMPASS_DEFAULT_PERMISSIONS = [
    'list_permissions',
]
SWITCHES_DEFAULT_FILTERS = []
DEFAULT_SWITCH_IP = '0.0.0.0'
DEFAULT_SWITCH_PORT = 0

COMPASS_SUPPORTED_PROXY = 'http://127.0.0.1:3128'
COMPASS_SUPPORTED_DEFAULT_NOPROXY = ['127.0.0.1']
COMPASS_SUPPORTED_NTP_SERVER = '127.0.0.1'
COMPASS_SUPPORTED_DNS_SERVERS = ['127.0.0.1']
COMPASS_SUPPORTED_DOMAINS = []
COMPASS_SUPPORTED_DEFAULT_GATEWAY = '127.0.0.1'
COMPASS_SUPPORTED_LOCAL_REPO = 'http://127.0.0.1'

PROGRESS_UPDATE_PID_FILE = '/var/run/progress_update.pid'

PROXY_URL_PREFIX = 'http://10.145.81.205:5000'

OS_INSTALLER_DIR = ''
PACKAGE_INSTALLER_DIR = ''
OS_DIR = ''
ADAPTER_DIR = ''
OS_METADATA_DIR = ''
PACKAGE_METADATA_DIR = ''
FLAVOR_METADATA_DIR = ''
OS_FIELD_DIR = ''
PACKAGE_FIELD_DIR = ''
FLAVOR_FIELD_DIR = ''
ADAPTER_ROLE_DIR = ''
ADAPTER_FLAVOR_DIR = ''
VALIDATOR_DIR = ''
CALLBACK_DIR = ''
TMPL_DIR = ''
MACHINE_LIST_DIR = ''
PROGRESS_CALCULATOR_DIR = ''
OS_MAPPING_DIR = ''
FLAVOR_MAPPING_DIR = ''
PLUGINS_DIR = ''

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

if not OS_INSTALLER_DIR:
    OS_INSTALLER_DIR = os.path.join(CONFIG_DIR, 'os_installer')

if not PACKAGE_INSTALLER_DIR:
    PACKAGE_INSTALLER_DIR = os.path.join(CONFIG_DIR, 'package_installer')

if not OS_DIR:
    OS_DIR = os.path.join(CONFIG_DIR, 'os')

if not ADAPTER_DIR:
    ADAPTER_DIR = os.path.join(CONFIG_DIR, 'adapter')

if not OS_METADATA_DIR:
    OS_METADATA_DIR = os.path.join(CONFIG_DIR, 'os_metadata')

if not PACKAGE_METADATA_DIR:
    PACKAGE_METADATA_DIR = os.path.join(CONFIG_DIR, 'package_metadata')

if not FLAVOR_METADATA_DIR:
    FLAVOR_METADATA_DIR = os.path.join(CONFIG_DIR, 'flavor_metadata')

if not OS_FIELD_DIR:
    OS_FIELD_DIR = os.path.join(CONFIG_DIR, 'os_field')

if not PACKAGE_FIELD_DIR:
    PACKAGE_FIELD_DIR = os.path.join(CONFIG_DIR, 'package_field')

if not FLAVOR_FIELD_DIR:
    FLAVOR_FIELD_DIR = os.path.join(CONFIG_DIR, 'flavor_field')

if not ADAPTER_ROLE_DIR:
    ADAPTER_ROLE_DIR = os.path.join(CONFIG_DIR, 'role')

if not ADAPTER_FLAVOR_DIR:
    ADAPTER_FLAVOR_DIR = os.path.join(CONFIG_DIR, 'flavor')

if not VALIDATOR_DIR:
    VALIDATOR_DIR = os.path.join(CONFIG_DIR, 'validator')

if not CALLBACK_DIR:
    CALLBACK_DIR = os.path.join(CONFIG_DIR, 'callback')

if not TMPL_DIR:
    TMPL_DIR = os.path.join(CONFIG_DIR, 'templates')

if not MACHINE_LIST_DIR:
    MACHINE_LIST_DIR = os.path.join(CONFIG_DIR, 'machine_list')

if not PROGRESS_CALCULATOR_DIR:
    PROGRESS_CALCULATOR_DIR = os.path.join(CONFIG_DIR, 'progress_calculator')

if not OS_MAPPING_DIR:
    OS_MAPPING_DIR = os.path.join(CONFIG_DIR, 'os_mapping')

if not FLAVOR_MAPPING_DIR:
    FLAVOR_MAPPING_DIR = os.path.join(CONFIG_DIR, 'flavor_mapping')

if not PLUGINS_DIR:
    PLUGINS_DIR = os.environ.get('COMPASS_PLUGINS_DIR',
                                 os.path.join(CONFIG_DIR, 'plugins'))
