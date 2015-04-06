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


import logging
import mock
import os
import sys
import unittest2
import uuid

from contextlib import contextmanager


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting


reload(setting)


from compass.actions import update_progress
from compass.actions import util
from compass.db.api import adapter as adapter_api
from compass.db.api import adapter_holder as adapter
from compass.db.api import cluster
from compass.db.api import database
from compass.db.api import host
from compass.db.api import machine
from compass.db.api import metadata as metadata_api
from compass.db.api import metadata_holder as metadata
from compass.db.api import network
from compass.db.api import switch
from compass.db.api import user as user_api
from compass.db import exception

from compass.log_analyzor.adapter_matcher import AdapterItemMatcher
from compass.log_analyzor.adapter_matcher import OSMatcher
from compass.log_analyzor.adapter_matcher import PackageMatcher
from compass.log_analyzor import file_matcher
from compass.log_analyzor.file_matcher import FileMatcher
from compass.log_analyzor.file_matcher import FileReaderFactory
from compass.log_analyzor.line_matcher import IncrementalProgress
from compass.log_analyzor.line_matcher import LineMatcher
from compass.log_analyzor import progress_calculator

from compass.utils import flags
from compass.utils import logsetting

ADAPTER_NAME = 'openstack_icehouse'
OS_NAME = 'CentOS-6.5-x86_64'
SWITCH_IP = '172.29.8.40'
MACHINE_MAC = '00:0c:29:bf:eb:1d'
SUBNET = '10.145.88.0/23'
HOST_IP = '10.145.88.0'


class TestProgressCalculator(unittest2.TestCase):
    """Test end to end."""

    def _prepare_database(self):
        adapter.load_adapters()
        metadata.load_metadatas()

        self.user_object = (
            user_api.get_user_object(
                setting.COMPASS_ADMIN_EMAIL
            )
        )
        self.adapter_id = None
        self.os_id = None
        self.flavor_id = None
        self.cluster_id = None

        # get adapter information
        list_adapters = adapter.list_adapters(user=self.user_object)
        for adptr in list_adapters:
            self.adapter_id = None
            if adptr['name'] != ADAPTER_NAME:
                continue
            self.adapter_id = adptr['id']
            self.os_id = None
            for supported_os in adptr['supported_oses']:
                if supported_os['name'] == OS_NAME:
                    self.os_id = supported_os['os_id']
                    break
            if not self.os_id:
                continue
            if (
                'package_installer' in adptr.keys() and
                adptr['flavors'] != [] and
                adptr['distributed_system_name'] == 'openstack'
            ):
                self.flavor_id = None
                for flavor in adptr['flavors']:
                    if flavor['name'] == 'allinone':
                        self.flavor_id = flavor['id']
                        break
                if not self.flavor_id:
                    continue
            else:
                continue
            if self.adapter_id and self.os_id and self.flavor_id:
                break

        if not self.adapter_id:
            raise Exception('adapter id not found')
        if not self.os_id:
            raise Exception('os id not found')
        if not self.flavor_id:
            raise Exception('flavor id not found')

        #add cluster
        cluster.add_cluster(
            adapter_id=self.adapter_id,
            os_id=self.os_id,
            flavor_id=self.flavor_id,
            name='test_cluster',
            user=self.user_object,
        )
        list_clusters = cluster.list_clusters(user=self.user_object)
        for list_cluster in list_clusters:
            if list_cluster['name'] == 'test_cluster':
                self.cluster_id = list_cluster['id']
                break
        for list_cluster in list_clusters:
            self.cluster_id = list_cluster['id']

        #add switch
        switch.add_switch(
            ip=SWITCH_IP,
            user=self.user_object,
        )
        list_switches = switch.list_switches(user=self.user_object)
        for list_switch in list_switches:
            self.switch_id = list_switch['id']
        switch.add_switch_machine(
            self.switch_id,
            user=self.user_object,
            mac=MACHINE_MAC,
            port='1'
        )

        #get machine information
        list_machines = machine.list_machines(user=self.user_object)
        for list_machine in list_machines:
            self.machine_id = list_machine['id']

        #add cluster host
        cluster.add_cluster_host(
            self.cluster_id,
            user=self.user_object,
            machine_id=self.machine_id,
            name='test_clusterhost'
        )
        list_clusterhosts = cluster.list_clusterhosts(user=self.user_object)
        for list_clusterhost in list_clusterhosts:
            self.host_id = list_clusterhost['host_id']
            self.clusterhost_id = list_clusterhost['clusterhost_id']

        #add subnet
        network.add_subnet(
            subnet=SUBNET,
            user=self.user_object,
        )
        list_subnets = network.list_subnets(
            user=self.user_object
        )
        for list_subnet in list_subnets:
            self.subnet_id = list_subnet['id']

        #add host network
        host.add_host_network(
            self.host_id,
            user=self.user_object,
            interface='eth0',
            ip=HOST_IP,
            subnet_id=self.subnet_id,
            is_mgmt=True
        )

        #get clusterhost
        list_clusterhosts = cluster.list_clusterhosts(
            user=self.user_object
        )
        for list_clusterhost in list_clusterhosts:
            self.clusterhost_id = list_clusterhost['id']

        #update host state
        self.list_hosts = host.list_hosts(user=self.user_object)
        for list_host in self.list_hosts:
            self.host_id = list_host['id']
        self.host_state = host.update_host_state(
            self.host_id,
            user=self.user_object,
            state='INSTALLING'
        )

        #update cluster state
        cluster.update_cluster_state(
            self.cluster_id,
            user=self.user_object,
            state='INSTALLING'
        )

        #update clusterhost state
        cluster.update_clusterhost_state(
            self.clusterhost_id,
            user=self.user_object,
            state='INSTALLING'
        )

    def _file_generator(self, check_point):
        file_line_mapping = {
            'sys.log': {
                1: 'NOTICE kernel: Phoenix BIOS detected:'
                'BIOS may corrupt low RAM, working around it.'
            },
            'anaconda.log': {
                1: 'setting up kickstart',
                2: 'starting STEP_STAGE2',
                3: 'Running anaconda scripti /usr/bin/anaconda',
                4: 'Running kickstart %%pre script(s)',
                5: 'All kickstart %%pre script(s) have been run',
                6: 'moving (1) to step enablefilesystems',
                7: 'leaving (1) step enablefilesystems',
                8: 'moving (1) to step reposetup',
                9: 'leaving (1) step reposetup',
                10: 'moving (1) to step postselection',
                11: 'leaving (1) step postselection',
                12: 'moving (1) to step installpackages',
                13: 'leaving (1) step installpackages',
                14: 'moving (1) to step instbootloader',
                15: 'leaving (1) step instbootloader',
            },
            'install.log': {
                1: 'Installing libgcc-4.4.7-4.el6.x86_64',
                2: 'FINISHED INSTALLING PACKAGES'
            },
            'chef-client.log': {
                1: 'Processing service[quantum-server] action',
                2: 'Processing directory[/var/cache/quantum] action',
                3: 'Chef Run complete in 1449.433415826 seconds'
            }
        }

        self.check_points = {
            'check_point_1': {
                'percentage': 0.095,
                'position': {
                    'file': 'anaconda.log',
                    'line': 'setting up kickstart'
                }
            },
            'check_point_2': {
                'percentage': 0.280594,
                'position': {
                    'file': 'install.log',
                    'line': 'Installing libgcc-4.4.7-4.el6.x86_64'
                }
            },
            'check_point_3': {
                'percentage': 0.41,
                'position': {
                    'file': 'anaconda.log',
                    'line': 'leaving (1) step installpackages'
                }
            },
            'check_point_4': {
                'percentage': 0.55405,
                'position': {
                    'file': 'chef-client.log',
                    'line': 'Processing directory[/var/cache/quantum] action'
                }
            },
            'check_point_5': {
                'percentage': 1.0,
                'position': {
                    'file': 'chef-client.log',
                    'line': 'Chef Run complete in 1449.433415826 seconds'
                }
            }
        }
        file_order = {
            1: 'sys.log',
            2: 'anaconda.log',
            3: 'install.log',
            4: 'chef-client.log'
        }

        class _AddToFile:
            def __init__(in_self, line, file, check_point):
                in_self.line = line
                in_self.file = file
                in_self.check_point = check_point

            def _get_content(in_self):
                files_to_use = []
                result = {}
                if in_self.check_point == 'check_point_2':
                    file_lines_sys = []
                    file_lines_anaconda = []
                    file_lines_install = []
                    for index, log_line in (
                        file_line_mapping['sys.log'].items()
                    ):
                        file_lines_sys.append(log_line)
                    result['sys.log'] = file_lines_sys
                    for index, log_line in (
                        file_line_mapping['anaconda.log'].items()
                    ):
                        file_lines_anaconda.append(log_line)
                        if index == 12:
                            break
                    result['anaconda.log'] = file_lines_anaconda
                    for index, log_line in (
                        file_line_mapping['install.log'].items()
                    ):
                        file_lines_install.append(log_line)
                        if index == 1:
                            break
                    result['install.log'] = file_lines_install
                    return result

                elif in_self.check_point == 'check_point_3':
                    file_lines_sys = []
                    file_lines_anaconda = []
                    file_lines_install = []
                    for index, log_line in (
                        file_line_mapping['sys.log'].items()
                    ):
                        file_lines_sys.append(log_line)
                    result['sys.log'] = file_lines_sys
                    for index, log_line in (
                        file_line_mapping['anaconda.log'].items()
                    ):
                        file_lines_anaconda.append(log_line)
                        if index == 13:
                            break
                    result['anaconda.log'] = file_lines_anaconda
                    for index, log_line in (
                        file_line_mapping['install.log'].items()
                    ):
                        file_lines_install.append(log_line)
                    result['install.log'] = file_lines_install
                    return result

                else:
                    for index, value in file_order.items():
                        files_to_use.append(value)
                        if value == in_self.file:
                            break
                    for file_to_use in files_to_use:
                        file_lines = []
                        for index, log_line in (
                            file_line_mapping[file_to_use].items()
                        ):
                            file_lines.append(log_line)
                        result[file_to_use] = file_lines
                    current_file_lines = []
                    for index, log_line in (
                        file_line_mapping[in_self.file].items()
                    ):
                        current_file_lines.append(log_line)
                        if log_line == in_self.line:
                            break
                    result[in_self.file] = current_file_lines
                    return result

        tmp_logdir = os.path.join(self.tmp_logpath, 'test_clusterhost')
        tmp_logdir_chef = os.path.join(
            self.tmp_logpath,
            'test_clusterhost.test_cluster'
        )
        if not os.path.exists(tmp_logdir):
            os.makedirs(tmp_logdir)
        if not os.path.exists(tmp_logdir_chef):
            os.makedirs(tmp_logdir_chef)
        line = self.check_points[check_point]['position']['line']
        file = self.check_points[check_point]['position']['file']
        add_to_file = _AddToFile(line, file, check_point)
        raw_files = add_to_file._get_content()
        for filename, raw_file in raw_files.items():
            if filename == 'chef-client.log':
                target_log = os.path.join(tmp_logdir_chef, filename)
            else:
                target_log = os.path.join(tmp_logdir, filename)
            with open(target_log, 'w') as f:
                for single_line in raw_file:
                    f.write(single_line + '\n')
            f.close

    def _mock_lock(self):
        @contextmanager
        def _lock(lock_name, blocking=True, timeout=10):
            try:
                yield lock_name
            finally:
                pass

        self.lock_backup_ = util.lock
        util.lock = mock.Mock(side_effect=_lock)

    def _unmock_lock(self):
        util.lock = self.lock_backup_

    def setUp(self):
        super(TestProgressCalculator, self).setUp()
        parent_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "../../../.."
        ))
        setting.CONFIG_DIR = os.path.join(parent_path, 'conf')
        logsetting.init()
        self._mock_lock()
        database.init('sqlite://')
        database.create_db()
        self.backup_cobbler_installation_dir = (
            setting.COBBLER_INSTALLATION_LOGDIR
        )
        self.backup_chef_installation_dir = setting.CHEF_INSTALLATION_LOGDIR
        self.backup_installation_dir = setting.INSTALLATION_LOGDIR
        self.tmp_logpath = os.path.join('/tmp/mocklogs', str(uuid.uuid4()))
        setting.COBBLER_INSTALLATION_LOGDIR = self.tmp_logpath
        setting.CHEF_INSTALLATION_LOGDIR = self.tmp_logpath
        setting.INSTALLATION_LOGDIR = {
            'CobblerInstaller': setting.COBBLER_INSTALLATION_LOGDIR,
            'ChefInstaller': setting.CHEF_INSTALLATION_LOGDIR
        }
        reload(progress_calculator)

    def tearDown(self):
        super(TestProgressCalculator, self).tearDown()
        self._unmock_lock()
        setting.COBBLER_INSTALLATION_LOGDIR = (
            self.backup_cobbler_installation_dir
        )
        setting.CHEF_INSTALLATION_LOGDIR = self.backup_chef_installation_dir
        setting.INSTALLATION_LOGDIR = self.backup_installation_dir
        database.drop_db()

    def test_update_progress_checkpoint1(self):
        self._prepare_database()
        self._file_generator('check_point_1')
        update_progress.update_progress()
        clusterhost_state = cluster.get_clusterhost_state(
            self.clusterhost_id,
            user=self.user_object,
        )
        self.assertAlmostEqual(
            clusterhost_state['percentage'],
            self.check_points['check_point_1']['percentage']
        )

    def test_update_progress_checkpoint2(self):
        self._prepare_database()
        self._file_generator('check_point_2')
        update_progress.update_progress()
        clusterhost_state = cluster.get_clusterhost_state(
            self.clusterhost_id,
            user=self.user_object,
        )
        self.assertAlmostEqual(
            clusterhost_state['percentage'],
            self.check_points['check_point_2']['percentage']
        )

    def test_update_progress_checkpoint3(self):
        self._prepare_database()
        self._file_generator('check_point_3')
        update_progress.update_progress()
        clusterhost_state = cluster.get_clusterhost_state(
            self.clusterhost_id,
            user=self.user_object,
        )
        self.assertAlmostEqual(
            clusterhost_state['percentage'],
            self.check_points['check_point_3']['percentage']
        )

    def test_update_progress_checkpoint4(self):
        self._prepare_database()
        self._file_generator('check_point_4')
        update_progress.update_progress()
        clusterhost_state = cluster.get_clusterhost_state(
            self.clusterhost_id,
            user=self.user_object,
        )
        self.assertAlmostEqual(
            clusterhost_state['percentage'],
            self.check_points['check_point_4']['percentage']
        )

    def test_update_progress_checkpoint5(self):
        self._prepare_database()
        self._file_generator('check_point_5')
        update_progress.update_progress()
        clusterhost_state = cluster.get_clusterhost_state(
            self.clusterhost_id,
            user=self.user_object,
        )
        self.assertEqual(
            clusterhost_state['percentage'],
            self.check_points['check_point_5']['percentage']
        )


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
