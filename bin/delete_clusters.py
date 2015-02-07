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
import sys


current_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(current_dir)


import switch_virtualenv


from compass.db.api import cluster as cluster_api
from compass.db.api import database
from compass.db.api import host as host_api
from compass.db.api import user as user_api
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import setting_wrapper as setting


flags.add('clusternames',
          help='comma seperated cluster names',
          default='')
flags.add_bool('delete_hosts',
               help='if all hosts related to the cluster will be deleted',
               default=False)


def delete_clusters():
    clusternames = [
        clustername
        for clustername in flags.OPTIONS.clusternames.split(',')
        if clustername
    ]
    user = user_api.get_user_object(setting.COMPASS_ADMIN_EMAIL)
    list_cluster_args = {}
    if clusternames:
        list_cluster_args['name'] = clusternames
    clusters = cluster_api.list_clusters(
        user=user, **list_cluster_args
    )
    delete_underlying_host = flags.OPTIONS.delete_hosts
    for cluster in clusters:
        cluster_id = cluster['id']
        cluster_api.del_cluster(
            cluster_id, True, False, delete_underlying_host, user=user
        )


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    database.init()
    delete_clusters()
