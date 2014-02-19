"""test package_installer module"""
import os
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from compass.config_management.installers import package_installer
from compass.utils import flags
from compass.utils import logsetting


class DummyInstaller(package_installer.Installer):
    """dummy installer"""
    NAME = 'dummy'

    def __init__(self):
        pass


class Dummy2Installer(package_installer.Installer):
    """another dummy installer"""
    NAME = 'dummy'

    def __init__(self):
        pass


class TestInstallerFunctions(unittest2.TestCase):
    """test installer functions"""

    def setUp(self):
        super(TestInstallerFunctions, self).setUp()
        logsetting.init()
        self.installers_backup = package_installer.INSTALLERS
        package_installer.INSTALLERS = {}

    def tearDown(self):
        package_installer.INSTALLERS = self.installers_backup
        super(TestInstallerFunctions, self).tearDown()

    def test_found_installer(self):
        """test found installer"""
        package_installer.register(DummyInstaller)
        intaller = package_installer.get_installer_by_name(
            DummyInstaller.NAME)
        self.assertIsInstance(intaller, DummyInstaller)

    def test_notfound_unregistered_installer(self):
        """test not found unregistered installer"""
        self.assertRaises(KeyError, package_installer.get_installer_by_name,
                          DummyInstaller.NAME)

    def test_multi_registered_installer(self):
        """test register multi installers with the same name"""
        package_installer.register(DummyInstaller)
        self.assertRaises(KeyError, package_installer.register,
                          Dummy2Installer)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
