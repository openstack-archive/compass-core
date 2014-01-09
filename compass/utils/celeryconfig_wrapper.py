"""celeryconfig wrapper."""
import logging
import os.path

from compass.utils import setting_wrapper as setting


CELERY_CONFIG = os.path.join(setting.CELERYCONFIG_DIR,
                            setting.CELERYCONFIG_FILE)

try:
    execfile(CELERY_CONFIG, globals(), locals())
except Exception as error:
    logging.exception(error)
    raise error
