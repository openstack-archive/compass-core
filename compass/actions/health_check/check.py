"""Main Entry Point of Compass Health Check"""

from compass.actions.health_check import check_apache as apache
from compass.actions.health_check import check_celery as celery
from compass.actions.health_check import check_dhcp as dhcp
from compass.actions.health_check import check_dns as dns
from compass.actions.health_check import check_hds as hds
from compass.actions.health_check import (
    check_os_installer as os_installer)
from compass.actions.health_check import (
    check_package_installer as package_installer)
from compass.actions.health_check import check_squid as squid
from compass.actions.health_check import check_tftp as tftp
from compass.actions.health_check import check_misc as misc
from compass.actions.health_check import base


class BootCheck(base.BaseCheck):
    """health check for all components"""

    def run(self):
        """do health check"""
        status = {}
        status['apache'] = self.check_apache()
        status['celery'] = self.check_celery()
        status['dhcp'] = self.check_dhcp()
        status['dns'] = self.check_dns()
        status['hds'] = self.check_hds()
        status['os_installer'] = self.check_os_installer()
        status['package_installer'] = self.check_package_installer()
        status['squid'] = self.check_squid()
        status['tftp'] = self.check_tftp()
        status['other'] = self.check_misc()

        return status

    def check_apache(self):
        """do apache health check"""
        checker = apache.ApacheCheck()
        return checker.run()

    def check_celery(self):
        """do celery health check"""
        checker = celery.CeleryCheck()
        return checker.run()

    def check_dhcp(self):
        """do dhcp health check"""
        checker = dhcp.DhcpCheck()
        return checker.run()

    def check_dns(self):
        """do dns health check"""
        checker = dns.DnsCheck()
        return checker.run()

    def check_hds(self):
        """do hds health check"""
        checker = hds.HdsCheck()
        return checker.run()

    def check_os_installer(self):
        """do os installer health check"""
        checker = os_installer.OsInstallerCheck()
        return checker.run()

    def check_package_installer(self):
        """do package installer health check"""
        checker = package_installer.PackageInstallerCheck()
        return checker.run()

    def check_squid(self):
        """do squid health check"""
        checker = squid.SquidCheck()
        return checker.run()

    def check_tftp(self):
        """do tftp health check"""
        checker = tftp.TftpCheck()
        return checker.run()

    def check_misc(self):
        """do misc health check"""
        checker = misc.MiscCheck()
        return checker.run()
