#!/usr/bin/env python
#
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
"""run fake flask server for test."""
import copy
import os
import simplejson as json
import sys


curr_dir = os.path.dirname(os.path.realpath(__file__))
compass_dir = os.path.dirname(os.path.dirname(os.path.dirname(curr_dir)))
sys.path.append(compass_dir)


from compass.api import app
from compass.db import database
from compass.db.model import Adapter
from compass.db.model import Cluster
from compass.db.model import ClusterHost
from compass.db.model import ClusterState
from compass.db.model import HostState
from compass.db.model import Machine
from compass.db.model import Role
from compass.db.model import Switch
from compass.db.model import SwitchConfig
from compass.utils import util


def setupDb():
    """setup database."""
    SECURITY_CONFIG = {
        "security": {
            "server_credentials": {
                "username": "root",
                "password": "root"},
            "service_credentials": {
                "username": "service",
                "password": "admin"},
            "console_credentials": {
                "username": "console",
                "password": "admin"}
        }
    }

    NET_CONFIG = {
        "networking": {
            "interfaces": {
                "management": {
                    "ip_start": "10.120.8.100",
                    "ip_end": "10.120.8.200",
                    "netmask": "255.255.255.0",
                    "gateway": "",
                    "nic": "eth0",
                    "promisc": 1
                },
                "tenant": {
                    "ip_start": "192.168.10.100",
                    "ip_end": "192.168.10.200",
                    "netmask": "255.255.255.0",
                    "gateway": "",
                    "nic": "eth1",
                    "promisc": 0
                },
                "public": {
                    "ip_start": "12.145.68.100",
                    "ip_end": "12.145.68.200",
                    "netmask": "255.255.255.0",
                    "gateway": "",
                    "nic": "eth2",
                    "promisc": 0
                },
                "storage": {
                    "ip_start": "172.29.8.100",
                    "ip_end": "172.29.8.200",
                    "netmask": "255.255.255.0",
                    "gateway": "",
                    "nic": "eth3",
                    "promisc": 0
                }
            },
            "global": {
                "nameservers": "8.8.8.8",
                "search_path": "ods.com",
                "gateway": "192.168.1.1",
                "proxy": "http://127.0.0.1:3128",
                "ntp_server": "127.0.0.1"
            }
        }
    }

    PAR_CONFIG = {
        "partition": "/home 20%;/tmp 10%;/var 30%;"
    }

    HOST_CONFIG = {
        "networking": {
            "interfaces": {
                "management": {
                    "ip": "%s"
                },
                "tenant": {
                    "ip": "%s"
                }
            }
        },
        "roles": ["base"]
    }

    print "Setting up DB ..."
    with database.session() as session:
            # populate switch_config
            switch_config = SwitchConfig(ip='192.168.1.10', filter_port='1')
            session.add(switch_config)

            # populate role table
            role = Role(name='compute', target_system='openstack')
            session.add(role)

            # Populate one adapter to DB
            adapter = Adapter(name='Centos_openstack', os='Centos',
                              target_system='openstack')
            session.add(adapter)

            #Populate switches info to DB
            switches = [Switch(ip="192.168.2.1",
                               credential={"version": "2c",
                                           "community": "public"},
                               vendor="huawei",
                               state="under_monitoring"),
                        Switch(ip="192.168.2.2",
                               credential={"version": "2c",
                                           "community": "public"},
                               vendor="huawei",
                               state="under_monitoring"),
                        Switch(ip="192.168.2.3",
                               credential={"version": "2c",
                                           "community": "public"},
                               vendor="huawei",
                               state="under_monitoring"),
                        Switch(ip="192.168.2.4",
                               credential={"version": "2c",
                                           "community": "public"},
                               vendor="huawei",
                               state="under_monitoring")]
            session.add_all(switches)

            # Populate machines info to DB
            machines = [
                Machine(mac='00:0c:27:88:0c:a1', port='1', vlan='1',
                        switch_id=1),
                Machine(mac='00:0c:27:88:0c:a2', port='2', vlan='1',
                        switch_id=1),
                Machine(mac='00:0c:27:88:0c:a3', port='3', vlan='1',
                        switch_id=1),
                Machine(mac='00:0c:27:88:0c:b1', port='1', vlan='1',
                        switch_id=2),
                Machine(mac='00:0c:27:88:0c:b2', port='2', vlan='1',
                        switch_id=2),
                Machine(mac='00:0c:27:88:0c:b3', port='3', vlan='1',
                        switch_id=2),
                Machine(mac='00:0c:27:88:0c:c1', port='1', vlan='1',
                        switch_id=3),
                Machine(mac='00:0c:27:88:0c:c2', port='2', vlan='1',
                        switch_id=3),
                Machine(mac='00:0c:27:88:0c:c3', port='3', vlan='1',
                        switch_id=3),
                Machine(mac='00:0c:27:88:0c:d1', port='1', vlan='1',
                        switch_id=4),
                Machine(mac='00:0c:27:88:0c:d2', port='2', vlan='1',
                        switch_id=4),
            ]

            session.add_all(machines)
            # Popluate clusters into DB
            """
            a. cluster #1: a new machine will be added to it.
            b. cluster #2: a failed machine needs to be re-deployed.
            c. cluster #3: a new cluster with 3 hosts will be deployed.
            """
            clusters_networking_config = [
                {"networking":
                    {"interfaces": {"management": {"ip_start": "10.120.1.100",
                                                   "ip_end": "10.120.1.200"},
                                    "tenant": {"ip_start": "192.168.1.100",
                                               "ip_end": "192.168.1.200"},
                                    "public": {"ip_start": "12.145.1.100",
                                               "ip_end": "12.145.1.200"},
                                    "storage": {"ip_start": "172.29.1.100",
                                                "ip_end": "172.29.1.200"}}}},
                {"networking":
                    {"interfaces": {"management": {"ip_start": "10.120.2.100",
                                                   "ip_end": "10.120.2.200"},
                                    "tenant": {"ip_start": "192.168.2.100",
                                               "ip_end": "192.168.2.200"},
                                    "public": {"ip_start": "12.145.2.100",
                                               "ip_end": "12.145.2.200"},
                                    "storage": {"ip_start": "172.29.2.100",
                                                "ip_end": "172.29.2.200"}}}}
            ]
            cluster_names = ['cluster_01', 'cluster_02']
            for name, networking_config in zip(cluster_names,
                                               clusters_networking_config):
                nconfig = copy.deepcopy(NET_CONFIG)
                util.merge_dict(nconfig, networking_config)
                c = Cluster(
                    name=name, adapter_id=1,
                    security_config=json.dumps(SECURITY_CONFIG['security']),
                    networking_config=json.dumps(nconfig['networking']),
                    partition_config=json.dumps(PAR_CONFIG['partition']))
                session.add(c)
            # Populate hosts to each cluster
            host_mips = ['10.120.1.100', '10.120.1.101', '10.120.1.102',
                         '10.120.2.100', '10.120.2.101', '10.120.2.102']
            host_tips = ['192.168.1.100', '192.168.1.101', '192.168.1.102',
                         '192.168.2.100', '192.168.2.101', '192.168.2.102']

            hosts_config = []
            for mip, tip in zip(host_mips, host_tips):
                config = copy.deepcopy(HOST_CONFIG)
                config['networking']['interfaces']['management']['ip'] = mip
                config['networking']['interfaces']['tenant']['ip'] = tip
                hosts_config.append(json.dumps(config))

            hosts = [
                ClusterHost(hostname='host_01', machine_id=1, cluster_id=1,
                            config_data=hosts_config[0]),
                ClusterHost(hostname='host_02', machine_id=2, cluster_id=1,
                            config_data=hosts_config[1]),
                ClusterHost(hostname='host_03', machine_id=3, cluster_id=1,
                            config_data=hosts_config[2]),
                ClusterHost(hostname='host_01', machine_id=4, cluster_id=2,
                            config_data=hosts_config[3]),
                ClusterHost(hostname='host_02', machine_id=5, cluster_id=2,
                            config_data=hosts_config[4]),
                ClusterHost(hostname='host_03', machine_id=6, cluster_id=2,
                            config_data=hosts_config[5])
            ]
            session.add_all(hosts)

            # Populate cluster state and host state
            cluster_states = [
                ClusterState(id=1, state="READY", progress=1.0,
                             message="Successfully!"),
                ClusterState(id=2, state="ERROR", progress=0.5,
                             message="Failed!")
            ]
            session.add_all(cluster_states)

            host_states = [
                HostState(id=1, state="READY", progress=1.0,
                          message="Successfully!"),
                HostState(id=2, state="READY", progress=1.0,
                          message="Successfully!"),
                HostState(id=3, state="READY", progress=1.0,
                          message="Successfully!"),
                HostState(id=4, state="ERROR", progress=0.5,
                          message="Failed!"),
                HostState(id=5, state="READY", progress=1.0,
                          message="Successfully!"),
                HostState(id=6, state="ERROR", progress=1.0,
                          message="Failed!")
            ]
            session.add_all(host_states)


if __name__ == '__main__':
    db_url, port = sys.argv[1:]
    print db_url
    try:
        database.init(db_url)
        database.create_db()
    except Exception as error:
        print "=====> Failed to create database"
        print error

    try:
        setupDb()
    except Exception as error:
        print "setupDb=====>Failed to setup database"
        print error

    print "Starting server ....."
    print "port is ", port
    app.run(use_reloader=False, host="0.0.0.0", port=port)
