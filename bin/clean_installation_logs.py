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

"""clean all installation logs."""
import logging
import os
import os.path
import sys


current_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(current_dir)


import switch_virtualenv

from compass.utils import flags
from compass.utils import logsetting
from compass.utils import setting_wrapper as setting


def clean_installation_logs():
    installation_log_dirs = setting.INSTALLATION_LOGDIR
    successful = True
    for _, logdir in installation_log_dirs.items():
        cmd = 'rm -rf %s/*' % logdir
        status = os.system(cmd)
        logging.info('run cmd %s resturns %s', cmd, status)
        if status:
            successful = False
    return successful


if __name__ == "__main__":
    flags.init()
    logsetting.init()
    clean_installation_logs()
