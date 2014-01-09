#!/usr/bin/python

import logging
import sys

from compass.db import database
from compass.db.model import Cluster
from compass.tasks.client import celery
from compass.utils import flags
from compass.utils import logsetting
from compass.actions import trigger_install


flags.add('clusterids',
          help='comma seperated cluster ids',
          default='')
flags.add_bool('async',
               help='ryn in async mode')


def main(argv):
    flags.init()
    logsetting.init()
    clusterids = [
        int(clusterid) for clusterid in flags.OPTIONS.clusterids.split(',')
        if clusterid
    ]
    with database.session() as session:
        if not clusterids:
            clusters = session.query(Cluster).all()
            trigger_clusterids  = [cluster.id for cluster in clusters]
        else:
            trigger_clusterids = clusterids
        logging.info('trigger installer for clusters: %s',
                     trigger_clusterids)
        for clusterid in trigger_clusterids:
            if flags.OPTIONS.async:
                celery.send_task('compass.tasks.trigger_install',
                                 (clusterid,))
            else:
                trigger_install.trigger_install(clusterid)


if __name__ == '__main__':
    main(sys.argv)
  
