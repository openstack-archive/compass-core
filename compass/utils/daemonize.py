"""Module to provider util functions in all compass code

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import daemon
import logging
import sys
import signal
import time

from compass.utils import flags


flags.add_bool('daemonize',
               help='run as daemon',
               default=False)


BUSY = False
KILLED = False


def handle_term(signum, frame):
    """Handle sig term."""
    global KILLED
    logging.info('Caught signal %s in %s', signum, frame)
    KILLED = True
    if not BUSY:
        sys.exit(0)


def _daemon(callback, run_interval):
    """help function to run callback in daemon"""
    global BUSY
    signal.signal(signal.SIGTERM, handle_term)
    signal.signal(signal.SIGHUP, handle_term)

    while True:
        BUSY = True
        callback()
        BUSY = False
        if KILLED:
            logging.info('exit loop')
            break

        if run_interval > 0:
            logging.info('will rerun after %s seconds',
                         flags.OPTIONS.run_interval)
            time.sleep(flags.OPTIONS.run_interval)
        else:
            logging.info('finish loop')
            break


def daemonize(callback, run_interval, **kwargs):
    """daemonize callback and run every run_interval seconds."""
    if flags.OPTIONS.daemonize:
        with daemon.DaemonContext(**kwargs):
            logging.info('run as daemon')
            _daemon(callback, run_interval)
    else:
        _daemon(callback, run_interval)
