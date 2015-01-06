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

from compass.actions import clean
from compass.actions import delete
from compass.actions import deploy
from compass.actions import poll_switch
from compass.actions import update_progress
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


@celery.task(name='compass.tasks.health_check')
def health_check(cluster_id, send_report_url, useremail):
    """Verify the deployed cluster functionally works.

       :param cluster_id: ID of the cluster
       :param send_report_url: The URL which reports should send back
    """
    try:
        deploy.health_check(cluster_id, send_report_url, useremail)
    except Exception as error:
        logging.exception(error)


@celery.task(name='compass.tasks.deploy_cluster')
def deploy_cluster(deployer_email, cluster_id, clusterhost_ids):
    """Deploy the given cluster.

    :param cluster_id: id of the cluster
    :type cluster_id: int
    :param clusterhost_ids: the id of the hosts in the cluster
    :type clusterhost_ids: list of int
    """
    try:
        deploy.deploy(cluster_id, clusterhost_ids, deployer_email)
    except Exception as error:
        logging.exception(error)


@celery.task(name='compass.tasks.reinstall_cluster')
def reinstall_cluster(installer_email, cluster_id, clusterhost_ids):
    """reinstall the given cluster.

    :param cluster_id: id of the cluster
    :type cluster_id: int
    :param clusterhost_ids: the id of the hosts in the cluster
    :type clusterhost_ids: list of int
    """
    try:
        deploy.redeploy(cluster_id, clusterhost_ids, installer_email)
    except Exception as error:
        logging.exception(error)


@celery.task(name='compass.tasks.delete_cluster')
def delete_cluster(
    deleter_email, cluster_id, clusterhost_ids,
    delete_underlying_host=False
):
    """Delete the given cluster.

    :param cluster_id: id of the cluster
    :type cluster_id: int
    :param clusterhost_ids: the id of the hosts in the cluster
    :type clusterhost_ids: list of int
    """
    try:
        delete.delete_cluster(
            cluster_id, clusterhost_ids, deleter_email,
            delete_underlying_host=delete_underlying_host
        )
    except Exception as error:
        logging.exception(error)


@celery.task(name='compass.tasks.delete_cluster_host')
def delete_cluster_host(
    deleter_email, cluster_id, host_id,
    delete_underlying_host=False
):
    """Delte the given cluster host.

    :param cluster_id: id of the cluster
    :type cluster_id: int
    :param host_id: id of the host
    :type host_id: int
    """
    try:
        delete.delete_cluster_host(
            cluster_id, host_id, deleter_email,
            delete_underlying_host=delete_underlying_host
        )
    except Exception as error:
        logging.exception(error)


@celery.task(name='compass.tasks.delete_host')
def delete_host(deleter_email, host_id, cluster_ids):
    """Delete the given host.

    :param host_id: id of the host
    :type host_id: int
    :param cluster_ids: list of cluster id
    :type cluster_ids: list of int
    """
    try:
        delete.delete_host(
            host_id, deleter_email, cluster_ids
        )
    except Exception as error:
        logging.exception(error)


@celery.task(name='compass.tasks.clean_os_installer')
def clean_os_installer(
    os_installer_name, os_installer_settings
):
    """Clean os installer."""
    try:
        clean.clean_os_installer(
            os_installer_name, os_installer_settings
        )
    except Exception as error:
        logging.excception(error)


@celery.task(name='compass.tasks.clean_package_installer')
def clean_package_installer(
    package_installer_name, package_installer_settings
):
    """Clean package installer."""
    try:
        clean.clean_package_installer(
            package_installer_name, package_installer_settings
        )
    except Exception as error:
        logging.excception(error)


@celery.task(name='compass.tasks.poweron_host')
def poweron_host(host_id):
    """Deploy the given cluster.
    """
    pass


@celery.task(name='compass.tasks.poweroff_host')
def poweroff_host(host_id):
    """Deploy the given cluster.
    """
    pass


@celery.task(name='compass.tasks.reset_host')
def reset_host(host_id):
    """Deploy the given cluster.
    """
    pass


@celery.task(name='compass.tasks.poweron_machine')
def poweron_machine(machine_id):
    """Deploy the given cluster.
    """
    pass


@celery.task(name='compass.tasks.poweroff_machine')
def poweroff_machine(machine_id):
    """Deploy the given cluster.
    """
    pass


@celery.task(name='compass.tasks.reset_machine')
def reset_machine(machine_id):
    """Deploy the given cluster.
    """
    pass


@celery.task(name='compass.tasks.update_progress')
def update_clusters_progress():
    """Calculate the installing progress of the given cluster.
    """
    logging.info('update_clusters_progress')
    try:
        update_progress.update_progress()
    except Exception as error:
        logging.exception(error)
