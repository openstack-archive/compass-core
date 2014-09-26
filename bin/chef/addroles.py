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

"""script to import roles to chef server."""
import logging
import os
import os.path
import sys


current_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(current_dir)


import switch_virtualenv

from compass.utils import flags
from compass.utils import logsetting


flags.add('roles_dir',
          help='chef roles directory',
          default='/var/chef/roles')


def main():
    """main entry."""
    flags.init()
    logsetting.init()
    rolelist = []
    roles_dir = flags.OPTIONS.roles_dir

    for item in os.listdir(roles_dir):
        if item.endswith('.rb') or item.endswith('.json'):
            rolelist.append(os.path.join(roles_dir, item))
        else:
            logging.info('ignore %s in %s', item, roles_dir)

    for role in rolelist:
        logging.info('add role %s', role)
        cmd = "knife role from file %s" % role
        status = os.system(cmd)
        logging.info('run cmd %s returns %s', cmd, status)
        if status:
            sys.exit(1)


if __name__ == '__main__':
    main()
