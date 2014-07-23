#!/usr/bin/env python
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import setting_wrapper as setting

flags.init()
flags.OPTIONS.logfile = setting.WEB_LOGFILE
logsetting.init()

from compass.api import api as compass_api
compass_api.init()
application = compass_api.app
