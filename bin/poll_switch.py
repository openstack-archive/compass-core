#!/usr/bin/python
"""main script to poll machines which is connected to the switches."""
import daemon
import lockfile
import logging
import sys
import signal
import time

from compass.actions import poll_switch 
from compass.db import database
from compass.db.model import Switch
from compass.tasks.client import celery
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import setting_wrapper as setting


flags.add('switchids',
          help='comma seperated switch ids',
          default='')
flags.add_bool('async',
               help='ryn in async mode',
               default=True)
flags.add_bool('once',
               help='run once or forever',
               default=False)
flags.add('run_interval',
          help='run interval in seconds',
          default=setting.POLLSWITCH_INTERVAL)
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
    global BUSY
    global KILLED
    switchids = [int(switchid) for switchid in flags.OPTIONS.switchids.split(',') if switchid]
    signal.signal(signal.SIGTERM, handle_term)
    signal.signal(signal.SIGHUP, handle_term)

    while True:
        BUSY = True
        with database.session() as session:
            switch_ips = {}
            switches = session.query(Switch).all()
            for switch in switches:
                switch_ips[switch.id] = switch.ip
            if not switchids:
                poll_switchids  = [switch.id for switch in switches]
            else:
                poll_switchids = switchids
            logging.info('poll switches to get machines mac: %s',
                         poll_switchids)
            for switchid in poll_switchids:
                if switchid not in switch_ips:
                    logging.error('there is no switch ip for switch %s',
                                  switchid)
                    continue
                if flags.OPTIONS.async:
                    celery.send_task('compass.tasks.pollswitch',
                                     (switch_ips[switchid],))
                else:
                    try:
                        poll_switch.poll_switch(switch_ips[switchid])
                    except Exception as error:
                        logging.error('failed to poll switch %s',
                                      switch_ips[switchid])

        BUSY = False
        if KILLED:
            logging.info('exit poll switch loop')
            break

        if flags.OPTIONS.once:
            logging.info('finish poll switch')
            break
    
        if flags.OPTIONS.run_interval > 0:
            logging.info('will rerun poll switch after %s seconds',
                         flags.OPTIONS.run_interval)
            time.sleep(flags.OPTIONS.run_interval)
        else:
            logging.info('rerun poll switch imediately')
        

if __name__ == '__main__':
    flags.init()
    logsetting.init()
    logging.info('run poll_switch: %s', sys.argv)
    if flags.OPTIONS.daemonize:
        with daemon.DaemonContext(
            pidfile=lockfile.FileLock('/var/run/poll_switch.pid'),
            stderr=open('/tmp/poll_switch_err.log', 'w+'),
            stdout=open('/tmp/poll_switch_out.log', 'w+')
        ):
            logging.info('run poll switch as daemon')
            main(sys.argv)
    else:
        main(sys.argv)
