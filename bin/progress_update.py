#!/usr/bin/python
"""main script to run as service to update hosts installing progress."""
import functools
import lockfile
import logging

from compass.actions import update_progress
from compass.tasks.client import celery
from compass.utils import daemonize
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import setting_wrapper as setting
from compass.utils import util


flags.add('clusters',
          help=(
              'clusters to clean, the format is as '
              'clusterid:hostname1,hostname2,...;...'),
          default='')
flags.add_bool('async',
               help='run in async mode',
               default=True)
flags.add('run_interval',
          help='run interval in seconds',
          default=setting.PROGRESS_UPDATE_INTERVAL)


def progress_update(cluster_hosts):
    """entry function."""
    if flags.OPTIONS.async:
        celery.send_task('compass.tasks.update_progress', (cluster_hosts,))
    else:
        try:
            update_progress.update_progress(cluster_hosts)
        except Exception as error:
            logging.error('failed to update progress for cluster_hosts: %s',
                          cluster_hosts)
            logging.exception(error)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    logging.info('run progress update')
    daemonize.daemonize(
        functools.partial(
            progress_update,
            util.get_clusters_from_str(flags.OPTIONS.clusters)),
        flags.OPTIONS.run_interval,
        pidfile=lockfile.FileLock('/var/run/progress_update.pid'),
        stderr=open('/tmp/progress_update_err.log', 'w+'),
        stdout=open('/tmp/progress_update_out.log', 'w+'))
