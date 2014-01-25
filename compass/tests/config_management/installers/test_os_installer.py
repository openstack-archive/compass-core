import unittest2

from compass.config_management.installers import os_installer


class DummyInstaller(os_installer.Installer):
    NAME = 'dummy'

    def __init__(self):
        pass


class Dummy2Installer(os_installer.Installer):
    NAME = 'dummy'

    def __init__(self):
        pass


class TestInstallerFunctions(unittest2.TestCase):
    def setUp(self):
        self.installers_backup = os_installer.INSTALLERS
        os_installer.INSTALLERS = {}

    def tearDown(self):
        os_installer.INSTALLERS = self.installers_backup

    def test_found_installer(self):
        os_installer.register(DummyInstaller)
        intaller = os_installer.get_installer_by_name(DummyInstaller.NAME)
        self.assertIsInstance(intaller, DummyInstaller)

    def test_notfound_unregistered_installer(self):
        self.assertRaises(KeyError, os_installer.get_installer_by_name,
                          DummyInstaller.NAME)

    def test_multi_registered_installer(self):
        os_installer.register(DummyInstaller)
        self.assertRaises(KeyError, os_installer.register, Dummy2Installer)


if __name__ == '__main__':
    unittest2.main()
