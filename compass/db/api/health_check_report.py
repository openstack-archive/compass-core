# Copyright 2014 Huawei Technologies Co. Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,

# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Cluster health check report."""
import logging

from compass.db.api import cluster as cluster_api
from compass.db.api import database
from compass.db.api import host as host_api
from compass.db.api import permission
from compass.db.api import user as user_api
from compass.db.api import utils
from compass.db import exception
from compass.db import models


REQUIRED_INSERT_FIELDS = ['name']
OPTIONAL_INSERT_FIELDS = [
    'display_name', 'report', 'category', 'state', 'error_message'
]
UPDATE_FIELDS = ['report', 'state', 'error_message']
RESP_FIELDS = [
    'cluster_id', 'name', 'display_name', 'report',
    'category', 'state', 'error_message'
]
RESP_ACTION_FIELDS = ['cluster_id', 'status']


@utils.supported_filters(REQUIRED_INSERT_FIELDS, OPTIONAL_INSERT_FIELDS)
@database.run_in_session()
@utils.wrap_to_dict(RESP_FIELDS)
def add_report_record(cluster_id, name=None, report={},
                      state='verifying', user=None, session=None, **kwargs):
    """Create a health check report record."""
    # Replace any white space into '-'
    words = name.split()
    name = '-'.join(words)
    cluster = cluster_api.get_cluster(cluster_id, user=user, session=session)
    return utils.add_db_object(
        session, models.HealthCheckReport, True, cluster['id'], name,
        report=report, state=state, **kwargs
    )


@utils.supported_filters(UPDATE_FIELDS)
@database.run_in_session()
@utils.wrap_to_dict(RESP_FIELDS)
def update_report(cluster_id, name, user=None, session=None, **kwargs):
    """Update health check report."""
    cluster = cluster_api.get_cluster(cluster_id, user=user, session=session)
    report = utils.get_db_object(
        session, models.HealthCheckReport, cluster_id=cluster['id'], name=name
    )
    if report.state == 'finished':
        err_msg = 'Report cannot be updated if state is in "finished"'
        raise exception.Forbidden(err_msg)

    return utils.update_db_object(session, report, **kwargs)


@utils.supported_filters(UPDATE_FIELDS)
@database.run_in_session()
@utils.wrap_to_dict(RESP_FIELDS)
def update_multi_reports(cluster_id, user=None, session=None, **kwargs):
    """Bulk update reports."""
    return set_error(cluster_id, session=session, **kwargs)


def set_error(cluster_id, report={}, session=None,
              state='error', error_message=None):
    cluster = cluster_api.get_cluster(cluster_id, session=session)
    logging.debug(
        "updates all reports as %s in cluster %s",
        state, cluster_id
    )
    reports = utils.list_db_objects(
        session, models.HealthCheckReport, cluster_id=cluster['id']
    )
    for report in reports:
        utils.update_db_object(
            session, report, report={},
            state='error', error_message=error_message
        )

    return reports


@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_HEALTH_REPORT
)
@utils.wrap_to_dict(RESP_FIELDS)
def list_health_reports(cluster_id, user=None, session=None):
    """List all reports in the specified cluster."""
    cluster = cluster_api.get_cluster(cluster_id, user=user, session=session)
    return utils.list_db_objects(
        session, models.HealthCheckReport, cluster_id=cluster['id']
    )


@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_GET_HEALTH_REPORT
)
@utils.wrap_to_dict(RESP_FIELDS)
def get_health_report(cluster_id, name, user=None, session=None):
    cluster = cluster_api.get_cluster(cluster_id, user=user, session=session)
    return utils.get_db_object(
        session, models.HealthCheckReport, cluster_id=cluster['id'], name=name
    )


@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_DELETE_REPORT
)
@utils.wrap_to_dict(RESP_FIELDS)
def delete_reports(cluster_id, name=None, user=None, session=None):
    cluster = cluster_api.get_cluster(cluster_id)
    if name:
        report = utils.get_db_object(
            session, models.HealthCheckReport,
            cluster_id=cluster['id'], name=name
        )
        return utils.del_db_object(session, report)

    return utils.del_db_objects(
        session, models.HealthCheckReport, cluster_id=cluster_id
    )


@utils.supported_filters(optional_support_keys=['check_health'])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_CHECK_CLUSTER_HEALTH
)
@utils.wrap_to_dict(RESP_ACTION_FIELDS)
def start_check_cluster_health(cluster_id, send_report_url,
                               user=None, session=None, check_health={}):
    """Start to check cluster health."""
    cluster = cluster_api.get_cluster(cluster_id, user=user, session=session)
    cluster_state = utils.get_db_object(
        session, models.Cluster, id=cluster['id']
    ).state_dict()

    if cluster_state['state'] != 'SUCCESSFUL':
        logging.debug("state is %s" % cluster_state['state'])
        err_msg = "Healthcheck starts only after cluster finished deployment!"
        raise exception.Forbidden(err_msg)

    reports = utils.list_db_objects(
        session, models.HealthCheckReport,
        cluster_id=cluster['id'], state='verifying'
    )
    if reports:
        err_msg = 'Healthcheck in progress, please wait for it to complete!'
        raise exception.Forbidden(err_msg)

    # Clear all preivous report
    utils.del_db_objects(
        session, models.HealthCheckReport, cluster_id=cluster['id']
    )

    from compass.tasks import client as celery_client
    celery_client.celery.send_task(
        'compass.tasks.cluster_health',
        (cluster['id'], send_report_url, user.email)
    )
    return {
        "cluster_id": cluster['id'],
        "status": "start to check cluster health."
    }
