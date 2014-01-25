"""Module to define celery tasks.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
from celery.signals import setup_logging

from compass.actions import poll_switch
from compass.actions import trigger_install
from compass.actions import progress_update
from compass.db import database
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


@celery.task(name="compass.tasks.pollswitch")
def pollswitch(ip_addr, req_obj='mac', oper="SCAN"):
    """Query switch and return expected result.

    :param ip_addr: switch ip address.
    :type ip_addr: str
    :param reqObj: the object requested to query from switch.
    :type reqObj: str
    :param oper: the operation to query the switch (SCAN, GET, SET).
    :type oper: str
    """
    with database.session():
        poll_switch.poll_switch(ip_addr, req_obj='mac', oper="SCAN")


@celery.task(name="compass.tasks.trigger_install")
def triggerinstall(clusterid, hostids=[]):
    """Deploy the given cluster.

    :param clusterid: the id of the cluster to deploy.
    :type clusterid: int
    :param hostids: the ids of the hosts to deploy.
    :type hostids: list of int
    """
    with database.session():
        trigger_install.trigger_install(clusterid, hostids)


@celery.task(name="compass.tasks.progress_update")
def progressupdate(clusterid):
    """Calculate the installing progress of the given cluster.

    :param clusterid: the id of the cluster to get the intstalling progress.
    :type clusterid: int
    """
    progress_update.update_progress(clusterid)
