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

"""Module to define celery tasks.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
from celery.signals import setup_logging

from compass.actions import clean_deployment
from compass.actions import clean_installing_progress
from compass.actions import deploy
from compass.actions import poll_switch
from compass.actions import reinstall
from compass.actions import update_progress
from compass.tasks.client import celery
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import setting_wrapper as setting


def tasks_setup_logging(**_):
    """Setup logging options from compass setting."""
    flags.init()
    flags.OPTIONS.logfile = setting.CELERY_LOGFILE
    logsetting.init()


setup_logging.connect(tasks_setup_logging)


@celery.task(name='compass.tasks.pollswitch')
def pollswitch(ip_addr, req_obj='mac', oper='SCAN'):
    """Query switch and return expected result.

    :param ip_addr: switch ip address.
    :type ip_addr: str
    :param reqObj: the object requested to query from switch.
    :type reqObj: str
    :param oper: the operation to query the switch (SCAN, GET, SET).
    :type oper: str
    """
    poll_switch.poll_switch(ip_addr, req_obj=req_obj, oper=oper)


@celery.task(name='compass.tasks.deploy')
def deploy_clusters(cluster_hosts):
    """Deploy the given cluster.

    :param cluster_hosts: the cluster and hosts of each cluster to deploy.
    :type cluster_hosts: dict of int to list of int
    """
    deploy.deploy(cluster_hosts)


@celery.task(name='compass.tasks.reinstall')
def reinstall_clusters(cluster_hosts):
    """reinstall the given cluster.

    :param cluster_hosts: the cluster and hosts of each cluster to reinstall.
    :type cluster_hosts: dict of int to list of int
    """
    reinstall.reinstall(cluster_hosts)


@celery.task(name='compass.tasks.clean_deployment')
def clean_clusters_deployment(cluster_hosts):
    """clean deployment of the given cluster.

    :param cluster_hosts: the cluster and hosts of each cluster to clean.
    :type cluster_hosts: dict of int to list of int
    """
    clean_deployment.clean_deployment(cluster_hosts)


@celery.task(name='compass.tasks.clean_installing_progress')
def clean_clusters_installing_progress(cluster_hosts):
    """clean installing progress of the given cluster.

    :param cluster_hosts: the cluster and hosts of each cluster to clean.
    :type cluster_hosts: dict of int to list of int
    """
    clean_installing_progress.clean_installing_progress(cluster_hosts)


@celery.task(name='compass.tasks.update_progress')
def update_clusters_progress(cluster_hosts):
    """Calculate the installing progress of the given cluster.

    :param cluster_hosts: the cluster and hosts of each cluster to update.
    :type cluster_hosts: dict of int to list of int
    """
    update_progress.update_progress(cluster_hosts)
