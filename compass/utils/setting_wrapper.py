"""comapss setting wrapper."""
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
OS_INSTALLER = 'cobbler'
COBBLER_INSTALLER_URL = ''
COBBLER_INSTALLER_TOKEN = ['cobbler', 'cobbler']
PACKAGE_INSTALLER = 'chef'
CHEF_INSTALLER_URL = ''
CHEF_GLOBAL_DATABAG_NAME = 'env_default'
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
