#!/usr/bin/env python
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

from compass.actions import deploy
from compass.actions import reinstall
from compass.api import app
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
    database.init()
    try:
        database.drop_db()
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
    database.init()
    database.drop_db()


@app_manager.command
def createtable():
    """Create database table."""
    database.init()
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
    database.init()
    if not flags.OPTIONS.table_name:
        print 'flag --table_name is missing'
        return

    table_name = flags.OPTIONS.table_name
    if table_name not in TABLE_MAPPING:
        print '--table_name should be in %s' % TABLE_MAPPING.keys()
        return

    database.drop_table(TABLE_MAPPING[table_name])


@app_manager.command
def reinstall_clusters():
    """Reinstall hosts in clusters.

    .. note::
       The hosts are defined in --clusters.
       The clusters flag is as clusterid:hostname1,hostname2,...;...
    """
    cluster_hosts = flags.OPTIONS.clusters
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
    cluster_hosts = flags.OPTIONS.clusters
    if flags.OPTIONS.async:
        celery.send_task('compass.tasks.deploy', (cluster_hosts,))
    else:
        deploy.deploy(cluster_hosts)


if __name__ == "__main__":
    flags.init()
    logsetting.init()
    app_manager.run()
