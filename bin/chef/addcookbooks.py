#!/usr/bin/env python

import logging
import os
import os.path


from compass.utils import flags
from compass.utils import logsetting


flags.add('cookbooks_dir',
          help='chef cookbooks directory',
          default='/var/chef/cookbooks')


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    cookbooks = []
    cookbooks_dir = flags.OPTIONS.cookbooks_dir
    logging.info('add cookbooks %s', cookbooks_dir)
    cmd = "knife cookbook upload --all --cookbook-path %s" % cookbooks_dir
    os.system(cmd)

