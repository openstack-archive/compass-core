#!/usr/bin/python
#
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

"""integration test for action deploy.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import chef
import logging
import mock
import os
import os.path
import shutil
import unittest2
import xmlrpclib

from contextlib import contextmanager


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from compass.actions import deploy
from compass.actions import util
from compass.db import database
from compass.db.model import Adapter
from compass.db.model import Cluster
from compass.db.model import ClusterHost
from compass.db.model import Machine
from compass.db.model import Role
from compass.db.model import Switch
from compass.utils import flags
from compass.utils import logsetting


class TestEndToEnd(unittest2.TestCase):
    """Integration test class."""

    def _contains(self, origin_config, expected_config):
        """check if expected config contains in origin config."""
        if isinstance(expected_config, dict):
            for key, value in expected_config.items():
                if not isinstance(origin_config, dict):
                    logging.error('%s type is not dict',
                                  origin_config)
                    return False

                if key not in origin_config:
                    logging.error('%s is not in config:\n%s',
                                  key, origin_config.keys())
                    return False

                if not self._contains(origin_config[key], value):
                    logging.error('%s is not match:\n%s\nvs\n%s',
                                  key, origin_config[key], value)
                    return False

            return True
        elif callable(expected_config):
            return expected_config(origin_config)
        else:
            return expected_config == origin_config

    def _mock_lock(self):
        @contextmanager
        def _lock(lock_name, blocking=True, timeout=10):
            """mock lock."""
            try:
                yield lock_name
            finally:
                pass

        self.lock_backup_ = util.lock
        util.lock = mock.Mock(side_effect=_lock)

    def _unmock_lock(self):
        util.lock = self.lock_backup_

    def _unmock_cobbler(self):
        xmlrpclib.Server = self.cobbler_server_backup_

    def _mock_cobbler(self, host_configs):
        """mock cobbler."""
        self.cobbler_server_backup_ = xmlrpclib.Server
        mock_server = mock.Mock()
        xmlrpclib.Server = mock_server
        mock_server.return_value.login.return_value = ''
        mock_server.return_value.sync = mock.Mock()
        mock_server.return_value.find_profile = mock.Mock(
            side_effect=lambda x: [x['name']])

        def _get_system_handle(sys_name, token):
            """mock get_system_handle."""
            for i, config in enumerate(host_configs):
                if config['name'] == sys_name:
                    return i

            raise Exception('Not Found %s' % sys_name)

        mock_server.return_value.get_system_handle = mock.Mock(
            side_effect=_get_system_handle)

        def _new_system(token):
            """mock new_system."""
            host_configs.append({'name': ''})
            return len(host_configs) - 1

        mock_server.return_value.new_system = mock.Mock(
            side_effect=_new_system)

        def _remove_system(sys_name, token):
            """mock remove system."""
            for i, config in host_configs:
                if config['name'] == sys_name:
                    del host_configs[i]
                    return

            raise Exception('Not Found %s' % sys_name)

        mock_server.return_value.remove_system = mock.Mock(
            side_effect=_remove_system)

        mock_server.return_value.save_system = mock.Mock()

        def _modify_system(sys_id, key, value, token):
            """mock modify_system."""
            host_configs[sys_id][key] = value

        mock_server.return_value.modify_system = mock.Mock(
            side_effect=_modify_system)

    def _check_cobbler(self, host_configs, expected_host_configs):
        """check cobbler config generated correctly."""
        self.assertEqual(len(host_configs), len(expected_host_configs))
        for i in range(len(host_configs)):
            self.assertTrue(
                self._contains(host_configs[i], expected_host_configs[i]),
                'host %s config is\n%s\nwhile expected config is\n%s' % (
                    i, host_configs[i], expected_host_configs[i]
                )
            )

    def _unmock_chef(self):
        chef.autoconfigure = self.chef_autoconfigure_backup_
        chef.DataBag = chef.chef_databag_backup_
        chef.DataBagItem = self.chef_databagitem_backup_
        chef.Client = self.chef_client_backup_
        chef.Node = self.chef_node_backup_

    def _mock_chef(self, configs):
        """mock chef."""
        self.chef_autoconfigure_backup_ = chef.autoconfigure
        chef.chef_databag_backup_ = chef.DataBag
        chef.autoconfigure = mock.Mock()
        chef.DataBag = mock.Mock()

        import collections

        class _mockDict(collections.Mapping):
            """mock dict class."""

            def __init__(in_self, bag, bag_item_name, api):
                in_self.bag_item_name_ = bag_item_name
                in_self.config_ = configs.get(bag_item_name, {})

            def __len__(in_self):
                return len(in_self.config_)

            def __iter__(in_self):
                return iter(in_self.config_)

            def __getitem__(in_self, name):
                return in_self.config_[name]

            def __setitem__(in_self, name, value):
                in_self.config_[name] = value

            def __delitem__(in_self, name):
                del in_self.config_[name]

            def delete(in_self):
                """mock delete."""
                del configs[in_self.bag_item_name_]

            def save(in_self):
                """mock save."""
                configs[in_self.bag_item_name_] = in_self.config_

        self.chef_databagitem_backup_ = chef.DataBagItem
        chef.DataBagItem = mock.Mock(side_effect=_mockDict)
        self.chef_client_backup_ = chef.Client
        chef.Client = mock.Mock()
        chef.Client.return_value.delete = mock.Mock()
        self.chef_node_backup_ = chef.Node
        chef.Node = mock.Mock()
        chef.Node.return_value.delete = mock.Mock()

    def _check_chef(self, configs, expected_configs):
        """check chef config is generated correctly."""
        self.assertTrue(
            self._contains(configs, expected_configs),
            'configs\n%s\nwhile expected configs\n%s' % (
                configs, expected_configs
            )
        )

    def _mock_os_installer(self, config_locals):
        """mock os installer."""
        self.os_installer_mock_[setting.OS_INSTALLER](
            **config_locals['%s_MOCK' % setting.OS_INSTALLER])

    def _unmock_os_installer(self):
        self.os_installer_unmock_[setting.OS_INSTALLER]()

    def _mock_package_installer(self, config_locals):
        """mock package installer."""
        self.package_installer_mock_[setting.PACKAGE_INSTALLER](
            **config_locals['%s_MOCK' % setting.PACKAGE_INSTALLER])

    def _unmock_package_installer(self):
        self.package_installer_unmock_[setting.PACKAGE_INSTALLER]()

    def _check_os_installer(self, config_locals):
        """check os installer generate correct configs."""
        mock_kwargs = config_locals['%s_MOCK' % setting.OS_INSTALLER]
        expected_kwargs = config_locals['%s_EXPECTED' % setting.OS_INSTALLER]
        kwargs = {}
        kwargs.update(mock_kwargs)
        kwargs.update(expected_kwargs)
        self.os_installer_checker_[setting.OS_INSTALLER](**kwargs)

    def _check_package_installer(self, config_locals):
        """check package installer generate correct configs."""
        mock_kwargs = config_locals['%s_MOCK' % setting.PACKAGE_INSTALLER]
        expected_kwargs = config_locals[
            '%s_EXPECTED' % setting.PACKAGE_INSTALLER]
        kwargs = {}
        kwargs.update(mock_kwargs)
        kwargs.update(expected_kwargs)
        self.package_installer_checker_[setting.PACKAGE_INSTALLER](**kwargs)

    def _test(self, config_filename):
        """run the test."""
        full_path = '%s/data/%s' % (
            os.path.dirname(os.path.abspath(__file__)),
            config_filename)
        config_globals = {}
        config_locals = {}
        execfile(full_path, config_globals, config_locals)
        self._prepare_database(config_locals)
        self._mock_os_installer(config_locals)
        self._mock_package_installer(config_locals)
        cluster_hosts = {}
        with database.session() as session:
            clusters = session.query(Cluster).all()
            for cluster in clusters:
                cluster_hosts[cluster.id] = [
                    host.id for host in cluster.hosts]

        deploy.deploy(cluster_hosts)

        self._check_os_installer(config_locals)
        self._check_package_installer(config_locals)
        self._unmock_os_installer()
        self._unmock_package_installer()

    def _prepare_database(self, config_locals):
        """prepare database."""
        with database.session() as session:
            adapters = {}
            for adapter_config in config_locals['ADAPTERS']:
                adapter = Adapter(**adapter_config)
                session.add(adapter)
                adapters[adapter_config['name']] = adapter

            roles = {}
            for role_config in config_locals['ROLES']:
                role = Role(**role_config)
                session.add(role)
                roles[role_config['name']] = role

            switches = {}
            for switch_config in config_locals['SWITCHES']:
                switch = Switch(**switch_config)
                session.add(switch)
                switches[switch_config['ip']] = switch

            machines = {}
            for switch_ip, machine_configs in (
                config_locals['MACHINES_BY_SWITCH'].items()
            ):
                for machine_config in machine_configs:
                    machine = Machine(**machine_config)
                    machines[machine_config['mac']] = machine
                    machine.switch = switches[switch_ip]
                    session.add(machine)

            clusters = {}
            for cluster_config in config_locals['CLUSTERS']:
                adapter_name = cluster_config['adapter']
                del cluster_config['adapter']
                cluster = Cluster(**cluster_config)
                clusters[cluster_config['name']] = cluster
                cluster.adapter = adapters[adapter_name]
                session.add(cluster)

            hosts = {}
            for cluster_name, host_configs in (
                config_locals['HOSTS_BY_CLUSTER'].items()
            ):
                for host_config in host_configs:
                    mac = host_config['mac']
                    del host_config['mac']
                    host = ClusterHost(**host_config)
                    hosts['%s.%s' % (
                        host_config['hostname'], cluster_name)] = host
                    host.machine = machines[mac]
                    host.cluster = clusters[cluster_name]
                    session.add(host)

    def _mock_setting(self):
        self.backup_os_installer_ = setting.OS_INSTALLER
        self.backup_package_installer_ = setting.PACKAGE_INSTALLER
        self.backup_cobbler_url_ = setting.COBBLER_INSTALLER_URL
        self.backup_chef_url_ = setting.CHEF_INSTALLER_URL
        self.backup_config_dir_ = setting.CONFIG_DIR
        self.backup_global_config_filename_ = setting.GLOBAL_CONFIG_FILENAME
        self.backup_config_file_format_ = setting.CONFIG_FILE_FORMAT
        setting.OS_INSTALLER = 'cobbler'
        setting.PACKAGE_INSTALLER = 'chef'
        setting.COBBLER_INSTALLER_URL = 'http://localhost/cobbler_api'
        setting.CHEF_INSTALLER_URL = 'https://localhost/'
        setting.CONFIG_DIR = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'data')
        setting.GLOBAL_CONFIG_FILENAME = 'global_config'
        setting.CONFIG_FILE_FORMAT = 'python'

    def _unmock_setting(self):
        setting.OS_INSTALLER = self.backup_os_installer_
        setting.PACKAGE_INSTALLER = self.backup_package_installer_
        setting.COBBLER_INSTALLER_URL = self.backup_cobbler_url_
        setting.CHEF_INSTALLER_URL = self.backup_chef_url_
        setting.CONFIG_DIR = self.backup_config_dir_
        setting.GLOBAL_CONFIG_FILENAME = self.backup_global_config_filename_
        self.backup_config_file_format_ = setting.CONFIG_FILE_FORMAT

    def setUp(self):
        """test setup."""
        super(TestEndToEnd, self).setUp()
        self._mock_setting()
        logsetting.init()
        database.create_db()
        self._mock_lock()
        self.rmtree_backup_ = shutil.rmtree
        shutil.rmtree = mock.Mock()
        self.system_backup_ = os.system
        os.system = mock.Mock()
        self.os_installer_mock_ = {}
        self.os_installer_mock_['cobbler'] = self._mock_cobbler
        self.os_installer_unmock_ = {}
        self.os_installer_unmock_['cobbler'] = self._unmock_cobbler
        self.package_installer_mock_ = {}
        self.package_installer_mock_['chef'] = self._mock_chef
        self.package_installer_unmock_ = {}
        self.package_installer_unmock_['chef'] = self._unmock_chef
        self.os_installer_checker_ = {}
        self.os_installer_checker_['cobbler'] = self._check_cobbler
        self.package_installer_checker_ = {}
        self.package_installer_checker_['chef'] = self._check_chef

    def tearDown(self):
        """test teardown."""
        database.drop_db()
        self._unmock_lock()
        shutil.rmtree = self.rmtree_backup_
        os.system = self.system_backup_
        self._unmock_setting()
        super(TestEndToEnd, self).tearDown()

    def test_1(self):
        """test one cluster one host."""
        self._test('test1')

    def test_2(self):
        """test one cluster multi hosts."""
        self._test('test2')

    def test_3(self):
        """test multi clusters multi hosts."""
        self._test('test3')

    def test_4(self):
        """test deploy unexist roles."""
        self._test('test4')


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
