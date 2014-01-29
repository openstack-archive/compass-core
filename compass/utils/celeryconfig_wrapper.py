"""celeryconfig wrapper."""
import logging
import os.path

from compass.utils import setting_wrapper as setting


CELERY_RESULT_BACKEND = 'amqp://'

BROKER_URL = 'amqp://guest:guest@localhost:5672//'

CELERY_IMPORTS = ('compass.tasks.tasks',)


if setting.CELERYCONFIG_FILE:
    CELERY_CONFIG = os.path.join(setting.CELERYCONFIG_DIR,
                                setting.CELERYCONFIG_FILE)

    try:
        logging.info('load celery config from %s', CELERY_CONFIG)
        execfile(CELERY_CONFIG, globals(), locals())
    except Exception as error:
        logging.exception(error)
        raise error
