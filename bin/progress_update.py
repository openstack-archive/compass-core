#!/usr/bin/python
"""main script to run as service to update hosts installing progress."""
import logging
import signal
import sys
import time
import daemon

from compass.actions import progress_update
from compass.db import database
from compass.db.model import Cluster
from compass.tasks.client import celery
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import setting_wrapper as setting


flags.add('clusterids',
          help='comma seperated cluster ids',
          default='')
flags.add_bool('async',
               help='ryn in async mode',
               default=True)
flags.add_bool('once',
               help='run once or forever',
               default=False)
flags.add('run_interval',
          help='run interval in seconds',
          default=setting.PROGRESS_UPDATE_INTERVAL)
flags.add_bool('daemonize',
               help='run as daemon',
               default=False)


BUSY = False
KILLED = False

def handle_term(signum, frame):
    global BUSY
    global KILLED
    logging.info('Caught signal %s', signum)
    KILLED = True
    if not BUSY:
        sys.exit(0)


def main(argv):
    """entry function."""
    global BUSY
    global KILLED
    clusterids = [
        int(clusterid) for clusterid in flags.OPTIONS.clusterids.split(',')
        if clusterid
    ]
    signal.signal(signal.SIGINT, handle_term)

    while True:
        BUSY = True
        with database.session() as session:
            if not clusterids:
                clusters = session.query(Cluster).all()
                update_clusterids = [cluster.id for cluster in clusters]
            else:
                update_clusterids = clusterids

        logging.info('update progress for clusters: %s', update_clusterids)
        for clusterid in update_clusterids:
            if flags.OPTIONS.async:
                celery.send_task('compass.tasks.progress_update', (clusterid,))
            else:
                try:
                    progress_update.update_progress(clusterid)
                except Exception as error:
                    logging.error('failed to update progress for cluster %s',
                                  clusterid)
                    logging.exception(error)
                    pass

        BUSY = False
        if KILLED:
            logging.info('exit progress update loop')
            break

        if flags.OPTIONS.once:
            logging.info('trigger installer finsished')
            break

        if flags.OPTIONS.run_interval > 0:
            logging.info('will rerun the trigger install after %s',
                         flags.OPTIONS.run_interval)
            time.sleep(flags.OPTIONS.run_interval)
        else:
            logging.info('rerun the trigger installer immediately')


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    logging.info('run progress update: %s', sys.argv)
    if flags.OPTIONS.daemonize:
        with daemon.DaemonContext(
            pidfile=lockfile.FileLock('/var/run/progress_update.pid'),
            stderr=open('/tmp/progress_update_err.log', 'w+'),
            stdout=open('/tmp/progress_update_out.log', 'w+')
        ):
            logging.info('run progress update as daemon') 
            main(sys.argv)
    else:
        main(sys.argv)
