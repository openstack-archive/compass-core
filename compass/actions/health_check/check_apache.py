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

"""Health Check module for Apache service."""

import socket
import urllib2

from compass.actions.health_check import base
from compass.actions.health_check import utils as health_check_utils


class ApacheCheck(base.BaseCheck):
    """apache server health check class."""
    NAME = "Apache Check"

    def run(self):
        """do the healthcheck."""
        if self.dist in ("centos", "redhat", "fedora", "scientific linux"):
            apache_service = 'httpd'
        else:
            apache_service = 'apache2'
        self.check_apache_conf(apache_service)
        print "[Done]"
        self.check_apache_running(apache_service)
        print "[Done]"
        if self.code == 1:
            self.messages.append(
                "[%s]Info: Apache health check has completed. "
                "No problems found, all systems go." % self.NAME)
        return (self.code, self.messages)

    def check_apache_conf(self, apache_service):
        """Validates if Apache settings.

        :param apache_service  : service type of apache, os dependent.
                                 e.g. httpd or apache2
        :type apache_service   : string

        """
        print "Checking Apache Config......",
        conf_err_msg = health_check_utils.check_path(
            self.NAME,
            "/etc/%s/conf.d/ods-server.conf" % apache_service)
        if not conf_err_msg == "":
            self._set_status(0, conf_err_msg)

        wsgi_err_msg = health_check_utils.check_path(
            self.NAME,
            '/var/www/compass/compass.wsgi')
        if not wsgi_err_msg == "":
            self._set_status(0, wsgi_err_msg)

        return True

    def check_apache_running(self, apache_service):
        """Checks if Apache service is running on port 80."""

        print "Checking Apache service......",
        serv_err_msg = health_check_utils.check_service_running(self.NAME,
                                                                apache_service)
        if not serv_err_msg == "":
            self._set_status(0, serv_err_msg)
        if 'http' != socket.getservbyport(80):
            self._set_status(
                0,
                "[%s]Error: Apache is not listening on port 80."
                % self.NAME)
        try:
            html = urllib2.urlopen('http://localhost')
            html.geturl()
        except Exception:
            self._set_status(
                0,
                "[%s]Error: Apache is not listening on port 80."
                % self.NAME)

        return True
