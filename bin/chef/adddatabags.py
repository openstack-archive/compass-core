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

"""import databags to chef server."""
import logging
import os
import os.path
import sys


current_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(current_dir)


import switch_virtualenv

from compass.utils import flags
from compass.utils import logsetting


flags.add('databags_dir',
          help='chef databags directory',
          default='/var/chef/databags')


def main():
    """main entry."""
    flags.init()
    logsetting.init()
    databags = []
    databags_dir = flags.OPTIONS.databags_dir
    for item in os.listdir(databags_dir):
        databags.append(item)

    for databag in databags:
        logging.info('add databag %s', databag)
        cmd = "knife data bag create %s" % databag
        os.system(cmd)
        databag_items = []
        databagitem_dir = os.path.join(databags_dir, databag)
        for item in os.listdir(databagitem_dir):
            if item.endswith('.json'):
                databag_items.append(os.path.join(databagitem_dir, item))
            else:
                logging.info('ignore %s in %s', item, databagitem_dir)

        for databag_item in databag_items:
            logging.info('add databag item %s to databag %s',
                         databag_item, databag)
            cmd = 'knife data bag from file %s %s' % (databag, databag_item)
            status = os.system(cmd)
            logging.info('run cmd %s returns %s', cmd, status)
            if status:
                sys.exit(1)


if __name__ == '__main__':
    main()
