# Copyright 2014 Huawei Technologies Co. Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Health Check module for Celery."""
import commands
import os

from celery.task.control import inspect

from compass.actions.health_check import base
from compass.actions.health_check import utils as health_check_utils


class CeleryCheck(base.BaseCheck):
    """celery health check class."""
    NAME = "Celery Check."

    def run(self):
        """do health check."""
        self.check_compass_celery_setting()
        print "[Done]"
        self.check_celery_backend()
        print "[Done]"
        if self.code == 1:
            self.messages.append("[%s]Info: Celery health check "
                                 "has completed. No problems found, "
                                 "all systems go." % self.NAME)
        return (self.code, self.messages)

    def check_compass_celery_setting(self):
        """Validates Celery settings."""

        print "Checking Celery setting......",
        setting_map = {
            'logfile': 'CELERY_LOGFILE',
            'configdir': 'CELERYCONFIG_DIR',
            'configfile': 'CELERYCONFIG_FILE',
        }
        unset = []
        res = health_check_utils.validate_setting('Celery',
                                                  self.config,
                                                  'CELERY_LOGFILE')
        if res is False:
            unset.append(setting_map["logfile"])
            self._set_status(0, res)

        res = health_check_utils.validate_setting('Celery',
                                                  self.config,
                                                  'CELERYCONFIG_DIR')
        if res is False:
            unset.append(setting_map["configdir"])
            self._set_status(0, res)

        res = health_check_utils.validate_setting('Celery',
                                                  self.config,
                                                  'CELERYCONFIG_FILE')
        if res is False:
            unset.append(setting_map["configdir"])
            self._set_status(0, res)

        if len(unset) != 0:
            self._set_status(0,
                             "[%s]Error: Unset celery settings: %s"
                             " in /etc/compass/setting"
                             % (self.NAME, ', '.join(item for item in unset)))
        return True

    def check_celery_backend(self):
        """Checks if Celery backend is running and configured properly."""

        print "Checking Celery Backend......",
        if 'celery worker' not in commands.getoutput('ps -ef'):
            self._set_status(0, "[%s]Error: celery is not running" % self.NAME)
            return True

        if not os.path.exists('/etc/compass/celeryconfig'):
            self._set_status(
                0,
                "[%s]Error: No celery config file found for Compass"
                % self.NAME)
            return True

        try:
            insp = inspect()
            celery_stats = inspect.stats(insp)
            if not celery_stats:
                self._set_status(
                    0,
                    "[%s]Error: No running Celery workers were found."
                    % self.NAME)
        except IOError as error:
            self._set_status(
                0,
                "[%s]Error: Failed to connect to the backend: %s"
                % (self.NAME, str(error)))
            from errno import errorcode
            if (
                len(error.args) > 0 and
                errorcode.get(error.args[0]) == 'ECONNREFUSED'
            ):
                self.messages.append(
                    "[%s]Error: RabbitMQ server isn't running"
                    % self.NAME)
        return True
