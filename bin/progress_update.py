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

"""main script to run as service to update hosts installing progress."""
import functools
import logging
import os
import sys


current_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(current_dir)


import switch_virtualenv

import lockfile

from compass.actions import update_progress
from compass.db.api import database
from compass.tasks.client import celery
from compass.utils import daemonize
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import setting_wrapper as setting
from compass.utils import util


flags.add_bool('async',
               help='run in async mode',
               default=True)
flags.add('run_interval', type='int',
          help='run interval in seconds',
          default=setting.PROGRESS_UPDATE_INTERVAL)


def progress_update():
    """entry function."""
    if flags.OPTIONS.async:
        celery.send_task('compass.tasks.update_progress', ())
    else:
        try:
            update_progress.update_progress()
        except Exception as error:
            logging.error('failed to update progress')
            logging.exception(error)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    database.init()
    logging.info('run progress update')
    daemonize.daemonize(
        progress_update,
        flags.OPTIONS.run_interval,
        pidfile=lockfile.FileLock('/var/run/progress_update.pid'),
        stderr=open('/tmp/progress_update_err.log', 'w+'),
        stdout=open('/tmp/progress_update_out.log', 'w+'))
