#!/usr/bin/env python
"""import databags to chef server."""
import logging
import os
import os.path

from compass.utils import flags
from compass.utils import logsetting


flags.add('databags_dir',
          help='chef databags directory',
          default='/var/chef/databags')


def main():
    """main entry"""
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
            databag_items.append(os.path.join(databagitem_dir, item))

        for databag_item in databag_items:
            logging.info('add databag item %s to databag %s',
                         databag_item, databag)
            cmd = 'knife data bag from file %s %s' % (databag, databag_item)
            os.system(cmd)


if __name__ == '__main__':
    main()
