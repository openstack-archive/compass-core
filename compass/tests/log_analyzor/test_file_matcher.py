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

"""test file matcher module"""

import datetime
import mock
import os
import unittest2

os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from compass.db import database
from compass.db.model import Adapter
from compass.db.model import Cluster
from compass.db.model import ClusterHost
from compass.db.model import ClusterState
from compass.db.model import HostState
from compass.db.model import LogProgressingHistory
from compass.db.model import Machine
from compass.db.model import Role
from compass.db.model import Switch

from compass.log_analyzor import file_matcher

from compass.log_analyzor.line_matcher import IncrementalProgress
from compass.log_analyzor.line_matcher import LineMatcher
from compass.log_analyzor.line_matcher import Progress

from compass.utils import flags
from compass.utils import logsetting


def prepare_database(config):
        with database.session() as session:
            adapters = {}
            for adapter_config in config['ADAPTERS']:
                adapter = Adapter(**adapter_config)
                session.add(adapter)
                adapters[adapter_config['name']] = adapter

            roles = {}
            for role_config in config['ROLES']:
                role = Role(**role_config)
                session.add(role)
                roles[role_config['name']] = role

            switches = {}
            for switch_config in config['SWITCHES']:
                switch = Switch(**switch_config)
                session.add(switch)
                switches[switch_config['ip']] = switch

            machines = {}
            for switch_ip, machine_configs in (
                config['MACHINES_BY_SWITCH'].items()
            ):
                for machine_config in machine_configs:
                    machine = Machine(**machine_config)
                    machines[machine_config['mac']] = machine
                    machine.switch = switches[switch_ip]
                    session.add(machine)

            clusters = {}
            for cluster_config in config['CLUSTERS']:
                adapter_name = cluster_config['adapter']
                del cluster_config['adapter']
                cluster = Cluster(**cluster_config)
                clusters[cluster_config['name']] = cluster
                cluster.adapter = adapters[adapter_name]
                cluster.state = ClusterState(
                    state="INSTALLING", progress=0.0, message='')
                session.add(cluster)

            hosts = {}
            for cluster_name, host_configs in (
                config['HOSTS_BY_CLUSTER'].items()
            ):
                for host_config in host_configs:
                    mac = host_config['mac']
                    del host_config['mac']
                    host = ClusterHost(**host_config)
                    hosts['%s.%s' % (
                        host_config['hostname'], cluster_name)] = host
                    host.machine = machines[mac]
                    host.cluster = clusters[cluster_name]
                    host.state = HostState(
                        state="INSTALLING", progress=0.0, message='')
                    session.add(host)


class TestFilterFileExist(unittest2.TestCase):
    def setUp(self):
        super(TestFilterFileExist, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestFilterFileExist, self).tearDown()

    def test_filter(self):
        pathname = 'NeverExists'
        filter = file_matcher.FilterFileExist()
        res = filter.filter(pathname)
        self.assertFalse(res)


class TestCompositeFileFilter(unittest2.TestCase):
    def setUp(self):
        super(TestCompositeFileFilter, self).setUp()
        self.file_path = os.path.dirname(os.path.abspath(__file__))
        logsetting.init()

    def tearDown(self):
        super(TestCompositeFileFilter, self).tearDown()

    def test_filter(self):
        filter_list = [
            file_matcher.FilterFileExist(),
            file_matcher.FilterFileExist(),
        ]
        exists = self.file_path + '/test_file_matcher.py'
        non_exists = '/nonexists'
        composite_filter = file_matcher.CompositeFileFilter(
            filter_list)
        self.assertTrue(
            composite_filter.filter(exists))
        self.assertFalse(
            composite_filter.filter(non_exists))

    def test_append_filter(self):
        filter_list = [
            file_matcher.FilterFileExist(),
            file_matcher.FilterFileExist(),
        ]
        composite_filter = file_matcher.CompositeFileFilter(
            filter_list)
        new_filter = file_matcher.FilterFileExist()
        composite_filter.append_filter(new_filter)
        self.assertEqual(3, len(composite_filter.filters_))


class TestFileReader(unittest2.TestCase):
    def setUp(self):
        super(TestFileReader, self).setUp()
        logsetting.init()
        database.create_db()
        self.config_file = '%s/data/config' % (
            os.path.dirname(os.path.abspath(__file__)))

    def tearDown(self):
        super(TestFileReader, self).tearDown()
        database.drop_db()

    def test_get_empty_history(self):
        config_locals = {}
        config_globals = {}
        execfile(self.config_file, config_globals, config_locals)
        prepare_database(config_locals)
        expected = {
            'matcher_name': 'start',
            'progress': 0.0,
            'message': '',
            'severity': None
        }
        res = {}
        reader = file_matcher.FileReader('dummy')
        history = reader.get_history()
        res.update(
            {
                'matcher_name': history[0],
                'progress': history[1].progress,
                'message': history[1].message,
                'severity': history[1].severity
            })
        self.assertEqual(expected, res)

    def test_get_existing_history(self):
        config_locals = {}
        config_globals = {}
        execfile(self.config_file, config_globals, config_locals)
        prepare_database(config_locals)
        with database.session() as session:
            history = LogProgressingHistory(
                line_matcher_name='start',
                progress=0.5,
                message='dummy',
                severity='INFO',
                position=0,
                partial_line='',
                pathname='dummy')
            session.add(history)

        expected = {
            'matcher_name': 'start',
            'progress': 0.5,
            'message': 'dummy',
            'severity': 'INFO'
        }
        res = {}
        reader = file_matcher.FileReader('dummy')
        history = reader.get_history()
        res.update({
            'matcher_name': history[0],
            'progress': history[1].progress,
            'message': history[1].message,
            'severity': history[1].severity
        })
        self.assertEqual(expected, res)

    def test_update_history_from_none(self):
        config_locals = {}
        config_globals = {}
        execfile(self.config_file, config_globals, config_locals)
        prepare_database(config_locals)

        expected = {
            'progress': 0.5,
            'line_matcher_name': 'start'
        }
        reader = file_matcher.FileReader('dummy')
        reader.update_history(
            expected['line_matcher_name'],
            Progress(
                progress=expected['progress'],
                message='',
                severity='INFO'))
        res = {}
        with database.session() as session:
            history = session.query(
                LogProgressingHistory).first()
            res.update({
                'line_matcher_name': history.line_matcher_name,
                'progress': history.progress
            })
        self.assertEqual(expected, res)

    def test_update_history_from_existing(self):
        config_locals = {}
        config_globals = {}
        execfile(self.config_file, config_globals, config_locals)
        prepare_database(config_locals)

        with database.session() as session:
            history = LogProgressingHistory(
                line_matcher_name='start',
                progress=0.5,
                message='dummy',
                severity='INFO',
                position=0,
                partial_line='',
                pathname='dummy')
            session.add(history)

        expected = {
            'progress': 0.8,
            'line_matcher_name': 'start'
        }
        reader = file_matcher.FileReader('dummy')
        reader.position_ = 1
        reader.update_history(
            expected['line_matcher_name'],
            Progress(
                progress=expected['progress'],
                message='',
                severity='INFO'))
        res = {}
        with database.session() as session:
            history = session.query(
                LogProgressingHistory).first()
            res.update({
                'line_matcher_name': history.line_matcher_name,
                'progress': history.progress
            })
        self.assertEqual(expected, res)

    def test_update_history_failure(self):
        config_locals = {}
        config_globals = {}
        execfile(self.config_file, config_globals, config_locals)
        prepare_database(config_locals)

        with database.session() as session:
            history = LogProgressingHistory(
                line_matcher_name='start',
                progress=0.5,
                message='dummy',
                severity='INFO',
                position=0,
                partial_line='',
                pathname='dummy')
            session.add(history)

        expected = {
            'progress': 0.8,
            'line_matcher_name': 'start'
        }
        reader = file_matcher.FileReader('dummy')
        reader.update_history(
            expected['line_matcher_name'],
            Progress(
                progress=expected['progress'],
                message='',
                severity='INFO'))
        res = {}
        with database.session() as session:
            history = session.query(
                LogProgressingHistory).first()
            res.update({
                'line_matcher_name': history.line_matcher_name,
                'progress': history.progress
            })
        self.assertNotEqual(expected, res)


class TestFileReaderFactory(unittest2.TestCase):
    def setUp(self):
        super(TestFileReaderFactory, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestFileReaderFactory, self).tearDown()

    def test_get_file_reader_None(self):
        reader_factory = file_matcher.FileReaderFactory(
            'dummy',
            file_matcher.get_file_filter())

        reader = reader_factory.get_file_reader('dummy', 'dummy')
        self.assertIsNone(reader)


class TestFileMatcher(unittest2.TestCase):
    def setUp(self):
        super(TestFileMatcher, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestFileMatcher, self).tearDown()

    def test_update_absolute_progress_range(self):
        matcher = file_matcher.FileMatcher(
            filename='sys.log',
            min_progress=0.0,
            max_progress=0.1,
            line_matchers={
                'start': LineMatcher(
                    pattern=r'NOTICE (?P<message>.*)',
                    progress=IncrementalProgress(.1, .9, .1),
                    message_template='%(message)s',
                    unmatch_nextline_next_matcher_name='start',
                    match_nextline_next_matcher_name='exit'
                ),
            }
        )
        matcher.update_absolute_progress_range(0.5, 1.0)
        expected = [0.5, 0.55]
        res = []
        res.append(matcher.absolute_min_progress_)
        res.append(matcher.absolute_max_progress_)
        self.assertEqual(expected, res)

    def test_update_total_progress_none(self):
        file_progress = Progress(
            message=None,
            progress=0.5,
            severity='info')

        total_progress = file_progress
        matcher = file_matcher.FileMatcher(
            filename='sys.log',
            min_progress=0.0,
            max_progress=0.1,
            line_matchers={
                'start': LineMatcher(
                    pattern=r'NOTICE (?P<message>.*)',
                    progress=IncrementalProgress(.1, .9, .1),
                    message_template='%(message)s',
                    unmatch_nextline_next_matcher_name='start',
                    match_nextline_next_matcher_name='exit'
                ),
            }
        )
        res = matcher.update_total_progress(file_progress, total_progress)
        self.assertIsNone(res)

    def test_update_total_progress(self):
        file_progress = Progress(
            message='dummy',
            progress=0.5,
            severity='info')

        total_progress = Progress(
            message='dummy',
            progress=0.4,
            severity='info')

        matcher = file_matcher.FileMatcher(
            filename='sys.log',
            min_progress=0.0,
            max_progress=0.1,
            line_matchers={
                'start': LineMatcher(
                    pattern=r'NOTICE (?P<message>.*)',
                    progress=IncrementalProgress(.1, .9, .1),
                    message_template='%(message)s',
                    unmatch_nextline_next_matcher_name='start',
                    match_nextline_next_matcher_name='exit'
                ),
            }
        )
        matcher.update_total_progress(file_progress, total_progress)
        self.assertEqual(
            0.5,
            total_progress.progress)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
