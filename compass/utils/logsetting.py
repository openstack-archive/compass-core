"""Module to setup logging configuration.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""

import logging
import logging.handlers
import os
import sys
import os.path

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
            logfile = os.path.basename(sys.argv[0])

        handler = logging.handlers.TimedRotatingFileHandler(
            os.path.join(logdir, logfile),
            when=flags.OPTIONS.log_interval_unit,
            interval=flags.OPTIONS.log_interval)
    else:
        if not logfile:
            handler = logging.StreamHandler(sys.stderr)
        else:
            handler = logging.FileHandler(logfile)

    if loglevel in LOGLEVEL_MAPPING:
        logger.setLevel(LOGLEVEL_MAPPING[loglevel])
        handler.setLevel(LOGLEVEL_MAPPING[loglevel])

    formatter = logging.Formatter(
        flags.OPTIONS.log_format)

    handler.setFormatter(formatter)
    logger.addHandler(handler)
