# Copyright 2014 Openstack Foundation
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

"""Module to provide ConfigProvider that reads config from db.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import logging
import os.path

from compass.config_management.providers import config_provider
from compass.config_management.utils import config_filter
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
from compass.db.model import SwitchConfig
from compass.utils import setting_wrapper as setting


CLUSTER_ALLOWS = ['/security', '/networking', '/partition']
CLUSTER_DENIES = []
HOST_ALLOWS = ['/roles', '/networking/interfaces/*/ip']
HOST_DENIES = []


class DBProvider(config_provider.ConfigProvider):
    """config provider which reads config from db.

    .. note::
       All method of this class should be called inside database
       session scope.
    """
    NAME = 'db'
    CLUSTER_FILTER = config_filter.ConfigFilter(
        CLUSTER_ALLOWS, CLUSTER_DENIES)
    HOST_FILTER = config_filter.ConfigFilter(
        HOST_ALLOWS, HOST_DENIES)

    def __init__(self):
        pass

    def get_cluster_config(self, clusterid):
        """Get cluster config from db."""
        session = database.current_session()
        cluster = session.query(Cluster).filter_by(id=clusterid).first()
        if cluster:
            return cluster.config
        else:
            return {}

    def get_host_config(self, hostid):
        """Get host config from db."""
        session = database.current_session()
        host = session.query(ClusterHost).filter_by(id=hostid).first()
        if host:
            return host.config
        else:
            return {}

    def update_host_config(self, hostid, config):
        """Update host config to db."""
        session = database.current_session()
        host = session.query(ClusterHost).filter_by(id=hostid).first()
        if not host:
            return

        filtered_config = self.HOST_FILTER.filter(config)
        host.config = filtered_config

    def update_adapters(self, adapters, roles_per_target_system):
        """Update adapter config to db."""
        session = database.current_session()
        session.query(Adapter).delete()
        session.query(Role).delete()
        for adapter in adapters:
            session.add(Adapter(**adapter))

        for _, roles in roles_per_target_system.items():
            for role in roles:
                session.add(Role(**role))

    def update_switch_filters(self, switch_filters):
        """update switch filters."""
        session = database.current_session()
        switch_filter_tuples = set([])
        session.query(SwitchConfig).delete(synchronize_session='fetch')
        for switch_filter in switch_filters:
            switch_filter_tuple = tuple(switch_filter.values())
            if switch_filter_tuple in switch_filter_tuples:
                logging.debug('ignore adding switch filter: %s',
                              switch_filter)
                continue
            else:
                logging.debug('add switch filter: %s', switch_filter)
                switch_filter_tuples.add(switch_filter_tuple)

            session.add(SwitchConfig(**switch_filter))

    def clean_host_config(self, hostid):
        """clean host config."""
        self.clean_host_installing_progress(hostid)
        session = database.current_session()
        session.query(ClusterHost).filter_by(
            id=hostid).delete(synchronize_session='fetch')
        session.query(HostState).filter_by(
            id=hostid).delete(synchronize_session='fetch')

    def reinstall_host(self, hostid):
        """reinstall host."""
        session = database.current_session()
        host = session.query(ClusterHost).filter_by(id=hostid).first()
        if not host:
            return

        log_dir = os.path.join(
            setting.INSTALLATION_LOGDIR,
            host.fullname,
            '')
        session.query(LogProgressingHistory).filter(
            LogProgressingHistory.pathname.startswith(
                log_dir)).delete(synchronize_session='fetch')
        if not host.state:
            host.state = HostState()

        host.mutable = False
        host.state.state = 'INSTALLING'
        host.state.progress = 0.0
        host.state.message = ''
        host.state.severity = 'INFO'

    def reinstall_cluster(self, clusterid):
        """reinstall cluster."""
        session = database.current_session()
        cluster = session.query(Cluster).filter_by(id=clusterid).first()
        if not cluster:
            return

        if not cluster.state:
            cluster.state = ClusterState()

        cluster.state.state = 'INSTALLING'
        cluster.mutable = False
        cluster.state.progress = 0.0
        cluster.state.message = ''
        cluster.state.severity = 'INFO'

    def clean_cluster_installing_progress(self, clusterid):
        """clean cluster installing progress."""
        session = database.current_session()
        cluster = session.query(Cluster).filter_by(id=clusterid).first()
        if not cluster:
            return

        if cluster.state and cluster.state.state != 'UNINITIALIZED':
            cluster.mutable = False
            cluster.state.state = 'INSTALLING'
            cluster.state.progress = 0.0
            cluster.state.message = ''
            cluster.state.severity = 'INFO'

    def clean_host_installing_progress(self, hostid):
        """clean host intalling progress."""
        session = database.current_session()
        host = session.query(ClusterHost).filter_by(id=hostid).first()
        if not host:
            return

        log_dir = os.path.join(
            setting.INSTALLATION_LOGDIR,
            host.fullname,
            '')
        session.query(LogProgressingHistory).filter(
            LogProgressingHistory.pathname.startswith(
                log_dir)).delete(synchronize_session='fetch')
        if host.state and host.state.state != 'UNINITIALIZED':
            host.mutable = False
            host.state.state = 'INSTALLING'
            host.state.progress = 0.0
            host.state.message = ''
            host.state.severity = 'INFO'

    def clean_cluster_config(self, clusterid):
        """clean cluster config."""
        session = database.current_session()
        session.query(Cluster).filter_by(
            id=clusterid).delete(synchronize_session='fetch')
        session.query(ClusterState).filter_by(
            id=clusterid).delete(synchronize_session='fetch')

    def get_cluster_hosts(self, clusterid):
        """get cluster hosts."""
        session = database.current_session()
        hosts = session.query(ClusterHost).filter_by(
            cluster_id=clusterid).all()
        return [host.id for host in hosts]

    def get_clusters(self):
        """get clusters."""
        session = database.current_session()
        clusters = session.query(Cluster).all()
        return [cluster.id for cluster in clusters]

    def get_switch_and_machines(self):
        """get switches and machines."""
        session = database.current_session()
        switches = session.query(Switch).all()
        switches_data = []
        switch_machines_data = {}
        for switch in switches:
            switches_data.append({
                'ip': switch.ip,
                'vendor_info': switch.vendor_info,
                'credential': switch.credential,
                'state': switch.state,
            })
            switch_machines_data[switch.ip] = []
            for machine in switch.machines:
                switch_machines_data[switch.ip].append({
                    'mac': machine.mac,
                    'port': machine.port,
                    'vlan': machine.vlan,
                })

        return switches_data, switch_machines_data

    def update_switch_and_machines(
        self, switches, switch_machines
    ):
        """update switches and machines."""
        session = database.current_session()
        session.query(Switch).delete(synchronize_session='fetch')
        session.query(Machine).delete(synchronize_session='fetch')
        for switch_data in switches:
            switch = Switch(**switch_data)
            logging.info('add switch %s', switch)
            session.add(switch)
            for machine_data in switch_machines.get(switch.ip, []):
                machine = Machine(**machine_data)
                logging.info('add machine %s under %s', machine, switch)
                machine.switch = switch
                session.add(machine)


config_provider.register_provider(DBProvider)
