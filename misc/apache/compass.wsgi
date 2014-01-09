#!/usr/bin/env python
from compass.api import app as application
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import setting_wrapper as setting

flags.init()
flags.OPTIONS.logfile = setting.WEB_LOGFILE
logsetting.init()
