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

"""Module to define celery tasks.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import logging

from celery.signals import celeryd_init
from celery.signals import setup_logging

from compass.actions import deploy
from compass.actions import poll_switch
from compass.actions import reinstall
from compass.db.api import adapter_holder as adapter_api
from compass.db.api import database
from compass.db.api import metadata_holder as metadata_api

from compass.tasks.client import celery
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import setting_wrapper as setting


@celeryd_init.connect()
def global_celery_init(**_):
    """Initialization code."""
    flags.init()
    flags.OPTIONS.logfile = setting.CELERY_LOGFILE
    logsetting.init()
    database.init()
    adapter_api.load_adapters()
    metadata_api.load_metadatas()


@setup_logging.connect()
def tasks_setup_logging(**_):
    """Setup logging options from compass setting."""
    flags.init()
    flags.OPTIONS.logfile = setting.CELERY_LOGFILE
    logsetting.init()


@celery.task(name='compass.tasks.pollswitch')
def pollswitch(
    poller_email, ip_addr, credentials,
    req_obj='mac', oper='SCAN'
):
    """Query switch and return expected result.

    :param ip_addr: switch ip address.
    :type ip_addr: str
    :param credentials: switch credentials
    :type credentials: dict
    :param reqObj: the object requested to query from switch.
    :type reqObj: str
    :param oper: the operation to query the switch (SCAN, GET, SET).
    :type oper: str
    """
    try:
        poll_switch.poll_switch(
            poller_email, ip_addr, credentials,
            req_obj=req_obj, oper=oper
        )
    except Exception as error:
        logging.exception(error)


@celery.task(name='compass.tasks.deploy_cluster')
def deploy_cluster(deployer_email, cluster_id, clusterhost_ids):
    """Deploy the given cluster.

    :param cluster_hosts: the cluster and hosts of each cluster to deploy.
    :type cluster_hosts: dict of int to list of int
    """
    try:
        deploy.deploy(cluster_id, clusterhost_ids, deployer_email)
    except Exception as error:
        logging.exception(error)


@celery.task(name='compass.tasks.reinstall_cluster')
def reinstall_cluster(installer_email, cluster_id, clusterhost_ids):
    """reinstall the given cluster.

    :param cluster_hosts: the cluster and hosts of each cluster to reinstall.
    :type cluster_hosts: dict of int to list of int
    """
    pass


@celery.task(name='compass.tasks.poweron_host')
def poweron_host(host_id):
    """Deploy the given cluster.

    :param cluster_hosts: the cluster and hosts of each cluster to deploy.
    :type cluster_hosts: dict of int to list of int
    """
    pass


@celery.task(name='compass.tasks.poweroff_host')
def poweroff_host(host_id):
    """Deploy the given cluster.

    :param cluster_hosts: the cluster and hosts of each cluster to deploy.
    :type cluster_hosts: dict of int to list of int
    """
    pass


@celery.task(name='compass.tasks.reset_host')
def reset_host(host_id):
    """Deploy the given cluster.

    :param cluster_hosts: the cluster and hosts of each cluster to deploy.
    :type cluster_hosts: dict of int to list of int
    """
    pass
