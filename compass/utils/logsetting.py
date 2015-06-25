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

"""Module to setup logging configuration.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""

import logging
import logging.handlers
import os
import os.path
import sys

from compass.utils import flags
from compass.utils import setting_wrapper as setting


flags.add('loglevel',
          help='logging level', default=setting.DEFAULT_LOGLEVEL)
flags.add('logdir',
          help='logging directory', default=setting.DEFAULT_LOGDIR)
flags.add('logfile',
          help='logging filename', default=None)
flags.add('log_interval', type='int',
          help='log interval', default=setting.DEFAULT_LOGINTERVAL)
flags.add('log_interval_unit',
          help='log interval unit', default=setting.DEFAULT_LOGINTERVAL_UNIT)
flags.add('log_format',
          help='log format', default=setting.DEFAULT_LOGFORMAT)
flags.add('log_backup_count', type='int',
          help='log backup count', default=setting.DEFAULT_LOGBACKUPCOUNT)


# mapping str setting in flag --loglevel to logging level.
LOGLEVEL_MAPPING = {
    'finest': logging.DEBUG - 2,  # more detailed log.
    'fine': logging.DEBUG - 1,    # detailed log.
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
}


logging.addLevelName(LOGLEVEL_MAPPING['fine'], 'fine')
logging.addLevelName(LOGLEVEL_MAPPING['finest'], 'finest')


# disable logging when logsetting.init not called
logging.getLogger().setLevel(logging.CRITICAL)


def getLevelByName(level_name):
    """Get log level by level name."""
    return LOGLEVEL_MAPPING[level_name]


def init():
    """Init loggsetting. It should be called after flags.init."""
    loglevel = flags.OPTIONS.loglevel.lower()
    logdir = flags.OPTIONS.logdir
    logfile = flags.OPTIONS.logfile
    logger = logging.getLogger()
    if logger.handlers:
        for handler in logger.handlers:
            logger.removeHandler(handler)

    if logdir:
        if not logfile:
            logfile = '%s.log' % os.path.basename(sys.argv[0])

        handler = logging.handlers.TimedRotatingFileHandler(
            os.path.join(logdir, logfile),
            when=flags.OPTIONS.log_interval_unit,
            interval=flags.OPTIONS.log_interval,
            backupCount=flags.OPTIONS.log_backup_count)
    else:
        if not logfile:
            handler = logging.StreamHandler(sys.stderr)
        else:
            handler = logging.handlers.TimedRotatingFileHandler(
                logfile,
                when=flags.OPTIONS.log_interval_unit,
                interval=flags.OPTIONS.log_interval,
                backupCount=flags.OPTIONS.log_backup_count)

    if loglevel in LOGLEVEL_MAPPING:
        logger.setLevel(LOGLEVEL_MAPPING[loglevel])
        handler.setLevel(LOGLEVEL_MAPPING[loglevel])

    formatter = logging.Formatter(
        flags.OPTIONS.log_format)

    handler.setFormatter(formatter)
    logger.addHandler(handler)
