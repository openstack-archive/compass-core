#!/usr/bin/env python
import site
import sys
import os
site.addsitedir('$PythonHome/lib/python2.6/site-packages')
sys.path.append('$PythonHome')
os.environ['PYTHON_EGG_CACHE'] = '/tmp/.egg'

from compass.api import app as application
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import setting_wrapper as setting

flags.init()
flags.OPTIONS.logfile = setting.WEB_LOGFILE
logsetting.init()
