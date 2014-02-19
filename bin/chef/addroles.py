#!/usr/bin/env python
"""script to import roles to chef server"""
import logging
import os
import os.path

from compass.utils import flags
from compass.utils import logsetting


flags.add('roles_dir',
          help='chef roles directory',
          default='/var/chef/roles')


def main():
    """main entry"""
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
        os.system(cmd)


if __name__ == '__main__':
    main()
