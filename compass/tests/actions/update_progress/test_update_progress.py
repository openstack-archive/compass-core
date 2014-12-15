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
import os
import sys
import unittest2
import uuid


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting


reload(setting)
tmp_logpath = os.path.join('/tmp/mocklogs', str(uuid.uuid4()))
for k in setting.INSTALLATION_LOGDIR.keys():
    setting.INSTALLATION_LOGDIR[k] = tmp_logpath

from compass.actions import update_progress
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
from compass.utils import util

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
        list_adapters = adapter.list_adapters(self.user_object)
        for adptr in list_adapters:
            if ('package_installer' in adptr.keys() and
                adptr['flavors'] != [] and
                    adptr['distributed_system_name'] == 'openstack'):
                self.adapter_id = adptr['id']
                for flavor in adptr['flavors']:
                    if flavor['name'] == 'allinone':
                        self.flavor_id = flavor['id']
                        break
            for supported_os in adptr['supported_oses']:
                if supported_os['name'] == OS_NAME:
                    self.os_id = supported_os['os_id']
                    break

        #add cluster
        cluster.add_cluster(
            self.user_object,
            adapter_id=self.adapter_id,
            os_id=self.os_id,
            flavor_id=self.flavor_id,
            name='test_cluster'
        )
        list_clusters = cluster.list_clusters(self.user_object)
        for list_cluster in list_clusters:
            if list_cluster['name'] == 'test_cluster':
                self.cluster_id = list_cluster['id']
                break
        for list_cluster in list_clusters:
            self.cluster_id = list_cluster['id']

        #add switch
        switch.add_switch(
            self.user_object,
            ip=SWITCH_IP
        )
        list_switches = switch.list_switches(self.user_object)
        for list_switch in list_switches:
            self.switch_id = list_switch['id']
        switch.add_switch_machine(
            self.user_object,
            self.switch_id,
            mac=MACHINE_MAC,
            port='1'
        )

        #get machine information
        list_machines = machine.list_machines(self.user_object)
        for list_machine in list_machines:
            self.machine_id = list_machine['id']

        #add cluster host
        cluster.add_cluster_host(
            self.user_object,
            self.cluster_id,
            machine_id=self.machine_id,
            name='test_clusterhost'
        )
        list_clusterhosts = cluster.list_clusterhosts(self.user_object)
        for list_clusterhost in list_clusterhosts:
            self.host_id = list_clusterhost['host_id']
            self.clusterhost_id = list_clusterhost['clusterhost_id']

        #add subnet
        network.add_subnet(
            self.user_object,
            subnet=SUBNET
        )
        list_subnets = network.list_subnets(
            self.user_object
        )
        for list_subnet in list_subnets:
            self.subnet_id = list_subnet['id']

        #add host network
        host.add_host_network(
            self.user_object,
            self.host_id,
            interface='eth0',
            ip=HOST_IP,
            subnet_id=self.subnet_id,
            is_mgmt=True
        )

        #get clusterhost
        list_clusterhosts = cluster.list_clusterhosts(
            self.user_object
        )
        for list_clusterhost in list_clusterhosts:
            self.clusterhost_id = list_clusterhost['id']

        #update host state
        self.list_hosts = host.list_hosts(self.user_object)
        for list_host in self.list_hosts:
            self.host_id = list_host['id']
        self.host_state = host.update_host_state(
            self.user_object,
            self.host_id,
            state='INSTALLING'
        )

        #update cluster state
        cluster.update_cluster_state(
            self.user_object,
            self.cluster_id,
            state='INSTALLING'
        )

        #update clusterhost state
        cluster.update_clusterhost_state(
            self.user_object,
            self.clusterhost_id,
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

        tmp_logdir = os.path.join(tmp_logpath, 'test_clusterhost')
        tmp_logdir_chef = os.path.join(
            tmp_logpath,
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

    def setUp(self):
        super(TestProgressCalculator, self).setUp()
        logsetting.init()
        database.init('sqlite://')
        database.create_db()

    def tearDown(self):
        super(TestProgressCalculator, self).tearDown()
        database.drop_db()

    def test_update_progress_checkpoint1(self):
        self._prepare_database()
        self._file_generator('check_point_1')
        update_progress.update_progress()
        clusterhost_state = cluster.get_clusterhost_state(
            self.user_object,
            self.clusterhost_id
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
            self.user_object,
            self.clusterhost_id
        )
        self.assertAlmostEqual(
            clusterhost_state['percentage'],
            self.check_points['check_point_2']['percentage'])

    def test_update_progress_checkpoint3(self):
        self._prepare_database()
        self._file_generator('check_point_3')
        update_progress.update_progress()
        clusterhost_state = cluster.get_clusterhost_state(
            self.user_object,
            self.clusterhost_id
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
            self.user_object,
            self.clusterhost_id
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
            self.user_object,
            self.clusterhost_id
        )
        self.assertEqual(
            clusterhost_state['percentage'],
            self.check_points['check_point_5']['percentage']
        )


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
