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

"""utility binary to manage database."""
import os
import os.path
import sys

from flask.ext.script import Manager

from compass.actions import clean_deployment
from compass.actions import clean_installing_progress
from compass.actions import deploy
from compass.actions import reinstall
from compass.actions import search
from compass.api import app
from compass.config_management.utils import config_manager
from compass.db.api import database
from compass.tasks.client import celery
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import setting_wrapper as setting
from compass.utils import util


flags.add('table_name',
          help='table name',
          default='')
flags.add('clusters',
          help=(
              'clusters and hosts of each cluster, the format is as '
              'clusterid:hostname1,hostname2,...;...'),
          default='')
flags.add_bool('async',
               help='ryn in async mode',
               default=True)
flags.add('switch_machines_file',
          help=(
              'files for switches and machines '
              'connected to each switch. each line in the file '
              'is machine,<switch ip>,<switch port>,<vlan>,<mac> '
              'or switch,<switch_ip>,<switch_vendor>,'
              '<switch_version>,<switch_community>,<switch_state>'),
          default='')
flags.add('search_cluster_properties',
          help='comma separated properties to search in cluster config',
          default='')
flags.add('print_cluster_properties',
          help='comma separated cluster config properties to print',
          default='')
flags.add('search_host_properties',
          help='comma separated properties to search in host config',
          default='')
flags.add('print_host_properties',
          help='comma separated host config properties to print',
          default='')


app_manager = Manager(app, usage="Perform database operations")


TABLE_MAPPING = {
}


@app_manager.command
def list_config():
    "List the commands."
    for key, value in app.config.items():
        print key, value


@app_manager.command
def checkdb():
    """check if db exists."""
    if setting.DATABASE_TYPE == 'file':
        if os.path.exists(setting.DATABASE_FILE):
            sys.exit(0)
        else:
            sys.exit(1)

    sys.exit(0)


@app_manager.command
def createdb():
    """Creates database from sqlalchemy models."""
    try:
        dropdb()
    except Exception:
        pass

    if setting.DATABASE_TYPE == 'file':
        if os.path.exists(setting.DATABASE_FILE):
            os.remove(setting.DATABASE_FILE)
    database.create_db()
    if setting.DATABASE_TYPE == 'file':
        os.chmod(setting.DATABASE_FILE, 0o777)


@app_manager.command
def dropdb():
    """Drops database from sqlalchemy models."""
    database.drop_db()


@app_manager.command
def createtable():
    """Create database table."""
    if not flags.OPTIONS.table_name:
        print 'flag --table_name is missing'
        return

    table_name = flags.OPTIONS.table_name
    if table_name not in TABLE_MAPPING:
        print '--table_name should be in %s' % TABLE_MAPPING.keys()
        return

    database.create_table(TABLE_MAPPING[table_name])


@app_manager.command
def droptable():
    """Drop database table."""
    if not flags.OPTIONS.table_name:
        print 'flag --table_name is missing'
        return

    table_name = flags.OPTIONS.table_name
    if table_name not in TABLE_MAPPING:
        print '--table_name should be in %s' % TABLE_MAPPING.keys()
        return

    database.drop_table(TABLE_MAPPING[table_name])


@app_manager.command
def sync_from_installers():
    """set adapters in Adapter table from installers."""
    with database.session():
        manager = config_manager.ConfigManager()
        manager.update_adapters_from_installers()


@app_manager.command
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
    with database.session():
        manager = config_manager.ConfigManager()
        manager.update_switch_filters()


@app_manager.command
def clean_clusters():
    """Delete clusters and hosts.

    .. note::
       The clusters and hosts are defined in --clusters.
       the clusters flag is as clusterid:hostname1,hostname2,...;...
    """
    cluster_hosts = util.get_clusters_from_str(flags.OPTIONS.clusters)
    if flags.OPTIONS.async:
        celery.send_task('compass.tasks.clean_deployment', (cluster_hosts,))
    else:
        clean_deployment.clean_deployment(cluster_hosts)


@app_manager.command
def clean_installation_progress():
    """Clean clusters and hosts installation progress.

    .. note::
       The cluster and hosts is defined in --clusters.
       The clusters flags is as clusterid:hostname1,hostname2,...;...
    """
    cluster_hosts = util.get_clusters_from_str(flags.OPTIONS.clusters)
    if flags.OPTIONS.async:
        celery.send_task('compass.tasks.clean_installing_progress',
                         (cluster_hosts,))
    else:
        clean_installing_progress.clean_installing_progress(cluster_hosts)


@app_manager.command
def reinstall_clusters():
    """Reinstall hosts in clusters.

    .. note::
       The hosts are defined in --clusters.
       The clusters flag is as clusterid:hostname1,hostname2,...;...
    """
    cluster_hosts = util.get_clusters_from_str(flags.OPTIONS.clusters)
    if flags.OPTIONS.async:
        celery.send_task('compass.tasks.reinstall', (cluster_hosts,))
    else:
        reinstall.reinstall(cluster_hosts)


@app_manager.command
def deploy_clusters():
    """Deploy hosts in clusters.

    .. note::
       The hosts are defined in --clusters.
       The clusters flag is as clusterid:hostname1,hostname2,...;...
    """
    cluster_hosts = util.get_clusters_from_str(flags.OPTIONS.clusters)
    if flags.OPTIONS.async:
        celery.send_task('compass.tasks.deploy', (cluster_hosts,))
    else:
        deploy.deploy(cluster_hosts)


@app_manager.command
def set_switch_machines():
    """Set switches and machines.

    .. note::
       --switch_machines_file is the filename which stores all switches
       and machines information.
       each line in fake_switches_files presents one machine.
       the format of each line machine,<switch_ip>,<switch_port>,<vlan>,<mac>
       or switch,<switch_ip>,<switch_vendor>,<switch_version>,
       <switch_community>,<switch_state>
    """
    if not flags.OPTIONS.switch_machines_file:
        print 'flag --switch_machines_file is missing'
        return

    switches, switch_machines = util.get_switch_machines_from_file(
        flags.OPTIONS.switch_machines_file)
    with database.session():
        manager = config_manager.ConfigManager()
        manager.update_switch_and_machines(switches, switch_machines)


@app_manager.command
def search_cluster_hosts():
    """Search cluster hosts by properties.

    .. note::
       --search_cluster_properties defines what properties are used to search.
       the format of search_cluster_properties is as
       <property_name>=<property_value>;... If no search properties are set,
       It will returns properties of all hosts.
       --print_cluster_properties defines what properties to print.
       the format of print_cluster_properties is as
       <property_name>;...
       --search_host_properties defines what properties are used to search.
       the format of search_host_properties is as
       <property_name>=<property_value>;... If no search properties are set,
       It will returns properties of all hosts.
       --print_host_properties defines what properties to print.
       the format of print_host_properties is as
       <property_name>;...

    """
    cluster_properties = util.get_properties_from_str(
        flags.OPTIONS.search_cluster_properties)
    cluster_properties_name = util.get_properties_name_from_str(
        flags.OPTIONS.print_cluster_properties)
    host_properties = util.get_properties_from_str(
        flags.OPTIONS.search_host_properties)
    host_properties_name = util.get_properties_name_from_str(
        flags.OPTIONS.print_host_properties)
    cluster_hosts = util.get_clusters_from_str(flags.OPTIONS.clusters)
    cluster_properties, cluster_host_properties = search.search(
        cluster_hosts, cluster_properties,
        cluster_properties_name, host_properties,
        host_properties_name)
    print 'clusters properties:'
    util.print_properties(cluster_properties)
    for clusterid, host_properties in cluster_host_properties.items():
        print 'hosts properties under cluster %s' % clusterid
        util.print_properties(host_properties)


if __name__ == "__main__":
    flags.init()
    logsetting.init()
    app_manager.run()
