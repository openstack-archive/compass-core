"""comapss setting wrapper."""
import logging
import os


if 'COMPASS_SETTING' in os.environ:
    SETTING = os.environ['COMPASS_SETTING']
else:
    SETTING = '/etc/compass/setting'

try:
    execfile(SETTING, globals(), locals())
except Exception as error:
    logging.exception(error)
    raise error
