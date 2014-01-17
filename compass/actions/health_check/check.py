import check_apache as apache
import check_celery as celery
import check_dhcp as dhcp
import check_dns as dns
import check_hds as hds
import check_os_installer as os_installer
import check_package_installer as package_installer
import check_squid as squid
import check_tftp as tftp
import check_misc as misc

import base

class BootCheck(base.BaseCheck):

    def run(self):
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
        checker = apache.ApacheCheck()
        return checker.run()

    def check_celery(self):
        checker = celery.CeleryCheck()
        return checker.run()

    def check_dhcp(self):
        checker = dhcp.DhcpCheck()
        return checker.run()

    def check_dns(self):
        checker = dns.DnsCheck()
        return checker.run()

    def check_hds(self):
        checker = hds.HdsCheck()
        return checker.run()

    def check_os_installer(self):
        checker = os_installer.OsInstallerCheck()
        return checker.run()

    def check_package_installer(self):
        checker = package_installer.PackageInstallerCheck()
        return checker.run()

    def check_squid(self):
        checker = squid.SquidCheck()
        return checker.run()

    def check_tftp(self):
        checker = tftp.TftpCheck()
        return checker.run()

    def check_misc(self):
        checker = misc.MiscCheck()
        return checker.run()
