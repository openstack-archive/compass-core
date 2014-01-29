import chef
import logging
import os
import os.path
import shutil
import unittest2
import xmlrpclib

from mock import Mock


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


setting.OS_INSTALLER = 'cobbler'
setting.COBBLER_INSTALLER_URL = 'http://localhost/cobbler_api'
setting.PACKAGE_INSTALLER = 'chef'
setting.CHEF_INSTALLER_URL = 'https://localhost/'
setting.CONFIG_DIR = '%s/data' % os.path.dirname(os.path.abspath(__file__))


import compass.config_management.installers
import compass.config_management.providers

from compass.actions import trigger_install
from compass.db import database
from compass.db.model import Switch, Machine, Cluster, ClusterHost, Adapter, Role
from compass.utils import flags
from compass.utils import logsetting


class TestEndToEnd(unittest2.TestCase):

    def _contains(self, origin_config, expected_config):
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

    def _mock_cobbler(self, host_configs):
        mock_server = Mock()
        xmlrpclib.Server = mock_server
        mock_server.return_value.login.return_value = '' 
        mock_server.return_value.sync = Mock()
        mock_server.return_value.find_profile = Mock(
            side_effect=lambda x: [x['name']])

        def _get_system_handle(sys_name, token):
            for i, config in enumerate(host_configs):
                if config['name'] ==  sys_name:
                    return i

            raise Exception('Not Found %s' % sys_name)

        mock_server.return_value.get_system_handle = Mock(
            side_effect=_get_system_handle)

        def _new_system(token):
            host_configs.append({'name': ''})
            return len(host_configs) - 1

        mock_server.return_value.new_system = Mock(
            side_effect=_new_system)

        def _remove_system(sys_name, token):
            for i, config in host_configs:
                if config['name'] == sys_name:
                    del host_configs[i]
                    return

            raise Exception('Not Found %s' % sys_name)

        mock_server.return_value.remove_system = Mock(
            side_effect=_remove_system)

        mock_server.return_value.save_system = Mock()

        def _modify_system(sys_id, key, value, token):
            host_configs[sys_id][key] = value

        mock_server.return_value.modify_system = Mock(
            side_effect=_modify_system)

    def _check_cobbler(self, host_configs, expected_host_configs):
        self.assertEqual(len(host_configs), len(expected_host_configs))
        for i in range(len(host_configs)):
            self.assertTrue(
                self._contains(host_configs[i], expected_host_configs[i]))

    def _mock_chef(self, configs):
        chef.autoconfigure = Mock()
        chef.DataBag = Mock()

        import collections
        class _mockDict(collections.Mapping):
            def __init__(in_self, bag, bag_item_name, api):
                in_self.bag_item_name_ = bag_item_name
                in_self.config_ = configs.get(bag_item_name, {})

            def __len__(in_self):
                return  len(in_self.config_)

            def __iter__(in_self):
                return iter(in_self.config_)

            def __getitem__(in_self, name):
                return in_self.config_[name]

            def __setitem__(in_self, name, value):
                in_self.config_[name] = value

            def delete(in_self):
                del configs[in_self.bag_item_name_]

            def save(in_self):
                configs[in_self.bag_item_name_] = in_self.config_

        chef.DataBagItem = Mock(side_effect=_mockDict)
        chef.Client = Mock()
        chef.Client.return_value.delete = Mock()
        chef.Node = Mock()
        chef.Node.return_value.delete = Mock()
        
    def _check_chef(self, configs, expected_configs):
        self.assertTrue(self._contains(configs, expected_configs))

    def _mock_os_installer(self, config_locals):
        self.os_installer_mock_[setting.OS_INSTALLER](
            **config_locals['%s_MOCK' % setting.OS_INSTALLER])

    def _mock_package_installer(self, config_locals):
        self.package_installer_mock_[setting.PACKAGE_INSTALLER](
            **config_locals['%s_MOCK' % setting.PACKAGE_INSTALLER])

    def _check_os_installer(self, config_locals):
        mock_kwargs = config_locals['%s_MOCK' % setting.OS_INSTALLER]
        expected_kwargs = config_locals['%s_EXPECTED' % setting.OS_INSTALLER]
        kwargs = {}
        kwargs.update(mock_kwargs)
        kwargs.update(expected_kwargs)
        self.os_installer_checker_[setting.OS_INSTALLER](**kwargs)

    def _check_package_installer(self, config_locals):
        mock_kwargs = config_locals['%s_MOCK' % setting.PACKAGE_INSTALLER]
        expected_kwargs = config_locals['%s_EXPECTED' % setting.PACKAGE_INSTALLER]
        kwargs = {}
        kwargs.update(mock_kwargs)
        kwargs.update(expected_kwargs)
        self.package_installer_checker_[setting.PACKAGE_INSTALLER](**kwargs)

    def _test(self, config_filename):
        full_path = '%s/data/%s' % (
            os.path.dirname(os.path.abspath(__file__)),
            config_filename)
        config_globals = {}
        config_locals = {}
        execfile(full_path, config_globals, config_locals)
        self._prepare_database(config_locals)
        self._mock_os_installer(config_locals)
        self._mock_package_installer(config_locals)
        with database.session() as session:
            clusters = session.query(Cluster).all()
            for cluster in clusters:
                clusterid = cluster.id
                hostids = [host.id for host in cluster.hosts]
                trigger_install.trigger_install(clusterid, hostids)

        self._check_os_installer(config_locals)
        self._check_package_installer(config_locals)

    def _prepare_database(self, config_locals):
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
            for switch_ip, machine_configs in config_locals['MACHINES_BY_SWITCH'].items():
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
            for cluster_name, host_configs in config_locals['HOSTS_BY_CLUSTER'].items():
                for host_config in host_configs:
                    mac = host_config['mac']
                    del host_config['mac']
                    host = ClusterHost(**host_config)
                    hosts['%s.%s' % (host_config['hostname'], cluster_name)] = host
                    host.machine = machines[mac]
                    host.cluster = clusters[cluster_name]
                    session.add(host)

    def setUp(self):
        database.create_db()
        shutil.rmtree = Mock()
        os.system = Mock()
        self.os_installer_mock_ = {}
        self.os_installer_mock_['cobbler'] = self._mock_cobbler
        self.package_installer_mock_ = {}
        self.package_installer_mock_['chef'] = self._mock_chef
        self.os_installer_checker_ = {}
        self.os_installer_checker_['cobbler'] = self._check_cobbler
        self.package_installer_checker_ = {}
        self.package_installer_checker_['chef'] = self._check_chef

    def tearDown(self):
        database.drop_db()

    def test_1(self):
        self._test('test1')

    def test_2(self):
        self._test('test2')

    def test_3(self):
        self._test('test3')


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
