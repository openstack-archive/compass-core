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

"""main script to poll machines which is connected to the switches."""
import functools
import lockfile
import logging

from multiprocessing import Pool

from compass.actions import poll_switch
from compass.actions import util
from compass.db import database
from compass.tasks.client import celery
from compass.utils import daemonize
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import setting_wrapper as setting


flags.add('switch_ips',
          help='comma seperated switch ips',
          default='')
flags.add_bool('async',
               help='ryn in async mode',
               default=True)
flags.add('thread_pool_size',
          help='thread pool size when run in noasync mode',
          default='4')
flags.add('run_interval',
          help='run interval in seconds',
          default=setting.POLLSWITCH_INTERVAL)


def pollswitches(switch_ips):
    """poll switch."""
    poll_switch_ips = []
    with database.session():
        poll_switch_ips = util.update_switch_ips(switch_ips)

    if flags.OPTIONS.async:
        for poll_switch_ip in poll_switch_ips:
            celery.send_task(
                'compass.tasks.pollswitch',
                (poll_switch_ip,)
            )

    else:
        try:
            pool = Pool(processes=int(flags.OPTIONS.thread_pool_size))
            for poll_switch_ip in poll_switch_ips:
                pool.apply_async(
                    poll_switch.poll_switch,
                    (poll_switch_ip,)
                )

            pool.close()
            pool.join()
        except Exception as error:
            logging.error('failed to poll switches %s',
                          poll_switch_ips)
            logging.exception(error)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    logging.info('run poll_switch')
    daemonize.daemonize(
        functools.partial(
            pollswitches,
            [switch_ip
             for switch_ip in flags.OPTIONS.switch_ips.split(',')
             if switch_ip]),
        flags.OPTIONS.run_interval,
        pidfile=lockfile.FileLock('/var/run/poll_switch.pid'),
        stderr=open('/tmp/poll_switch_err.log', 'w+'),
        stdout=open('/tmp/poll_switch_out.log', 'w+'))
