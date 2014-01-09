#!/usr/bin/python
import logging
import os
import os.path
import shutil
import sys

from flask.ext.script import Manager

from compass.api import app
from compass.config_management.utils import config_manager
from compass.db import database
from compass.db.model import Adapter, Role, Switch, Machine, HostState, ClusterState, Cluster, ClusterHost, LogProgressingHistory    
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import setting_wrapper as setting


flags.add('table_name',
          help='table name',
          default='')
flags.add('clusters',
          help=(
              'clusters to clean, the format is as '
              'clusterid:hostname1,hostname2,...;...'),
          default='')


manager = Manager(app, usage="Perform database operations")


TABLE_MAPPING = {
    'role': Role,
    'adapter': Adapter,
    'switch': Switch,
    'machine': Machine,
    'hoststate': HostState,
    'clusterstate': ClusterState,
    'cluster': Cluster,
    'clusterhost': ClusterHost,
    'logprogressinghistory': LogProgressingHistory,
}


@manager.command
def list_config():
    "List the configuration"
    for key, value in app.config.items():
        print key, value


@manager.command
def createdb():
    "Creates database from sqlalchemy models"
    if setting.DATABASE_TYPE == 'sqlite':
        if os.path.exists(setting.DATABASE_FILE):
            os.remove(setting.DATABASE_FILE)
    database.create_db()
    if setting.DATABASE_TYPE == 'sqlite':
        os.chmod(setting.DATABASE_FILE, 0777)

@manager.command
def dropdb():
    "Drops database from sqlalchemy models"
    database.drop_db()


@manager.command
def createtable():
    """Create database table by --table_name"""
    table_name = flags.OPTIONS.table_name
    if table_name and table_name in TABLE_MAPPING:
        database.create_table(TABLE_MAPPING[table_name])
    else:
        print '--table_name should be in %s' % TABLE_MAPPING.keys()

              
@manager.command
def droptable():
    """Drop database table by --talbe_name"""
    table_name = flags.OPTIONS.table_name
    if table_name and table_name in TABLE_MAPPING:
        database.drop_table(TABLE_MAPPING[table_name])
    else:
        print '--table_name should be in %s' % TABLE_MAPPING.keys()


@manager.command
def sync_from_installers():
    """set adapters in Adapter table from installers."""
    manager = config_manager.ConfigManager()
    adapters = manager.get_adapters()
    target_systems = set()
    roles_per_target_system = {}
    for adapter in adapters:
        target_systems.add(adapter['target_system'])
    for target_system in target_systems:
        roles_per_target_system[target_system] = manager.get_roles(
            target_system)
    with database.session() as session:
        session.query(Adapter).delete()
        session.query(Role).delete()
        for adapter in adapters:
            session.add(Adapter(**adapter))
        for target_system, roles in roles_per_target_system.items():
            for role in roles:
                session.add(Role(**role))
 

def _get_clusters():
    clusters = {}
    logging.debug('get clusters from flag: %s', flags.OPTIONS.clusters)
    for clusterid_and_hostnames in flags.OPTIONS.clusters.split(';'):
        if not clusterid_and_hostnames:
            continue

        if ':' in clusterid_and_hostnames:
            clusterid_str, hostnames_str = clusterid_and_hostnames.split(
                ':', 1)
        else:
            clusterid_str = clusterid_and_hostnames
            hostnames_str = ''

        clusterid = int(clusterid_str)
        hostnames = [
            hostname for hostname in hostnames_str.split(',')
            if hostname
        ]
        clusters[clusterid] = hostnames

    logging.debug('got clusters from flag: %s', clusters)
    with database.session() as session:
        clusterids = clusters.keys()
        if not clusterids:
            cluster_list = session.query(Cluster).all()
            clusterids = [cluster.id for cluster in cluster_list]

        for clusterid in clusterids:
            hostnames = clusters.get(clusterid, [])
            if not hostnames:
                host_list = session.query(ClusterHost).filter_by(
                    cluster_id=clusterid).all()
                hostids = [host.id for host in host_list]
                clusters[clusterid] = hostids
            else:
                hostids = []
                for hostname in hostnames:
                    host = session.query(ClusterHost).filter_by(
                        cluster_id=clusterid, hostname=hostname).first()
                    if host:
                        hostids.append(host.id)
                clusters[clusterid] = hostids

    return clusters 


def _clean_clusters(clusters):
    manager = config_manager.ConfigManager()
    logging.info('clean cluster hosts: %s', clusters)
    with database.session() as session:
        for clusterid, hostids in clusters.items():
            cluster = session.query(Cluster).filter_by(id=clusterid).first()
            if not cluster:
                continue
           
            all_hostids = [host.id for host in cluster.hosts]
            logging.debug('all hosts in cluster %s is: %s',
                          clusterid, all_hostids)

            logging.info('clean hosts %s in cluster %s',
                         hostids, clusterid)

            adapter = cluster.adapter
            for hostid in hostids:
                host = session.query(ClusterHost).filter_by(id=hostid).first()
                if not host:
                    continue

                log_dir = os.path.join(
                    setting.INSTALLATION_LOGDIR,
                    '%s.%s' % (host.hostname, clusterid))
                logging.info('clean log dir %s', log_dir)
                shutil.rmtree(log_dir, True)
                session.query(LogProgressingHistory).filter(
                    LogProgressingHistory.pathname.startswith(
                        '%s/' % log_dir)).delete(
                    synchronize_session='fetch')

                logging.info('clean host %s', hostid)
                manager.clean_host_config(
                    hostid,
                    os_version=adapter.os,
                    target_system=adapter.target_system)
                session.query(ClusterHost).filter_by(
                    id=hostid).delete(synchronize_session='fetch')
                session.query(HostState).filter_by(
                    id=hostid).delete(synchronize_session='fetch')

            if set(all_hostids) == set(hostids):
                logging.info('clean cluster %s', clusterid)
                manager.clean_cluster_config(
                    clusterid,
                    os_version=adapter.os,
                    target_system=adapter.target_system)
                session.query(Cluster).filter_by(
                    id=clusterid).delete(synchronize_session='fetch')
                session.query(ClusterState).filter_by(
                    id=clusterid).delete(synchronize_session='fetch')

    manager.sync()


@manager.command
def clean_clusters():
    """delete clusters and hosts.
       The clusters and hosts are defined in --clusters.
    """
    clusters = _get_clusters()
    _clean_clusters(clusters)
    os.system('service rsyslog restart')


def _clean_installation_progress(clusters):
    logging.info('clean installation progress for cluster hosts: %s',
                 clusters)
    with database.session() as session:
        for clusterid, hostids in clusters.items():
            cluster = session.query(Cluster).filter_by(
                id=clusterid).first()
            if not cluster:
                continue

            logging.info(
                'clean installation progress for hosts %s in cluster %s',
                hostids, clusterid)
            
            all_hostids = [host.id for host in cluster.hosts]
            logging.debug('all hosts in cluster %s is: %s',
                          clusterid, all_hostids)

            for hostid in hostids:
                host = session.query(ClusterHost).filter_by(id=hostid).first()
                if not host:
                    continue

                log_dir = os.path.join(
                    setting.INSTALLATION_LOGDIR,
                    '%s.%s' % (host.hostname, clusterid))

                logging.info('clean log dir %s', log_dir)
                shutil.rmtree(log_dir, True)

                session.query(LogProgressingHistory).filter(
                    LogProgressingHistory.pathname.startswith(
                        '%s/' % log_dir)).delete(
                    synchronize_session='fetch')

                logging.info('clean host installation progress for %s',
                             hostid)
                if host.state and host.state.state != 'UNINITIALIZED':
                    session.query(ClusterHost).filter_by(
                        id=hostid).update({
                            'mutable': False
                        }, synchronize_session='fetch')
                    session.query(HostState).filter_by(id=hostid).update({
                        'state': 'INSTALLING',
                        'progress': 0.0,
                        'message': '',
                        'severity': 'INFO'
                    }, synchronize_session='fetch')

            if set(all_hostids) == set(hostids):
                logging.info('clean cluster installation progress %s',
                             clusterid)
                if cluster.state and cluster.state != 'UNINITIALIZED':
                    session.query(Cluster).filter_by(
                        id=clusterid).update({
                        'mutable': False
                    }, synchronize_session='fetch')
                    session.query(ClusterState).filter_by(
                        id=clusterid).update({
                        'state': 'INSTALLING',
                        'progress': 0.0,
                        'message': '',
                        'severity': 'INFO'
                    }, synchronize_session='fetch')


@manager.command
def clean_installation_progress():
    """Clean clusters and hosts installation progress.
       The cluster and hosts is defined in --clusters.
    """
    clusters = _get_clusters()
    _clean_installation_progress(clusters)
    os.system('service rsyslog restart')


def _reinstall_hosts(clusters):
    logging.info('reinstall cluster hosts: %s', clusters)
    manager = config_manager.ConfigManager()
    with database.session() as session:
        for clusterid, hostids in clusters.items():
            cluster = session.query(Cluster).filter_by(id=clusterid).first()
            if not cluster:
                continue
           
            all_hostids = [host.id for host in cluster.hosts]
            logging.debug('all hosts in cluster %s is: %s',
                          clusterid, all_hostids)

            logging.info('reinstall hosts %s in cluster %s',
                         hostids, clusterid)
            adapter = cluster.adapter
            for hostid in hostids:
                host = session.query(ClusterHost).filter_by(id=hostid).first()
                if not host:
                    continue

                log_dir = os.path.join(
                    setting.INSTALLATION_LOGDIR,
                    '%s.%s' % (host.hostname, clusterid))
                logging.info('clean log dir %s', log_dir)
                shutil.rmtree(log_dir, True)
                session.query(LogProgressingHistory).filter(
                    LogProgressingHistory.pathname.startswith(
                        '%s/' % log_dir)).delete(
                    synchronize_session='fetch')

                logging.info('reinstall host %s', hostid)
                manager.reinstall_host(
                    hostid,
                    os_version=adapter.os,
                    target_system=adapter.target_system)
                if host.state and host.state.state != 'UNINITIALIZED':
                    session.query(ClusterHost).filter_by(
                        id=hostid).update({
                            'mutable': False
                        }, synchronize_session='fetch')
                    session.query(HostState).filter_by(
                        id=hostid).update({
                            'state': 'INSTALLING',
                            'progress': 0.0,
                            'message': '',
                            'severity': 'INFO'
                        }, synchronize_session='fetch')

            if set(all_hostids) == set(hostids):
                logging.info('reinstall cluster %s',
                             clusterid)
                if cluster.state and cluster.state != 'UNINITIALIZED':
                    session.query(Cluster).filter_by(
                        id=clusterid).update({
                        'mutable': False
                    }, synchronize_session='fetch')
                    session.query(ClusterState).filter_by(
                        id=clusterid).update({
                        'state': 'INSTALLING',
                        'progress': 0.0,
                        'message': '',
                        'severity': 'INFO'
                    }, synchronize_session='fetch')

    manager.sync()
  

@manager.command
def reinstall_hosts():
    """Reinstall hosts in clusters.
       the hosts are defined in --clusters.
    """
    clusters = _get_clusters()
    _reinstall_hosts(clusters)


@manager.command
def set_fake_switch_machine():
    """Set fake switches and machines for test."""
    with database.session() as session:
        credential = { 'version'    :  'v2c',
                       'community'  :  'public',
                     }
        switches = [ {'ip': '192.168.100.250'},
                     {'ip': '192.168.100.251'},
                     {'ip': '192.168.100.252'},
        ]
        session.query(Switch).delete()
        session.query(Machine).delete()
        ip_switch ={}
        for item in switches:
            logging.info('add switch %s', item)     
            switch = Switch(ip=item['ip'], vendor_info='huawei',
                            state='under_monitoring')
            switch.credential = credential
            session.add(switch)
            ip_switch[item['ip']] = switch
        session.flush()

        machines = [
            {'mac': '00:0c:29:32:76:85', 'port':50, 'vlan':1, 'switch_ip':'192.168.100.250'},
            {'mac': '00:0c:29:fa:cb:72', 'port':51, 'vlan':1, 'switch_ip':'192.168.100.250'},
            {'mac': '28:6e:d4:64:c7:4a', 'port':1, 'vlan':1, 'switch_ip':'192.168.100.251'},
            {'mac': '28:6e:d4:64:c7:4c', 'port':2, 'vlan':1, 'switch_ip':'192.168.100.251'},
            {'mac': '28:6e:d4:46:c4:25', 'port': 40, 'vlan': 1, 'switch_ip': '192.168.100.252'},
            {'mac': '26:6e:d4:4d:c6:be', 'port': 41, 'vlan': 1, 'switch_ip': '192.168.100.252'},
            {'mac': '28:6e:d4:62:da:38', 'port': 42, 'vlan': 1, 'switch_ip': '192.168.100.252'},
            {'mac': '28:6e:d4:62:db:76', 'port': 43, 'vlan': 1, 'switch_ip': '192.168.100.252'},
        ]
       
        for item in machines:
            logging.info('add machine %s', item)
            machine = Machine(mac=item['mac'], port=item['port'],
                              vlan=item['vlan'],
                              switch_id=ip_switch[item['switch_ip']].id)
            session.add(machine)

 
if __name__ == "__main__":
    flags.init()
    logsetting.init()
    manager.run()
