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

"""Scripts to delete cluster and it hosts"""
import logging
import os
import os.path
import site
import sys

activate_this = '$PythonHome/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))
site.addsitedir('$PythonHome/lib/python2.6/site-packages')
sys.path.append('$PythonHome')
os.environ['PYTHON_EGG_CACHE'] = '/tmp/.egg'

from compass.db.api import database
from compass.db.api import host as host_api
from compass.db.api import cluster as cluster_api
from compass.db.api import user as user_api
from compass.db.api import utils
from compass.db import models
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import setting_wrapper as setting


flags.add('clusternames',
          help='comma seperated cluster names',
          default='')
flags.add_bool('delete_hosts',
               help='if all hosts related to the cluster will be deleted',
               default=False)



if __name__ == '__main__':
    flags.init()
    logsetting.init()
    database.init()
    clusternames = [
        clustername
        for clustername in flags.OPTIONS.clusternames.split(',')
        if clustername
    ]
    logging.info('delete clusters %s', clusternames)
    user = user_api.get_user_object(setting.COMPASS_ADMIN_EMAIL)
    clusters = cluster_api.list_clusters(
        user, name=clusternames
    )
    if flags.OPTIONS.delete_hosts:
        for cluster in clusters:
            hosts = cluster_api.list_cluster_hosts(
                user, cluster['id'])
            for host in hosts:
                logging.info('delete host %s', host['hostname'])
                host_api.del_host(user, host['id'])
    for cluster in clusters:
        logging.info('delete cluster %s', cluster['name'])
        cluster_api.del_cluster(user, cluster['id'])
