#!/usr/bin/python
"""main script to start an instance of compass server ."""
import logging

from compass.api import app
from compass.utils import flags
from compass.utils import logsetting


flags.add('server_host',
          help='server host address',
          default='0.0.0.0')
flags.add_bool('debug',
               help='run in debug mode',
               default=True)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    logging.info('run server')
    app.run(host=flags.OPTIONS.server_host, debug=flags.OPTIONS.debug)
