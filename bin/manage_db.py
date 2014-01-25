#!/usr/bin/python
import logging
import os
import os.path
import re
import shutil
import sys

from flask.ext.script import Manager

from compass.api import app
from compass.config_management.utils import config_manager
from compass.config_management.utils import config_reference
from compass.db import database
from compass.db.model import Adapter, Role, Switch, SwitchConfig
from compass.db.model import Machine, HostState, ClusterState
from compass.db.model import Cluster, ClusterHost, LogProgressingHistory    
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
flags.add('fake_switches_file',
          help=(
              'files for switches and machines '
              'connected to each switch. each line in the file '
              'is <switch ip>,<switch port>,<vlan>,<mac>'),
          default='')
flags.add('fake_switches_vendor',
          help='switch vendor used to set fake switch and machines.',
          default='huawei')
flags.add('search_config_properties',
          help='semicomma separated properties to search in config',
          default='')
flags.add('print_config_properties',
          help='semicomma separated config properties to print',
          default='') 


manager = Manager(app, usage="Perform database operations")


TABLE_MAPPING = {
    'role': Role,
    'adapter': Adapter,
    'switch': Switch,
    'switch_config': SwitchConfig,
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
    if setting.DATABASE_TYPE == 'file':
        if os.path.exists(setting.DATABASE_FILE):
            os.remove(setting.DATABASE_FILE)
    database.create_db()
    if setting.DATABASE_TYPE == 'file':
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
 

@manager.command
def sync_switch_configs():
    """Set switch configs in SwitchConfig table from setting.

    .. note::
       the switch config is stored in SWITCHES list in setting config.
       for each entry in the SWITCHES, its type is dict and must contain
       fields 'switch_ips' and 'filter_ports'.
       The format of switch_ips is
       <ip_blocks>.<ip_blocks>.<ip_blocks>.<ip_blocks>.
       ip_blocks consists of ip_block separated by comma.
       ip_block can be an integer and a range of integer like xx-xx.
       The example of switch_ips is like: xxx.xxx.xxx-yyy,xxx-yyy.xxx,yyy
       The format of filter_ports consists of list of
       <port_prefix><port_range> separated by comma. port_range can be an
       integer or a rnage of integer like xx-xx.
       The example of filter_ports is like: ae1-5,20-40.
    """
    if not hasattr(setting, 'SWITCHES') or not setting.SWITCHES:
        logging.info('no switch configs to set')
        return

    switch_configs = []
    port_pat = re.compile(r'(\D*)(\d+(?:-\d+)?)')

    for switch in setting.SWITCHES:
        ips = []
        blocks = switch['switch_ips'].split('.')
        ip_blocks_list = []
        for block in blocks:
            ip_blocks_list.append([])
            sub_blocks = block.split(',')
            for sub_block in sub_blocks:
                if not sub_block:
                    continue

                if '-' in sub_block:
                    start_block, end_block = sub_block.split('-', 1)
                    start_block = int(start_block)
                    end_block = int(end_block)
                    if start_block > end_block:
                        continue

                    ip_block = start_block
                    while ip_block <= end_block:
                        ip_blocks_list[-1].append(str(ip_block))
                        ip_block += 1

                else:
                    ip_blocks_list[-1].append(sub_block)

        ip_prefixes = [[]]
        for ip_blocks in ip_blocks_list:
            prefixes = []
            for ip_block in ip_blocks:
                for prefix in ip_prefixes:
                    prefixes.append(prefix + [ip_block])

            ip_prefixes = prefixes

        for prefix in ip_prefixes:
            if not prefix:
                continue

            ips.append('.'.join(prefix))

        logging.debug('found switch ips: %s', ips)

        filter_ports = []
        for port_range in switch['filter_ports'].split(','):
            if not port_range:
                continue

            mat = port_pat.match(port_range)
            if not mat:
                filter_ports.append(port_range)
            else:
                port_prefix = mat.group(1)
                port_range = mat.group(2)
                if '-' in port_range:
                    start_port, end_port = port_range.split('-', 1)
                    start_port = int(start_port)
                    end_port = int(end_port)
                    if start_port > end_port:
                        continue

                    port = start_port
                    while port <= end_port:
                        filter_ports.append('%s%s' % (port_prefix, port))
                        port += 1

                else:
                    filter_ports.append('%s%s' % (port_prefix, port_range))

        for ip in ips:
            for filter_port in filter_ports:
                switch_configs.append(
                    {'ip': ip, 'filter_port': filter_port})

    switch_config_tuples = set([])
    with database.session() as session:
        session.query(SwitchConfig).delete(synchronize_session='fetch')
        for switch_config in switch_configs:
            switch_config_tuple = tuple(switch_config.values())
            if switch_config_tuple in switch_config_tuples:
                logging.debug('ignore adding switch config: %s',
                              switch_config)
                continue
            else:
                logging.debug('add switch config: %s', switch_config)
                switch_config_tuples.add(switch_config_tuple)

            session.add(SwitchConfig(**switch_config))
            

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
    """Delete clusters and hosts.

    .. note::
       The clusters and hosts are defined in --clusters.
       the clusters flag is as clusterid:hostname1,hostname2,...;...
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

    .. note::
       The cluster and hosts is defined in --clusters.
       The clusters flags is as clusterid:hostname1,hostname2,...;...
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

    .. note::
       The hosts are defined in --clusters.
       The clusters flag is as clusterid:hostname1,hostname2,...;...
    """
    clusters = _get_clusters()
    _reinstall_hosts(clusters)
    os.system('service rsyslog restart')


@manager.command
def set_fake_switch_machine():
    """Set fake switches and machines.

    .. note::
       --fake_switches_vendor is the vendor name for all fake switches.
       the default value is 'huawei'
       --fake_switches_file is the filename which stores all fake switches
       and fake machines.
       each line in fake_switches_files presents one machine.
       the format of each line <switch_ip>,<switch_port>,<vlan>,<mac>.
    """
    missing_flags = False
    if not flags.OPTIONS.fake_switches_vendor:
        print 'the flag --fake_switches_vendor should be specified'
        missing_flags = True

    if not flags.OPTIONS.fake_switches_file:
        print 'the flag --fake_switches_file should be specified.'
        print 'each line in fake_switches_files presents one machine'
        print 'the format of each line is <%s>,<%s>,<%s>,<%s>' % (
            'switch ip as xxx.xxx.xxx.xxx',
            'switch port as xxx12',
            'vlan as 1',
            'mac as xx:xx:xx:xx:xx:xx')
        missing_flags = True

    if missing_flags:
        return

    switch_ips = []
    switch_machines = {}
    vendor = flags.OPTIONS.fake_switches_vendor
    credential = { 
        'version'    :  'v2c',
        'community'  :  'public',
    }

    try:
        with open(flags.OPTIONS.fake_switches_file) as f:
            for line in f:
                line = line.strip()
                switch_ip, switch_port, vlan, mac = line.split(',', 3)
                if switch_ip not in switch_ips:
                    switch_ips.append(switch_ip)

                switch_machines.setdefault(switch_ip, []).append({
                    'mac': mac,
                    'port': switch_port,
                    'vlan': int(vlan)
                })

    except Exception as error:
        logging.error('failed to parse file %s',
                      flags.OPTIONS.fake_switches_file)
        logging.exception(error)
        return

    with database.session() as session:
        session.query(Switch).delete(synchronize_session='fetch')
        session.query(Machine).delete(synchronize_session='fetch')
        for switch_ip in switch_ips:
            logging.info('add switch %s', switch_ip)     
            switch = Switch(ip=switch_ip, vendor_info=vendor,
                            credential=credential,
                            state='under_monitoring')
            logging.debug('add switch %s', switch_ip)
            session.add(switch)

            machines = switch_machines[switch_ip]
            for item in machines:
                logging.debug('add machine %s', item)
                machine = Machine(**item)
                machine.switch = switch

            session.add(machine)


def _get_config_properties():
    if not flags.OPTIONS.search_config_properties:
        logging.info('the flag --search_config_properties is not specified.')
        return {}

    search_config_properties = flags.OPTIONS.search_config_properties
    config_properties = {}
    for config_property in search_config_properties.split(';'):
        if not config_property:
            continue

        if '=' not in config_property:
            logging.debug('ignore config property %s '
                          'since there is no = in it.', config_property)
            continue

        property_name, property_value = config_property.split('=', 1)
        config_properties[property_name] = property_value

    logging.debug('get search config properties: %s', config_properties)
    return config_properties


def _get_print_properties():
    if not flags.OPTIONS.print_config_properties:
        logging.info('the flag --print_config_properties is not specified.')
        return []

    print_config_properties = flags.OPTIONS.print_config_properties
    config_properties = []
    for config_property in print_config_properties.split(';'):
        if not config_property:
            continue

        config_properties.append(config_property)

    logging.debug('get print config properties: %s', config_properties)
    return config_properties



def _match_config_properties(config, config_properties):
    ref = config_reference.ConfigReference(config)
    for property_name, property_value in config_properties.items():
        config_value = ref.get(property_name)
        if config_value is None:
            return False

        if isinstance(config_value, list):
            found = False
            for config_value_item in config_value:
                if str(config_value_item) == str(property_value):
                    found = True

            if not found:
                return False

        else:
            if not str(config_value) == str(property_value):
                return False

    return True


def _print_config_properties(config, config_properties):
    ref = config_reference.ConfigReference(config)
    print_properties = []
    for property_name in config_properties:
        config_value = ref.get(property_name)
        if config_value is None:
            logging.error('did not found %s in %s',
                          property_name, config)
            continue

        print_properties.append('%s=%s' % (property_name, config_value))

    print ';'.join(print_properties)


@manager.command
def search_hosts():
    """Search hosts by properties.

    .. note::
       --search_config_properties defines what properties are used to search.
       the format of search_config_properties is as
       <property_name>=<property_value>;... If no search properties are set,
       It will returns properties of all hosts.
       --print_config_properties defines what properties to print.
       the format of print_config_properties is as
       <property_name>;...
    """
    config_properties = _get_config_properties()
    print_properties = _get_print_properties()
    with database.session() as session:
        hosts = session.query(ClusterHost).all()
        for host in hosts:
            if _match_config_properties(host.config, config_properties):
                _print_config_properties(host.config, print_properties)


@manager.command
def search_clusters():
    """Search clusters by properties.

    .. note::
       --search_config_properties defines what properties are used to search.
       the format of search_config_properties is as
       <property_name>=<property_value>;... If no search properties are set,
       It will returns properties of all hosts.
       --print_config_properties defines what properties to print.
       the format of print_config_properties is as
       <property_name>;...
    """
    config_properties = _get_config_properties()
    print_properties = _get_print_properties()
    with database.session() as session:
        clusters = session.query(Cluster).all()
        for cluster in clusters:
            if _match_config_properties(cluster.config, config_properties):
                _print_config_properties(cluster.config, print_properties)


if __name__ == "__main__":
    flags.init()
    logsetting.init()
    manager.run()
