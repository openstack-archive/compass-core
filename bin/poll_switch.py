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
import logging
import os
import sys


current_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(current_dir)


import switch_virtualenv

import lockfile
from multiprocessing import Pool

from compass.actions import poll_switch
from compass.actions import util
from compass.db.api import database
from compass.db.api import switch as switch_api
from compass.db.api import user as user_api
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
flags.add('thread_pool_size', type='int',
          help='thread pool size when run in noasync mode',
          default=4)
flags.add('run_interval', type='int',
          help='run interval in seconds',
          default=setting.POLLSWITCH_INTERVAL)


def pollswitches(switch_ips):
    """poll switch."""
    user = user_api.get_user_object(setting.COMPASS_ADMIN_EMAIL)
    poll_switches = []
    all_switches = dict([
        (switch['ip'], switch['credentials'])
        for switch in switch_api.list_switches(user=user)
    ])
    if switch_ips:
        poll_switches = dict([
            (switch_ip, all_switches[switch_ip])
            for switch_ip in switch_ips
            if switch_ip in all_switches
        ])
    else:
        poll_switches = all_switches

    if flags.OPTIONS.async:
        for switch_ip, switch_credentials in poll_switches.items():
            celery.send_task(
                'compass.tasks.pollswitch',
                (user.email, switch_ip, switch_credentials)
            )

    else:
        try:
            pool = Pool(processes=flags.OPTIONS.thread_pool_size)
            for switch_ip, switch_credentials in poll_switches.items():
                pool.apply_async(
                    poll_switch.poll_switch,
                    (user.email, switch_ip, switch_credentials)
                )
            pool.close()
            pool.join()
        except Exception as error:
            logging.error('failed to poll switches %s',
                          poll_switches)
            logging.exception(error)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    database.init()
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
