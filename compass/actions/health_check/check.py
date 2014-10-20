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

"""Main Entry Point of Compass Health Check."""
from compass.actions.health_check import base
from compass.actions.health_check import check_apache
from compass.actions.health_check import check_celery
from compass.actions.health_check import check_dhcp
from compass.actions.health_check import check_dns
from compass.actions.health_check import check_hds
from compass.actions.health_check import check_misc
from compass.actions.health_check import check_os_installer
from compass.actions.health_check import check_package_installer
from compass.actions.health_check import check_squid
from compass.actions.health_check import check_tftp


class BootCheck(base.BaseCheck):
    """health check for all components."""

    def run(self):
        """do health check."""
        status = {}
        status['apache'] = self._check_apache()
        status['celery'] = self._check_celery()
        status['dhcp'] = self._check_dhcp()
        status['dns'] = self._check_dns()
        status['hds'] = self._check_hds()
        status['os_installer'] = self._check_os_installer()
        status['package_installer'] = self._check_package_installer()
        status['squid'] = self._check_squid()
        status['tftp'] = self._check_tftp()
        status['other'] = self._check_misc()

        return status

    def _check_apache(self):
        """do apache health check."""
        checker = check_apache.ApacheCheck()
        return checker.run()

    def _check_celery(self):
        """do celery health check."""
        checker = check_celery.CeleryCheck()
        return checker.run()

    def _check_dhcp(self):
        """do dhcp health check."""
        checker = check_dhcp.DhcpCheck()
        return checker.run()

    def _check_dns(self):
        """do dns health check."""
        checker = check_dns.DnsCheck()
        return checker.run()

    def _check_hds(self):
        """do hds health check."""
        checker = check_hds.HdsCheck()
        return checker.run()

    def _check_os_installer(self):
        """do os installer health check."""
        checker = check_os_installer.OsInstallerCheck()
        return checker.run()

    def _check_package_installer(self):
        """do package installer health check."""
        checker = check_package_installer.PackageInstallerCheck()
        return checker.run()

    def _check_squid(self):
        """do squid health check."""
        checker = check_squid.SquidCheck()
        return checker.run()

    def _check_tftp(self):
        """do tftp health check."""
        checker = check_tftp.TftpCheck()
        return checker.run()

    def _check_misc(self):
        """do misc health check."""
        checker = check_misc.MiscCheck()
        return checker.run()
