#!/usr/bin/env python
#
# Copyright 2014 Openstack Foundation
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
        role_file = os.path.join(roles_dir, item)
        rolelist.append(role_file)

    for role in rolelist:
        logging.info('add role %s', role)
        cmd = "knife role from file %s" % role
        status = os.system(cmd)
        if status:
            return status


if __name__ == '__main__':
    main()
