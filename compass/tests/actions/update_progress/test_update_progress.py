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

"""integration test for action update_progress"""
import logging
import mock
import os
import os.path
import shutil
import unittest2
import uuid

from contextlib import contextmanager


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


setting.CONFIG_DIR = '%s/data' % os.path.dirname(os.path.abspath(__file__))


from compass.actions import update_progress
from compass.actions import util
from compass.db import database
from compass.db.model import Adapter
from compass.db.model import Cluster
from compass.db.model import ClusterHost
from compass.db.model import ClusterState
from compass.db.model import HostState
from compass.db.model import Machine
from compass.db.model import Role
from compass.db.model import Switch

from compass.log_analyzor import file_matcher

from compass.utils import flags
from compass.utils import logsetting


def sortCheckPoints(check_points):
    ret = []
    mapping = {}
    for check_point in check_points:
        cp_index = int(check_point[-1])
        ret.append(cp_index)
        mapping[cp_index] = check_point

    ret.sort()
    while True:
        if isinstance(ret[0], int):
            ret.append(mapping[ret[0]])
            ret.pop(0)
        else:
            break
    return ret


class TestEndToEnd(unittest2.TestCase):
    """Integration test classs."""

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

    def _test(self, config_file):
        full_path = '%s/data/%s' % (
            os.path.dirname(os.path.abspath(__file__)),
            config_file)
        config_file_path = '%s/%s' % (
            full_path, config_file)

        class _TmpLogMocker:
            """Mocks logs from a check point."""

            def __init__(in_self, source_path, check_point, tmp_logdir):
                in_self.source_path = source_path
                in_self.check_point = check_point
                in_self.__logdir__ = tmp_logdir

            def _merge_logs(in_self):
                dest = in_self.__logdir__
                source = os.path.join(
                    in_self.source_path, in_self.check_point)
                shutil.copytree(source, dest)

        config_globals = {}
        config_locals = {}
        execfile(config_file_path, config_globals, config_locals)
        self._prepare_database(config_locals)
        cluster_hosts = {}
        with database.session() as session:
            clusters = session.query(Cluster).all()
            for cluster in clusters:
                cluster_hosts[cluster.id] = [
                    host.id for host in cluster.hosts]

        mock_log_path = os.path.join(full_path, "anamon")
        check_points = os.listdir(mock_log_path)
        check_points = sortCheckPoints(check_points)
        for check_point in check_points:
            tmp_logdir = os.path.join('/tmp/mocklogs', str(uuid.uuid4()))
            log_mocker = _TmpLogMocker(mock_log_path, check_point, tmp_logdir)
            setting.INSTALLATION_LOGDIR = log_mocker.__logdir__
            logging.info('temp logging dir set to: %s',
                         setting.INSTALLATION_LOGDIR)
            log_mocker._merge_logs()
            reload(file_matcher)
            update_progress.update_progress(cluster_hosts)
            self._check_progress(config_locals, config_file, check_point)

    def _check_progress(self, mock_configs, test_type, check_point):
        with database.session() as session:
            host_states = session.query(HostState).all()
            cluster_states = session.query(ClusterState).all()
            expected = mock_configs['EXPECTED']

            for host_state in host_states:
                states = self._filter_query_result(
                    host_state, ("hostname", "state", "progress"))
                expected_host_states = expected[
                    test_type][check_point][
                        'host_states'][host_state.hostname]
                self.assertEqual(expected_host_states, states)

            for cluster_state in cluster_states:
                states = self._filter_query_result(
                    cluster_state, ("clustername", "state", "progress"))
                expected_cluster_states = expected[
                    test_type][check_point][
                        'cluster_states'][cluster_state.clustername]
                self.assertEqual(expected_cluster_states, states)

    def _filter_query_result(self, model, keywords):
        filtered_dict = {}
        for keyword in keywords:
            pair = {keyword: eval("model.%s" % keyword)}
            filtered_dict.update(pair)
        return filtered_dict

    def _prepare_database(self, config_locals):
        """Prepare database."""
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
                cluster.state = ClusterState(
                    state="INSTALLING", progress=0.0, message='')
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
                    host.state = HostState(
                        state="INSTALLING", progress=0.0, message='')
                    session.add(host)

    def setUp(self):
        super(TestEndToEnd, self).setUp()
        logsetting.init()
        database.create_db()
        self._mock_lock()
        shutil.rmtree = mock.Mock()
        os.system = mock.Mock()
        self.progress_checker_ = {}

    def tearDown(self):
        database.drop_db()
        self._unmock_lock()
        shutil.rmtree('/tmp/mocklogs/')
        super(TestEndToEnd, self).tearDown()

    def test_1(self):
        self._test('test1')

    def test_2(self):
        self._test('test2')

if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
