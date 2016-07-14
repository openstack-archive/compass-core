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

"""Cluster database operations."""
import copy
import functools
import logging
import re

from compass.db.api import adapter_holder as adapter_api
from compass.db.api import database
from compass.db.api import metadata_holder as metadata_api
from compass.db.api import permission
from compass.db.api import user as user_api
from compass.db.api import utils
from compass.db import exception
from compass.db import models
from compass.utils import util


SUPPORTED_FIELDS = [
    'name', 'os_name', 'owner',
    'adapter_name', 'flavor_name'
]
SUPPORTED_CLUSTERHOST_FIELDS = []
RESP_FIELDS = [
    'id', 'name', 'os_name', 'os_id', 'adapter_id', 'flavor_id',
    'reinstall_distributed_system', 'flavor',
    'distributed_system_installed',
    'owner', 'adapter_name', 'flavor_name',
    'created_at', 'updated_at'
]
RESP_CLUSTERHOST_FIELDS = [
    'id', 'host_id', 'clusterhost_id', 'machine_id',
    'name', 'hostname', 'roles', 'os_installer',
    'cluster_id', 'clustername', 'location', 'tag',
    'networks', 'mac', 'switch_ip', 'port', 'switches',
    'os_installed', 'distributed_system_installed',
    'os_name', 'os_id', 'ip',
    'reinstall_os', 'reinstall_distributed_system',
    'owner', 'cluster_id',
    'created_at', 'updated_at',
    'patched_roles'
]
RESP_CONFIG_FIELDS = [
    'os_config',
    'package_config',
    'config_step',
    'config_validated',
    'created_at',
    'updated_at'
]
RESP_DEPLOYED_CONFIG_FIELDS = [
    'deployed_os_config',
    'deployed_package_config',
    'created_at',
    'updated_at'
]
RESP_METADATA_FIELDS = [
    'os_config', 'package_config'
]
RESP_CLUSTERHOST_CONFIG_FIELDS = [
    'package_config',
    'os_config',
    'config_step',
    'config_validated',
    'networks',
    'created_at',
    'updated_at'
]
RESP_CLUSTERHOST_DEPLOYED_CONFIG_FIELDS = [
    'deployed_os_config',
    'deployed_package_config',
    'created_at',
    'updated_at'
]
RESP_STATE_FIELDS = [
    'id', 'state', 'percentage', 'message', 'severity',
    'status', 'ready',
    'created_at', 'updated_at'
]
RESP_CLUSTERHOST_STATE_FIELDS = [
    'id', 'state', 'percentage', 'message', 'severity',
    'ready', 'created_at', 'updated_at'
]
RESP_REVIEW_FIELDS = [
    'cluster', 'hosts'
]
RESP_DEPLOY_FIELDS = [
    'status', 'cluster', 'hosts'
]
IGNORE_FIELDS = ['id', 'created_at', 'updated_at']
ADDED_FIELDS = ['name', 'adapter_id', 'os_id']
OPTIONAL_ADDED_FIELDS = ['flavor_id']
UPDATED_FIELDS = ['name', 'reinstall_distributed_system']
ADDED_HOST_FIELDS = ['machine_id']
UPDATED_HOST_FIELDS = ['name', 'reinstall_os']
UPDATED_CLUSTERHOST_FIELDS = ['roles', 'patched_roles']
PATCHED_CLUSTERHOST_FIELDS = ['patched_roles']
UPDATED_CONFIG_FIELDS = [
    'put_os_config', 'put_package_config', 'config_step'
]
UPDATED_DEPLOYED_CONFIG_FIELDS = [
    'deployed_os_config', 'deployed_package_config'
]
PATCHED_CONFIG_FIELDS = [
    'patched_os_config', 'patched_package_config', 'config_step'
]
UPDATED_CLUSTERHOST_CONFIG_FIELDS = [
    'put_os_config',
    'put_package_config'
]
PATCHED_CLUSTERHOST_CONFIG_FIELDS = [
    'patched_os_config',
    'patched_package_config'
]
UPDATED_CLUSTERHOST_DEPLOYED_CONFIG_FIELDS = [
    'deployed_os_config',
    'deployed_package_config'
]
UPDATED_CLUSTERHOST_STATE_FIELDS = [
    'state', 'percentage', 'message', 'severity'
]
UPDATED_CLUSTERHOST_STATE_INTERNAL_FIELDS = [
    'ready'
]
UPDATED_CLUSTER_STATE_FIELDS = ['state']
IGNORE_UPDATED_CLUSTER_STATE_FIELDS = ['percentage', 'message', 'severity']
UPDATED_CLUSTER_STATE_INTERNAL_FIELDS = ['ready']
RESP_CLUSTERHOST_LOG_FIELDS = [
    'clusterhost_id', 'id', 'host_id', 'cluster_id',
    'filename', 'position', 'partial_line',
    'percentage',
    'message', 'severity', 'line_matcher_name'
]
ADDED_CLUSTERHOST_LOG_FIELDS = [
    'filename'
]
UPDATED_CLUSTERHOST_LOG_FIELDS = [
    'position', 'partial_line', 'percentage',
    'message', 'severity', 'line_matcher_name'
]


@utils.supported_filters(optional_support_keys=SUPPORTED_FIELDS)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_CLUSTERS
)
@utils.wrap_to_dict(RESP_FIELDS)
def list_clusters(user=None, session=None, **filters):
    """List clusters."""
    clusters = utils.list_db_objects(
        session, models.Cluster, **filters
    )
    logging.info('user is %s', user.email)
    if not user.is_admin and len(clusters):
        clusters = [c for c in clusters if c.owner == user.email]
    return clusters


def _get_cluster(cluster_id, session=None, **kwargs):
    """Get cluster by id."""
    if isinstance(cluster_id, (int, long)):
        return utils.get_db_object(
            session, models.Cluster, id=cluster_id, **kwargs
        )
    raise exception.InvalidParameter(
        'cluster id %s type is not int compatible' % cluster_id
    )


def get_cluster_internal(cluster_id, session=None, **kwargs):
    """Helper function to get cluster.

    Should be only used by other files under db/api.
    """
    return _get_cluster(cluster_id, session=session, **kwargs)


def _get_cluster_host(
    cluster_id, host_id, session=None, **kwargs
):
    """Get clusterhost by cluster id and host id."""
    cluster = _get_cluster(cluster_id, session=session, **kwargs)
    from compass.db.api import host as host_api
    host = host_api.get_host_internal(host_id, session=session, **kwargs)
    return utils.get_db_object(
        session, models.ClusterHost,
        cluster_id=cluster.id,
        host_id=host.id,
        **kwargs
    )


def _get_clusterhost(clusterhost_id, session=None, **kwargs):
    """Get clusterhost by clusterhost id."""
    if isinstance(clusterhost_id, (int, long)):
        return utils.get_db_object(
            session, models.ClusterHost,
            clusterhost_id=clusterhost_id,
            **kwargs
        )
    raise exception.InvalidParameter(
        'clusterhost id %s type is not int compatible' % clusterhost_id
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_CLUSTERS
)
@utils.wrap_to_dict(RESP_FIELDS)
def get_cluster(
    cluster_id, exception_when_missing=True,
    user=None, session=None, **kwargs
):
    """Get cluster info."""
    return _get_cluster(
        cluster_id,
        session=session,
        exception_when_missing=exception_when_missing
    )


@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_CLUSTERS)
def is_cluster_os_ready(
    cluster_id, exception_when_missing=True,
    user=None, session=None, **kwargs
):
    cluster = utils.get_db_object(
        session, models.Cluster, exception_when_missing, id=cluster_id)

    all_states = ([i.host.state.ready for i in cluster.clusterhosts])

    logging.info("is_cluster_os_ready: all_states %s" % all_states)

    return all(all_states)


def check_cluster_validated(cluster):
    """Check cluster is validated."""
    if not cluster.config_validated:
        raise exception.Forbidden(
            'cluster %s is not validated' % cluster.name
        )


def check_clusterhost_validated(clusterhost):
    """Check clusterhost is validated."""
    if not clusterhost.config_validated:
        raise exception.Forbidden(
            'clusterhost %s is not validated' % clusterhost.name
        )


def check_cluster_editable(
    cluster, user=None,
    check_in_installing=False
):
    """Check if cluster is editable.

    If we try to set cluster
    reinstall_distributed_system attribute or any
    checking to make sure the cluster is not in installing state,
    we can set check_in_installing to True.
    Otherwise we will make sure the cluster is not in deploying or
    deployed.
    If user is not admin or not the owner of the cluster, the check
    will fail to make sure he can not update the cluster attributes.
    """
    if check_in_installing:
        if cluster.state.state == 'INSTALLING':
            raise exception.Forbidden(
                'cluster %s is not editable '
                'when state is installing' % cluster.name
            )
#    elif (
#        cluster.flavor_name and
#        not cluster.reinstall_distributed_system
#    ):
#        raise exception.Forbidden(
#            'cluster %s is not editable '
#            'when not to be reinstalled' % cluster.name
#        )
    if user and not user.is_admin and cluster.creator_id != user.id:
        raise exception.Forbidden(
            'cluster %s is not editable '
            'when user is not admin or cluster owner' % cluster.name
        )


def is_cluster_editable(
    cluster, user=None,
    check_in_installing=False
):
    """Get if cluster is editble."""
    try:
        check_cluster_editable(
            cluster, user=user,
            check_in_installing=check_in_installing
        )
        return True
    except exception.Forbidden:
        return False


@utils.supported_filters(
    ADDED_FIELDS,
    optional_support_keys=OPTIONAL_ADDED_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(name=utils.check_name)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_CLUSTER
)
@utils.wrap_to_dict(RESP_FIELDS)
def add_cluster(
    exception_when_existing=True,
    name=None, adapter_id=None, flavor_id=None,
    user=None, session=None, **kwargs
):
    """Create a cluster."""
    adapter = adapter_api.get_adapter(
        adapter_id, user=user, session=session
    )
    # if flavor_id is not None, also set flavor field.
    # In future maybe we can move the use of flavor from
    # models.py to db/api and explictly get flavor when
    # needed instead of setting flavor into cluster record.
    flavor = {}
    if flavor_id:
        flavor = adapter_api.get_flavor(
            flavor_id,
            user=user, session=session
        )
        if flavor['adapter_id'] != adapter['id']:
            raise exception.InvalidParameter(
                'flavor %s is not of adapter %s' % (
                    flavor_id, adapter_id
                )
            )

    cluster = utils.add_db_object(
        session, models.Cluster, exception_when_existing,
        name, user.id, adapter_id=adapter_id,
        flavor_id=flavor_id, flavor=flavor, **kwargs
    )
    return cluster


@utils.supported_filters(
    optional_support_keys=UPDATED_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(name=utils.check_name)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_CLUSTER
)
@utils.wrap_to_dict(RESP_FIELDS)
def update_cluster(cluster_id, user=None, session=None, **kwargs):
    """Update a cluster."""
    cluster = _get_cluster(
        cluster_id, session=session
    )
    check_cluster_editable(
        cluster, user=user,
        check_in_installing=(
            kwargs.get('reinstall_distributed_system', False)
        )
    )
    return utils.update_db_object(session, cluster, **kwargs)


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_DEL_CLUSTER
)
@utils.wrap_to_dict(
    RESP_FIELDS + ['status', 'cluster', 'hosts'],
    cluster=RESP_FIELDS,
    hosts=RESP_CLUSTERHOST_FIELDS
)
def del_cluster(
    cluster_id, force=False, from_database_only=False,
    delete_underlying_host=False, user=None, session=None, **kwargs
):
    """Delete a cluster.

    If force, the cluster will be deleted anyway. It is used by cli to
    force clean a cluster in any case.
    If from_database_only, the cluster recored will only be removed from
    database. Otherwise, a del task is sent to celery to do clean deletion.
    If delete_underlying_host, all hosts under this cluster will also be
    deleted.
    The backend will call del_cluster again with from_database_only set
    when it has done the deletion work on os installer/package installer.
    """
    cluster = _get_cluster(
        cluster_id, session=session
    )
    logging.debug(
        'delete cluster %s with force=%s '
        'from_database_only=%s delete_underlying_host=%s',
        cluster.id, force, from_database_only, delete_underlying_host
    )
    # force set cluster state to ERROR and the state of any clusterhost
    # in the cluster to ERROR when we want to delete the cluster anyway
    # even the cluster is in installing or already installed.
    # It let the api know the deleting is in doing when backend is doing
    # the real deleting.
    # In future we may import a new state like INDELETE to indicate
    # the deleting is processing.
    # We need discuss about if we can delete a cluster when it is already
    # installed by api.
    for clusterhost in cluster.clusterhosts:
        if clusterhost.state.state != 'UNINITIALIZED' and force:
            clusterhost.state.state = 'ERROR'
        if delete_underlying_host:
            host = clusterhost.host
            if host.state.state != 'UNINITIALIZED' and force:
                host.state.state = 'ERROR'
    if cluster.state.state != 'UNINITIALIZED' and force:
        cluster.state.state = 'ERROR'

    check_cluster_editable(
        cluster, user=user,
        check_in_installing=True
    )

    # delete underlying host if delete_underlying_host is set.
    if delete_underlying_host:
        for clusterhost in cluster.clusterhosts:
            # delete underlying host only user has permission.
            from compass.db.api import host as host_api
            host = clusterhost.host
            if host_api.is_host_editable(
                host, user=user, check_in_installing=True
            ):
                # Delete host record directly in database when there is no need
                # to do the deletion in backend or from_database_only is set.
                if host.state.state == 'UNINITIALIZED' or from_database_only:
                    utils.del_db_object(
                        session, host
                    )

    # Delete cluster record directly in database when there
    # is no need to do the deletion in backend or from_database_only is set.
    if cluster.state.state == 'UNINITIALIZED' or from_database_only:
        return utils.del_db_object(
            session, cluster
        )
    else:
        from compass.tasks import client as celery_client
        logging.info('send del cluster %s task to celery', cluster_id)
        celery_client.celery.send_task(
            'compass.tasks.delete_cluster',
            (
                user.email, cluster.id,
                [
                    clusterhost.host_id
                    for clusterhost in cluster.clusterhosts
                ],
                delete_underlying_host
            ),
            queue=user.email,
            exchange=user.email,
            routing_key=user.email
        )
        return {
            'status': 'delete action is sent',
            'cluster': cluster,
            'hosts': cluster.clusterhosts
        }


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_CLUSTER_CONFIG
)
@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
def get_cluster_config(cluster_id, user=None, session=None, **kwargs):
    """Get cluster config."""
    return _get_cluster(cluster_id, session=session)


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_CLUSTER_CONFIG
)
@utils.wrap_to_dict(RESP_DEPLOYED_CONFIG_FIELDS)
def get_cluster_deployed_config(cluster_id, user=None, session=None, **kwargs):
    """Get cluster deployed config."""
    return _get_cluster(cluster_id, session=session)


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_METADATAS
)
@utils.wrap_to_dict(RESP_METADATA_FIELDS)
def get_cluster_metadata(cluster_id, user=None, session=None, **kwargs):
    """Get cluster metadata.

    If no flavor in the cluster, it means this is a os only cluster.
    We ignore package metadata for os only cluster.
    """
    cluster = _get_cluster(cluster_id, session=session)
    metadatas = {}
    os_name = cluster.os_name
    if os_name:
        metadatas.update(
            metadata_api.get_os_metadata(
                os_name, session=session
            )
        )
    flavor_id = cluster.flavor_id
    if flavor_id:
        metadatas.update(
            metadata_api.get_flavor_metadata(
                flavor_id,
                user=user, session=session
            )
        )

    return metadatas


def _cluster_os_config_validates(
    config, cluster, session=None, user=None, **kwargs
):
    """Check cluster os config validation."""
    metadata_api.validate_os_config(
        config, cluster.os_id
    )


def _cluster_package_config_validates(
    config, cluster, session=None, user=None, **kwargs
):
    """Check cluster package config validation."""
    metadata_api.validate_flavor_config(
        config, cluster.flavor_id
    )


@utils.input_validates_with_args(
    put_os_config=_cluster_os_config_validates,
    put_package_config=_cluster_package_config_validates
)
@utils.output_validates_with_args(
    os_config=_cluster_os_config_validates,
    package_config=_cluster_package_config_validates
)
@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
def _update_cluster_config(cluster, session=None, user=None, **kwargs):
    """Update a cluster config."""
    check_cluster_editable(cluster, user=user)
    return utils.update_db_object(
        session, cluster, **kwargs
    )


# replace os_config to deployed_os_config,
# package_config to deployed_package_config
@utils.replace_filters(
    os_config='deployed_os_config',
    package_config='deployed_package_config'
)
@utils.supported_filters(
    optional_support_keys=UPDATED_DEPLOYED_CONFIG_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_CLUSTER_CONFIG
)
@utils.wrap_to_dict(RESP_DEPLOYED_CONFIG_FIELDS)
def update_cluster_deployed_config(
    cluster_id, user=None, session=None, **kwargs
):
    """Update cluster deployed config."""
    cluster = _get_cluster(cluster_id, session=session)
    check_cluster_editable(cluster, user=user)
    check_cluster_validated(cluster)
    return utils.update_db_object(
        session, cluster, **kwargs
    )


# replace os_config to put_os_config,
# package_config to put_package_config in kwargs.
# It tells db these fields will be updated not patched.
@utils.replace_filters(
    os_config='put_os_config',
    package_config='put_package_config'
)
@utils.supported_filters(
    optional_support_keys=UPDATED_CONFIG_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_CLUSTER_CONFIG
)
def update_cluster_config(cluster_id, user=None, session=None, **kwargs):
    """Update cluster config."""
    cluster = _get_cluster(cluster_id, session=session)
    return _update_cluster_config(
        cluster, session=session, user=user, **kwargs
    )


# replace os_config to patched_os_config and
# package_config to patched_package_config in kwargs.
# It tells db these fields will be patched not updated.
@utils.replace_filters(
    os_config='patched_os_config',
    package_config='patched_package_config'
)
@utils.supported_filters(
    optional_support_keys=PATCHED_CONFIG_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_CLUSTER_CONFIG
)
def patch_cluster_config(cluster_id, user=None, session=None, **kwargs):
    """patch cluster config."""
    cluster = _get_cluster(cluster_id, session=session)
    return _update_cluster_config(
        cluster, session=session, user=user, **kwargs
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_DEL_CLUSTER_CONFIG
)
@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
def del_cluster_config(cluster_id, user=None, session=None):
    """Delete a cluster config."""
    cluster = _get_cluster(
        cluster_id, session=session
    )
    check_cluster_editable(cluster, user=user)
    return utils.update_db_object(
        session, cluster, os_config={},
        package_config={}, config_validated=False
    )


def _roles_validates(roles, cluster, session=None, user=None):
    """Check roles is validated to a cluster's roles."""
    if roles:
        if not cluster.flavor_name:
            raise exception.InvalidParameter(
                'not flavor in cluster %s' % cluster.name
            )
        cluster_roles = [role['name'] for role in cluster.flavor['roles']]
        for role in roles:
            if role not in cluster_roles:
                raise exception.InvalidParameter(
                    'role %s is not in cluster roles %s' % (
                        role, cluster_roles
                    )
                )


def _cluster_host_roles_validates(
    value, cluster, host, session=None, user=None, **kwargs
):
    """Check clusterhost roles is validated by cluster and host."""
    _roles_validates(value, cluster, session=session, user=user)


def _clusterhost_roles_validates(
    value, clusterhost, session=None, user=None, **kwargs
):
    """Check clusterhost roles is validated by clusterhost."""
    _roles_validates(
        value, clusterhost.cluster, session=session, user=user
    )


@utils.supported_filters(
    optional_support_keys=UPDATED_HOST_FIELDS,
    ignore_support_keys=UPDATED_CLUSTERHOST_FIELDS
)
@utils.input_validates(name=utils.check_name)
def _add_host_if_not_exist(
    machine_id, cluster, session=None, user=None, **kwargs
):
    """Add underlying host if it does not exist."""
    from compass.db.api import host as host_api
    host = host_api.get_host_internal(
        machine_id, session=session, exception_when_missing=False
    )
    if host:
        if kwargs:
            # ignore update underlying host if host is not editable.
            from compass.db.api import host as host_api
            if host_api.is_host_editable(
                host, user=cluster.creator,
                check_in_installing=kwargs.get('reinstall_os', False),
            ):
                utils.update_db_object(
                    session, host,
                    **kwargs
                )
            else:
                logging.debug(
                    'ignore update host host %s '
                    'since it is not editable' % host.name
                )
        else:
            logging.debug('nothing to update for host %s', host.name)
    else:
        from compass.db.api import adapter_holder as adapter_api
        adapter = adapter_api.get_adapter(
            cluster.adapter_name, user=user, session=session
        )
        host = utils.add_db_object(
            session, models.Host, False, machine_id,
            os_name=cluster.os_name,
            os_installer=adapter['os_installer'],
            creator=cluster.creator,
            **kwargs
        )
    return host


@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTERHOST_FIELDS,
    ignore_support_keys=UPDATED_HOST_FIELDS
)
@utils.input_validates_with_args(
    roles=_cluster_host_roles_validates
)
def _add_clusterhost_only(
    cluster, host,
    exception_when_existing=False,
    session=None, user=None,
    **kwargs
):
    """Get clusterhost only."""
    if not cluster.state.state == "UNINITIALIZED":
        cluster.state.ready = False
        cluster.state.state = "UNINITIALIZED"
        cluster.state.percentage = 0.0
        utils.update_db_object(session, cluster.state, state="UNINITIALIZED")

    return utils.add_db_object(
        session, models.ClusterHost, exception_when_existing,
        cluster.id, host.id, **kwargs
    )


@utils.supported_filters(
    ADDED_HOST_FIELDS,
    optional_support_keys=UPDATED_HOST_FIELDS + UPDATED_CLUSTERHOST_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
def _add_clusterhost(
        cluster,
        exception_when_existing=False,
        session=None, user=None, machine_id=None, **kwargs
):
    """Add clusterhost and add underlying host if it does not exist."""
    host = _add_host_if_not_exist(
        machine_id, cluster, session=session,
        user=user, **kwargs
    )

    return _add_clusterhost_only(
        cluster, host, exception_when_existing=exception_when_existing,
        session=session, user=user, **kwargs
    )


def _add_clusterhosts(cluster, machines, session=None, user=None):
    """Add machines to cluster.

    Args:
       machines: list of dict which contains clusterost attr to update.

    Examples:
       [{'machine_id': 1, 'name': 'host1'}]
    """
    check_cluster_editable(
        cluster, user=user,
        check_in_installing=True
    )
    if cluster.state.state == 'SUCCESSFUL':
        cluster.state.state == 'UPDATE_PREPARING'
    for machine_dict in machines:
        _add_clusterhost(
            cluster, session=session, user=user, **machine_dict
        )


def _remove_clusterhosts(cluster, hosts, session=None, user=None):
    """Remove hosts from cluster.

    Args:
       hosts: list of host id.
    """
    check_cluster_editable(
        cluster, user=user,
        check_in_installing=True
    )
    utils.del_db_objects(
        session, models.ClusterHost,
        cluster_id=cluster.id, host_id=hosts
    )


def _set_clusterhosts(cluster, machines, session=None, user=None):
    """set machines to cluster.

    Args:
       machines: list of dict which contains clusterost attr to update.

    Examples:
       [{'machine_id': 1, 'name': 'host1'}]
    """
    check_cluster_editable(
        cluster, user=user,
        check_in_installing=True
    )
    utils.del_db_objects(
        session, models.ClusterHost,
        cluster_id=cluster.id
    )
    if cluster.state.state == 'SUCCESSFUL':
        cluster.state.state = 'UPDATE_PREPARING'
    for machine_dict in machines:
        _add_clusterhost(
            cluster, True, session=session, user=user, **machine_dict
        )


@utils.supported_filters(optional_support_keys=SUPPORTED_CLUSTERHOST_FIELDS)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_CLUSTERHOSTS
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_FIELDS)
def list_cluster_hosts(cluster_id, user=None, session=None, **filters):
    """List clusterhosts of a cluster."""
    cluster = _get_cluster(cluster_id, session=session)
    return utils.list_db_objects(
        session, models.ClusterHost, cluster_id=cluster.id,
        **filters
    )


@utils.supported_filters(optional_support_keys=SUPPORTED_CLUSTERHOST_FIELDS)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_CLUSTERHOSTS
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_FIELDS)
def list_clusterhosts(user=None, session=None, **filters):
    """List all clusterhosts."""
    return utils.list_db_objects(
        session, models.ClusterHost, **filters
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_CLUSTERHOSTS
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_FIELDS)
def get_cluster_host(
    cluster_id, host_id, exception_when_missing=True,
    user=None, session=None, **kwargs
):
    """Get clusterhost info by cluster id and host id."""
    return _get_cluster_host(
        cluster_id, host_id, session=session,
        exception_when_missing=exception_when_missing,
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_CLUSTERHOSTS
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_FIELDS)
def get_clusterhost(
    clusterhost_id, exception_when_missing=True,
    user=None, session=None, **kwargs
):
    """Get clusterhost info by clusterhost id."""
    return _get_clusterhost(
        clusterhost_id, session=session,
        exception_when_missing=exception_when_missing,
        user=user
    )


@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_UPDATE_CLUSTER_HOSTS
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_FIELDS)
def add_cluster_host(
    cluster_id, exception_when_existing=True,
    user=None, session=None, **kwargs
):
    """Add a host to a cluster."""
    cluster = _get_cluster(cluster_id, session=session)
    check_cluster_editable(
        cluster, user=user,
        check_in_installing=True
    )
    if cluster.state.state == 'SUCCESSFUL':
        cluster.state.state = 'UPDATE_PREPARING'
    return _add_clusterhost(
        cluster, exception_when_existing,
        session=session, user=user, **kwargs
    )


@utils.supported_filters(
    optional_support_keys=UPDATED_HOST_FIELDS,
    ignore_support_keys=(
        UPDATED_CLUSTERHOST_FIELDS +
        PATCHED_CLUSTERHOST_FIELDS
    )
)
def _update_host_if_necessary(
    clusterhost, session=None, user=None, **kwargs
):
    """Update underlying host if there is something to update."""
    host = clusterhost.host
    if kwargs:
        # ignore update underlying host if the host is not editable.
        from compass.db.api import host as host_api
        if host_api.is_host_editable(
            host, user=clusterhost.cluster.creator,
            check_in_installing=kwargs.get('reinstall_os', False),
        ):
            utils.update_db_object(
                session, host,
                **kwargs
            )
        else:
            logging.debug(
                'ignore update host %s since it is not editable' % host.name
            )
    else:
        logging.debug(
            'nothing to update for host %s', host.name
        )
    return host


@utils.supported_filters(
    optional_support_keys=(
        UPDATED_CLUSTERHOST_FIELDS +
        PATCHED_CLUSTERHOST_FIELDS
    ),
    ignore_support_keys=UPDATED_HOST_FIELDS
)
@utils.input_validates_with_args(
    roles=_clusterhost_roles_validates,
    patched_roles=_clusterhost_roles_validates
)
def _update_clusterhost_only(
    clusterhost, session=None, user=None, **kwargs
):
    """Update clusterhost only."""
    check_cluster_editable(clusterhost.cluster, user=user)
    return utils.update_db_object(
        session, clusterhost, **kwargs
    )


@utils.wrap_to_dict(RESP_CLUSTERHOST_FIELDS)
def _update_clusterhost(clusterhost, session=None, user=None, **kwargs):
    """Update clusterhost and underlying host if necessary."""
    _update_host_if_necessary(
        clusterhost, session=session, user=user, **kwargs
    )
    return _update_clusterhost_only(
        clusterhost, session=session, user=user, **kwargs
    )


@utils.supported_filters(
    optional_support_keys=(UPDATED_HOST_FIELDS + UPDATED_CLUSTERHOST_FIELDS),
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_UPDATE_CLUSTER_HOSTS
)
def update_cluster_host(
    cluster_id, host_id, user=None,
    session=None, **kwargs
):
    """Update clusterhost by cluster id and host id."""
    logging.info('updating kwargs: %s', kwargs)
    clusterhost = _get_cluster_host(
        cluster_id, host_id, session=session
    )
    return _update_clusterhost(
        clusterhost, session=session, user=user, **kwargs
    )


@utils.supported_filters(
    optional_support_keys=(UPDATED_HOST_FIELDS + UPDATED_CLUSTERHOST_FIELDS),
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_UPDATE_CLUSTER_HOSTS
)
def update_clusterhost(
    clusterhost_id, user=None,
    session=None, **kwargs
):
    """Update clusterhost by clusterhost id."""
    clusterhost = _get_clusterhost(
        clusterhost_id, session=session
    )
    return _update_clusterhost(
        clusterhost, session=session, user=user, **kwargs
    )


# replace roles to patched_roles in kwargs.
# It tells db roles field will be patched.
@utils.replace_filters(
    roles='patched_roles'
)
@utils.supported_filters(
    optional_support_keys=PATCHED_CLUSTERHOST_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_UPDATE_CLUSTER_HOSTS
)
def patch_cluster_host(
    cluster_id, host_id, user=None,
    session=None, **kwargs
):
    """Patch clusterhost by cluster id and host id."""
    logging.info("kwargs are %s", kwargs)
    clusterhost = _get_cluster_host(
        cluster_id, host_id, session=session
    )
    updated_clusterhost = _update_clusterhost(
        clusterhost, session=session, user=user, **kwargs
    )
    return updated_clusterhost


# replace roles to patched_roles in kwargs.
# It tells db roles field will be patched.
@utils.replace_filters(
    roles='patched_roles'
)
@utils.supported_filters(
    optional_support_keys=PATCHED_CLUSTERHOST_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_UPDATE_CLUSTER_HOSTS
)
def patch_clusterhost(
    clusterhost_id, user=None, session=None,
    **kwargs
):
    """Patch clusterhost by clusterhost id."""
    clusterhost = _get_clusterhost(
        clusterhost_id, session=session
    )
    return _update_clusterhost(
        clusterhost, session=session, user=user, **kwargs
    )


@user_api.check_user_permission(
    permission.PERMISSION_DEL_CLUSTER_HOST
)
@utils.wrap_to_dict(
    RESP_CLUSTERHOST_FIELDS + ['status', 'host'],
    host=RESP_CLUSTERHOST_FIELDS
)
def _del_cluster_host(
    clusterhost,
    force=False, from_database_only=False,
    delete_underlying_host=False, user=None,
    session=None, **kwargs
):
    """delete clusterhost.

    If force, the cluster host will be deleted anyway.
    If from_database_only, the cluster host recored will only be
    deleted from database. Otherwise a celery task sent to do
    clean deletion.
    If delete_underlying_host, the underlying host will also be deleted.
    The backend will call _del_cluster_host again when the clusterhost is
    deleted from os installer/package installer with from_database_only
    set.
    """
    # force set clusterhost state to ERROR when we want to delete the
    # clusterhost anyway even the clusterhost is in installing or already
    # installed. It let the api know the deleting is in doing when backend
    # is doing the real deleting. In future we may import a new state like
    # INDELETE to indicate the deleting is processing.
    # We need discuss about if we can delete a clusterhost when it is already
    # installed by api.
    if clusterhost.state.state != 'UNINITIALIZED' and force:
        clusterhost.state.state = 'ERROR'
    if not force:
        check_cluster_editable(
            clusterhost.cluster, user=user,
            check_in_installing=True
        )
    # delete underlying host if delete_underlying_host is set.
    if delete_underlying_host:
        host = clusterhost.host
        if host.state.state != 'UNINITIALIZED' and force:
            host.state.state = 'ERROR'
        # only delete the host when user have the permission to delete it.
        import compass.db.api.host as host_api
        if host_api.is_host_editable(
            host, user=user,
            check_in_installing=True
        ):
            # if there is no need to do the deletion by backend or
            # from_database_only is set, we only delete the record
            # in database.
            if host.state.state == 'UNINITIALIZED' or from_database_only:
                utils.del_db_object(
                    session, host
                )

    # if there is no need to do the deletion by backend or
    # from_database_only is set, we only delete the record in database.
    if clusterhost.state.state == 'UNINITIALIZED' or from_database_only:
        return utils.del_db_object(
            session, clusterhost
        )
    else:
        logging.info(
            'send del cluster %s host %s task to celery',
            clusterhost.cluster_id, clusterhost.host_id
        )
        from compass.tasks import client as celery_client
        celery_client.celery.send_task(
            'compass.tasks.delete_cluster_host',
            (
                user.email, clusterhost.cluster_id, clusterhost.host_id,
                delete_underlying_host
            ),
            queue=user.email,
            exchange=user.email,
            routing_key=user.email
        )
        return {
            'status': 'delete action sent',
            'host': clusterhost,
        }


@utils.supported_filters([])
@database.run_in_session()
def del_cluster_host(
    cluster_id, host_id,
    force=False, from_database_only=False,
    delete_underlying_host=False, user=None,
    session=None, **kwargs
):
    """Delete clusterhost by cluster id and host id."""
    clusterhost = _get_cluster_host(
        cluster_id, host_id, session=session
    )
    return _del_cluster_host(
        clusterhost, force=force, from_database_only=from_database_only,
        delete_underlying_host=delete_underlying_host, user=user,
        session=session, **kwargs
    )


@utils.supported_filters([])
@database.run_in_session()
def del_clusterhost(
    clusterhost_id,
    force=False, from_database_only=False,
    delete_underlying_host=False, user=None,
    session=None, **kwargs
):
    """Delete clusterhost by clusterhost id."""
    clusterhost = _get_clusterhost(
        clusterhost_id, session=session
    )
    return _del_cluster_host(
        clusterhost, force=force, from_database_only=from_database_only,
        delete_underlying_host=delete_underlying_host, user=user,
        session=session, **kwargs
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_CLUSTERHOST_CONFIG
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_CONFIG_FIELDS)
def get_cluster_host_config(
        cluster_id, host_id, user=None,
        session=None, **kwargs
):
    """Get clusterhost config by cluster id and host id."""
    return _get_cluster_host(
        cluster_id, host_id, session=session
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_CLUSTERHOST_CONFIG
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_DEPLOYED_CONFIG_FIELDS)
def get_cluster_host_deployed_config(
    cluster_id, host_id, user=None, session=None, **kwargs
):
    """Get clusterhost deployed config by cluster id and host id."""
    return _get_cluster_host(
        cluster_id, host_id, session=session
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_CLUSTERHOST_CONFIG
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_CONFIG_FIELDS)
def get_clusterhost_config(clusterhost_id, user=None, session=None, **kwargs):
    """Get clusterhost config by clusterhost id."""
    return _get_clusterhost(
        clusterhost_id, session=session
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_CLUSTERHOST_CONFIG
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_DEPLOYED_CONFIG_FIELDS)
def get_clusterhost_deployed_config(
    clusterhost_id, user=None,
    session=None, **kwargs
):
    """Get clusterhost deployed config by clusterhost id."""
    return _get_clusterhost(
        clusterhost_id, session=session
    )


def _clusterhost_os_config_validates(
    config, clusterhost, session=None, user=None, **kwargs
):
    """Validate clusterhost's underlying host os config."""
    from compass.db.api import host as host_api
    host = clusterhost.host
    host_api.check_host_editable(host, user=user)
    metadata_api.validate_os_config(
        config, host.os_id
    )


def _clusterhost_package_config_validates(
    config, clusterhost, session=None, user=None, **kwargs
):
    """Validate clusterhost's cluster package config."""
    cluster = clusterhost.cluster
    check_cluster_editable(cluster, user=user)
    metadata_api.validate_flavor_config(
        config, cluster.flavor_id
    )


def _filter_clusterhost_host_editable(
    config, clusterhost, session=None, user=None, **kwargs
):
    """Filter fields if the underlying host is not editable."""
    from compass.db.api import host as host_api
    host = clusterhost.host
    return host_api.is_host_editable(host, user=user)


@utils.input_filters(
    put_os_config=_filter_clusterhost_host_editable,
    patched_os_config=_filter_clusterhost_host_editable
)
@utils.input_validates_with_args(
    put_os_config=_clusterhost_os_config_validates,
    put_package_config=_clusterhost_package_config_validates
)
@utils.output_validates_with_args(
    os_config=_clusterhost_os_config_validates,
    package_config=_clusterhost_package_config_validates
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_CONFIG_FIELDS)
def _update_clusterhost_config(clusterhost, session=None, user=None, **kwargs):
    """Update clusterhost config."""
    return utils.update_db_object(
        session, clusterhost, **kwargs
    )


def _clusterhost_host_validated(
    config, clusterhost, session=None, user=None, **kwargs
):
    """Check clusterhost's underlying host is validated."""
    from compass.db.api import host as host_api
    host = clusterhost.host
    host_api.check_host_editable(host, user=user)
    host_api.check_host_validated(host)


def _clusterhost_cluster_validated(
    config, clusterhost, session=None, user=None, **kwargs
):
    """Check clusterhost's cluster is validated."""
    cluster = clusterhost.cluster
    check_cluster_editable(cluster, user=user)
    check_clusterhost_validated(clusterhost)


@utils.input_filters(
    deployed_os_config=_filter_clusterhost_host_editable,
)
@utils.input_validates_with_args(
    deployed_os_config=_clusterhost_host_validated,
    deployed_package_config=_clusterhost_cluster_validated
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_DEPLOYED_CONFIG_FIELDS)
def _update_clusterhost_deployed_config(
    clusterhost, session=None, user=None, **kwargs
):
    """Update clusterhost deployed config."""
    return utils.update_db_object(
        session, clusterhost, **kwargs
    )


# replace os_config to put_os_config and
# package_config to put_package_config in kwargs.
# It tells db these fields will be updated not patched.
@utils.replace_filters(
    os_config='put_os_config',
    package_config='put_package_config'
)
@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTERHOST_CONFIG_FIELDS,
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_CLUSTERHOST_CONFIG
)
def update_cluster_host_config(
    cluster_id, host_id, user=None, session=None, **kwargs
):
    """Update clusterhost config by cluster id and host id."""
    clusterhost = _get_cluster_host(
        cluster_id, host_id, session=session
    )
    return _update_clusterhost_config(
        clusterhost, user=user, session=session, **kwargs
    )


# replace os_config to deployed_os_config and
# package_config to deployed_package_config in kwargs.
@utils.replace_filters(
    os_config='deployed_os_config',
    package_config='deployed_package_config'
)
@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTERHOST_DEPLOYED_CONFIG_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_CLUSTERHOST_CONFIG
)
def update_cluster_host_deployed_config(
    cluster_id, host_id, user=None, session=None, **kwargs
):
    """Update clusterhost deployed config by cluster id and host id."""
    clusterhost = _get_cluster_host(
        cluster_id, host_id, session=session
    )
    return _update_clusterhost_deployed_config(
        clusterhost, session=session, user=user, **kwargs
    )


# replace os_config to put_os_config and
# package_config to put_package_config in kwargs.
# It tells db these fields will be updated not patched.
@utils.replace_filters(
    os_config='put_os_config',
    package_config='put_package_config'
)
@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTERHOST_CONFIG_FIELDS,
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_CLUSTERHOST_CONFIG
)
def update_clusterhost_config(
    clusterhost_id, user=None, session=None, **kwargs
):
    """Update clusterhost config by clusterhost id."""
    clusterhost = _get_clusterhost(
        clusterhost_id, session=session
    )
    return _update_clusterhost_config(
        clusterhost, session=session, user=user, **kwargs
    )


# replace os_config to deployed_os_config and
# package_config to deployed_package_config in kwargs.
@utils.replace_filters(
    os_config='deployed_os_config',
    package_config='deployed_package_config'
)
@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTERHOST_DEPLOYED_CONFIG_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_CLUSTERHOST_CONFIG
)
def update_clusterhost_deployed_config(
    clusterhost_id, user=None, session=None, **kwargs
):
    """Update clusterhost deployed config by clusterhost id."""
    clusterhost = _get_clusterhost(
        clusterhost_id, session=session
    )
    return _update_clusterhost_deployed_config(
        clusterhost, session=session, user=user, **kwargs
    )


# replace os_config to patched_os_config and
# package_config to patched_package_config in kwargs
# It tells db these fields will be patched not updated.
@utils.replace_filters(
    os_config='patched_os_config',
    package_config='patched_package_config'
)
@utils.supported_filters(
    optional_support_keys=PATCHED_CLUSTERHOST_CONFIG_FIELDS,
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_CLUSTERHOST_CONFIG
)
def patch_cluster_host_config(
    cluster_id, host_id, user=None, session=None, **kwargs
):
    """patch clusterhost config by cluster id and host id."""
    clusterhost = _get_cluster_host(
        cluster_id, host_id, session=session
    )
    return _update_clusterhost_config(
        clusterhost, session=session, user=user, **kwargs
    )


# replace os_config to patched_os_config and
# package_config to patched_package_config in kwargs
# It tells db these fields will be patched not updated.
@utils.replace_filters(
    os_config='patched_os_config',
    package_config='patched_package_config'
)
@utils.supported_filters(
    optional_support_keys=PATCHED_CLUSTERHOST_CONFIG_FIELDS,
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_CLUSTERHOST_CONFIG
)
def patch_clusterhost_config(
    clusterhost_id, user=None, session=None, **kwargs
):
    """patch clusterhost config by clusterhost id."""
    clusterhost = _get_clusterhost(
        clusterhost_id, session=session
    )
    return _update_clusterhost_config(
        clusterhost, session=session, user=user, **kwargs
    )


def _clusterhost_host_editable(
    config, clusterhost, session=None, user=None, **kwargs
):
    """Check clusterhost underlying host is editable."""
    from compass.db.api import host as host_api
    host_api.check_host_editable(clusterhost.host, user=user)


def _clusterhost_cluster_editable(
    config, clusterhost, session=None, user=None, **kwargs
):
    """Check clusterhost's cluster is editable."""
    check_cluster_editable(clusterhost.cluster, user=user)


@utils.supported_filters(
    optional_support_keys=['os_config', 'package_config']
)
@utils.input_filters(
    os_config=_filter_clusterhost_host_editable,
)
@utils.output_validates_with_args(
    package_config=_clusterhost_cluster_editable
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_CONFIG_FIELDS)
def _delete_clusterhost_config(
    clusterhost, session=None, user=None, **kwargs
):
    """delete clusterhost config."""
    return utils.update_db_object(
        session, clusterhost, config_validated=False,
        **kwargs
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_DEL_CLUSTERHOST_CONFIG
)
def delete_cluster_host_config(
    cluster_id, host_id, user=None, session=None
):
    """Delete a clusterhost config by cluster id and host id."""
    clusterhost = _get_cluster_host(
        cluster_id, host_id, session=session
    )
    return _delete_clusterhost_config(
        clusterhost, session=session, user=user,
        os_config={}, package_config={}
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_DEL_CLUSTERHOST_CONFIG
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_CONFIG_FIELDS)
def delete_clusterhost_config(clusterhost_id, user=None, session=None):
    """Delet a clusterhost config by clusterhost id."""
    clusterhost = _get_clusterhost(
        clusterhost_id, session=session
    )
    return _delete_clusterhost_config(
        clusterhost, session=session, user=user,
        os_config={}, package_config={}
    )


@utils.supported_filters(
    optional_support_keys=['add_hosts', 'remove_hosts', 'set_hosts']
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_UPDATE_CLUSTER_HOSTS
)
@utils.wrap_to_dict(
    ['hosts'],
    hosts=RESP_CLUSTERHOST_FIELDS
)
def update_cluster_hosts(
    cluster_id, add_hosts={}, set_hosts=None,
    remove_hosts={}, user=None, session=None
):
    """Update cluster hosts."""
    cluster = _get_cluster(cluster_id, session=session)
    if remove_hosts:
        _remove_clusterhosts(
            cluster, session=session, user=user, **remove_hosts
        )
    if add_hosts:
        _add_clusterhosts(
            cluster, session=session, user=user, **add_hosts
        )
    if set_hosts is not None:
        _set_clusterhosts(
            cluster, session=session, user=user, **set_hosts
        )

    return {
        'hosts': list_cluster_hosts(cluster_id, session=session)
    }


def validate_clusterhost(clusterhost, session=None):
    """validate clusterhost."""
    roles = clusterhost.roles
    if not roles:
        if clusterhost.cluster.flavor_name:
            raise exception.InvalidParameter(
                'empty roles for clusterhost %s' % clusterhost.name
            )


def validate_cluster(cluster, session=None):
    """Validate cluster."""
    if not cluster.clusterhosts:
        raise exception.InvalidParameter(
            'cluster %s does not have any hosts' % cluster.name
        )
    if cluster.flavor_name:
        cluster_roles = cluster.flavor['roles']
    else:
        cluster_roles = []
    necessary_roles = set([
        role['name'] for role in cluster_roles if not role.get('optional')
    ])
    clusterhost_roles = set([])
    interface_subnets = {}
    for clusterhost in cluster.clusterhosts:
        roles = clusterhost.roles
        for role in roles:
            clusterhost_roles.add(role['name'])
        host = clusterhost.host
        for host_network in host.host_networks:
            interface_subnets.setdefault(
                host_network.interface, set([])
            ).add(host_network.subnet.subnet)
    missing_roles = necessary_roles - clusterhost_roles
    if missing_roles:
        raise exception.InvalidParameter(
            'cluster %s have some roles %s not assigned to any host' % (
                cluster.name, list(missing_roles)
            )
        )
    for interface, subnets in interface_subnets.items():
        if len(subnets) > 1:
            raise exception.InvalidParameter(
                'cluster %s multi subnets %s in interface %s' % (
                    cluster.name, list(subnets), interface
                )
            )


@utils.supported_filters(optional_support_keys=['review'])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_REVIEW_CLUSTER
)
@utils.wrap_to_dict(
    RESP_REVIEW_FIELDS,
    cluster=RESP_CONFIG_FIELDS,
    hosts=RESP_CLUSTERHOST_CONFIG_FIELDS
)
def review_cluster(cluster_id, review={}, user=None, session=None, **kwargs):
    """review cluster.

    Args:
       cluster_id: the cluster id.
       review: dict contains hosts to be reviewed. either contains key
               hosts or clusterhosts. where hosts is a list of host id,
               clusterhosts is a list of clusterhost id.
    """
    from compass.db.api import host as host_api
    cluster = _get_cluster(cluster_id, session=session)
    check_cluster_editable(cluster, user=user)
    host_ids = review.get('hosts', [])
    clusterhost_ids = review.get('clusterhosts', [])
    clusterhosts = []
    # Get clusterhosts need to be reviewed.
    for clusterhost in cluster.clusterhosts:
        if (
            clusterhost.clusterhost_id in clusterhost_ids or
            clusterhost.host_id in host_ids
        ):
            clusterhosts.append(clusterhost)

    os_config = copy.deepcopy(cluster.os_config)
    os_config = metadata_api.autofill_os_config(
        os_config, cluster.os_id, cluster=cluster
    )
    metadata_api.validate_os_config(
        os_config, cluster.os_id, True
    )
    for clusterhost in clusterhosts:
        host = clusterhost.host
        # ignore underlying host os config validation
        # since the host is not editable
        if not host_api.is_host_editable(
            host, user=user, check_in_installing=False
        ):
            logging.info(
                'ignore update host %s config '
                'since it is not editable' % host.name
            )
            continue
        host_os_config = copy.deepcopy(host.os_config)
        host_os_config = metadata_api.autofill_os_config(
            host_os_config, host.os_id,
            host=host
        )
        deployed_os_config = util.merge_dict(
            os_config, host_os_config
        )
        metadata_api.validate_os_config(
            deployed_os_config, host.os_id, True
        )
        host_api.validate_host(host)
        utils.update_db_object(
            session, host, os_config=host_os_config, config_validated=True
        )

    package_config = copy.deepcopy(cluster.package_config)
    if cluster.flavor_name:
        package_config = metadata_api.autofill_flavor_config(
            package_config, cluster.flavor_id,
            cluster=cluster
        )
        metadata_api.validate_flavor_config(
            package_config, cluster.flavor_id, True
        )
        for clusterhost in clusterhosts:
            clusterhost_package_config = copy.deepcopy(
                clusterhost.package_config
            )
            clusterhost_package_config = (
                metadata_api.autofill_flavor_config(
                    clusterhost_package_config,
                    cluster.flavor_id,
                    clusterhost=clusterhost
                )
            )
            deployed_package_config = util.merge_dict(
                package_config, clusterhost_package_config
            )
            metadata_api.validate_flavor_config(
                deployed_package_config,
                cluster.flavor_id, True
            )
            validate_clusterhost(clusterhost, session=session)
            utils.update_db_object(
                session, clusterhost,
                package_config=clusterhost_package_config,
                config_validated=True
            )

    validate_cluster(cluster, session=session)
    utils.update_db_object(
        session, cluster, os_config=os_config, package_config=package_config,
        config_validated=True
    )
    return {
        'cluster': cluster,
        'hosts': clusterhosts
    }


@utils.supported_filters(optional_support_keys=['deploy'])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_DEPLOY_CLUSTER
)
@utils.wrap_to_dict(
    RESP_DEPLOY_FIELDS,
    cluster=RESP_CONFIG_FIELDS,
    hosts=RESP_CLUSTERHOST_FIELDS
)
def deploy_cluster(
    cluster_id, deploy={}, user=None, session=None, **kwargs
):
    """deploy cluster.

    Args:
       cluster_id: cluster id.
       deploy: dict contains key either hosts or clusterhosts.
               deploy['hosts'] is a list of host id,
               deploy['clusterhosts'] is a list of clusterhost id.
    """
    from compass.db.api import host as host_api
    from compass.tasks import client as celery_client
    cluster = _get_cluster(cluster_id, session=session)
    host_ids = deploy.get('hosts', [])
    clusterhost_ids = deploy.get('clusterhosts', [])
    clusterhosts = []
    # get clusterhost to deploy.
    for clusterhost in cluster.clusterhosts:
        if (
            clusterhost.clusterhost_id in clusterhost_ids or
            clusterhost.host_id in host_ids
        ):
            clusterhosts.append(clusterhost)
    check_cluster_editable(cluster, user=user)
    check_cluster_validated(cluster)
    utils.update_db_object(session, cluster.state, state='INITIALIZED')
    for clusterhost in clusterhosts:
        host = clusterhost.host
        # ignore checking if underlying host is validated if
        # the host is not editable.
        if host_api.is_host_editable(host, user=user):
            host_api.check_host_validated(host)
            utils.update_db_object(session, host.state, state='INITIALIZED')
        if cluster.flavor_name:
            check_clusterhost_validated(clusterhost)
            utils.update_db_object(
                session, clusterhost.state, state='INITIALIZED'
            )

    celery_client.celery.send_task(
        'compass.tasks.deploy_cluster',
        (
            user.email, cluster_id,
            [clusterhost.host_id for clusterhost in clusterhosts]
        ),
        queue=user.email,
        exchange=user.email,
        routing_key=user.email
    )
    return {
        'status': 'deploy action sent',
        'cluster': cluster,
        'hosts': clusterhosts
    }


@utils.supported_filters(optional_support_keys=['redeploy'])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_DEPLOY_CLUSTER
)
@utils.wrap_to_dict(
    RESP_DEPLOY_FIELDS,
    cluster=RESP_CONFIG_FIELDS,
    hosts=RESP_CLUSTERHOST_FIELDS
)
def redeploy_cluster(
    cluster_id, deploy={}, user=None, session=None, **kwargs
):
    """redeploy cluster.

    Args:
       cluster_id: cluster id.
    """
    from compass.db.api import host as host_api
    from compass.tasks import client as celery_client
    cluster = _get_cluster(cluster_id, session=session)

    check_cluster_editable(cluster, user=user)
    check_cluster_validated(cluster)
    utils.update_db_object(
        session, cluster.state,
        state='INITIALIZED',
        percentage=0,
        ready=False
    )
    for clusterhost in cluster.clusterhosts:
        host = clusterhost.host
        # ignore checking if underlying host is validated if
        # the host is not editable.
        host_api.check_host_validated(host)
        utils.update_db_object(
            session, host.state,
            state='INITIALIZED',
            percentage=0,
            ready=False
        )
        if cluster.flavor_name:
            check_clusterhost_validated(clusterhost)
            utils.update_db_object(
                session,
                clusterhost.state,
                state='INITIALIZED',
                percentage=0,
                ready=False
            )

    celery_client.celery.send_task(
        'compass.tasks.redeploy_cluster',
        (
            user.email, cluster_id
        ),
        queue=user.email,
        exchange=user.email,
        routing_key=user.email
    )
    return {
        'status': 'redeploy action sent',
        'cluster': cluster
    }


@utils.supported_filters(optional_support_keys=['apply_patch'])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_DEPLOY_CLUSTER
)
@utils.wrap_to_dict(
    RESP_DEPLOY_FIELDS,
    cluster=RESP_CONFIG_FIELDS,
    hosts=RESP_CLUSTERHOST_FIELDS
)
def patch_cluster(cluster_id, user=None, session=None, **kwargs):

    from compass.tasks import client as celery_client

    cluster = _get_cluster(cluster_id, session=session)
    celery_client.celery.send_task(
        'compass.tasks.patch_cluster',
        (
            user.email, cluster_id,
        ),
        queue=user.email,
        exchange=user.email,
        routing_key=user.email
    )
    return {
        'status': 'patch action sent',
        'cluster': cluster
    }


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_GET_CLUSTER_STATE
)
@utils.wrap_to_dict(RESP_STATE_FIELDS)
def get_cluster_state(cluster_id, user=None, session=None, **kwargs):
    """Get cluster state info."""
    return _get_cluster(cluster_id, session=session).state_dict()


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_GET_CLUSTERHOST_STATE
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_STATE_FIELDS)
def get_cluster_host_state(
    cluster_id, host_id, user=None, session=None, **kwargs
):
    """Get clusterhost state merged with underlying host state."""
    return _get_cluster_host(
        cluster_id, host_id, session=session
    ).state_dict()


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_GET_CLUSTERHOST_STATE
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_STATE_FIELDS)
def get_cluster_host_self_state(
    cluster_id, host_id, user=None, session=None, **kwargs
):
    """Get clusterhost itself state."""
    return _get_cluster_host(
        cluster_id, host_id, session=session
    ).state


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_GET_CLUSTERHOST_STATE
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_STATE_FIELDS)
def get_clusterhost_state(
    clusterhost_id, user=None, session=None, **kwargs
):
    """Get clusterhost state merged with underlying host state."""
    return _get_clusterhost(
        clusterhost_id, session=session
    ).state_dict()


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_GET_CLUSTERHOST_STATE
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_STATE_FIELDS)
def get_clusterhost_self_state(
    clusterhost_id, user=None, session=None, **kwargs
):
    """Get clusterhost itself state."""
    return _get_clusterhost(
        clusterhost_id, session=session
    ).state


@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTERHOST_STATE_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_UPDATE_CLUSTERHOST_STATE
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_STATE_FIELDS)
def update_cluster_host_state(
    cluster_id, host_id, user=None, session=None, **kwargs
):
    """Update a clusterhost itself state."""
    clusterhost = _get_cluster_host(
        cluster_id, host_id, session=session
    )
    utils.update_db_object(session, clusterhost.state, **kwargs)
    return clusterhost.state_dict()


def _update_clusterhost_state(
    clusterhost, from_database_only=False,
    session=None, user=None, **kwargs
):
    """Update clusterhost state.

    If from_database_only, the state will only be updated in database.
    Otherwise a task sent to celery and os installer/package installer
    will also update its state if needed.
    """
    if 'ready' in kwargs and kwargs['ready'] and not clusterhost.state.ready:
        ready_triggered = True
    else:
        ready_triggered = False
    cluster_ready = False
    host = clusterhost.host
    cluster = clusterhost.cluster
    host_ready = not host.state.ready
    if ready_triggered:
        cluster_ready = True
        for clusterhost_in_cluster in cluster.clusterhosts:
            if (
                clusterhost_in_cluster.clusterhost_id
                    == clusterhost.clusterhost_id
            ):
                continue
            if not clusterhost_in_cluster.state.ready:
                cluster_ready = False

    logging.info(
        'clusterhost %s ready: %s',
        clusterhost.name, ready_triggered
    )
    logging.info('cluster ready: %s', cluster_ready)
    logging.info('host ready: %s', host_ready)
    if not ready_triggered or from_database_only:
        logging.info('%s state is set to %s', clusterhost.name, kwargs)
        utils.update_db_object(session, clusterhost.state, **kwargs)
        if not clusterhost.state.ready:
            logging.info('%s state ready is set to False', cluster.name)
            utils.update_db_object(session, cluster.state, ready=False)
        status = '%s state is updated' % clusterhost.name
    else:
        if not user:
            user_id = cluster.creator_id
            user_dict = user_api.get_user(user_id, session=session)
            user_email = user_dict['email']
        else:
            user_email = user.email
        from compass.tasks import client as celery_client
        celery_client.celery.send_task(
            'compass.tasks.package_installed',
            (
                clusterhost.cluster_id, clusterhost.host_id,
                cluster_ready, host_ready
            ),
            queue=user_email,
            exchange=user_email,
            routing_key=user_email
        )
        status = '%s: cluster ready %s host ready %s' % (
            clusterhost.name, cluster_ready, host_ready
        )
        logging.info('action status: %s', status)
    return {
        'status': status,
        'clusterhost': clusterhost.state_dict()
    }


@util.deprecated
@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTERHOST_STATE_INTERNAL_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_UPDATE_CLUSTERHOST_STATE
)
@utils.wrap_to_dict(['status', 'clusterhost'])
def update_cluster_host_state_internal(
    cluster_id, host_id, from_database_only=False,
    user=None, session=None, **kwargs
):
    """Update a clusterhost state by installation process."""
    # TODO(xicheng): it should be merged into update_cluster_host_state
    clusterhost = _get_cluster_host(
        cluster_id, host_id, session=session
    )
    return _update_clusterhost_state(
        clusterhost, from_database_only=from_database_only,
        session=session, users=user, **kwargs
    )


@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTERHOST_STATE_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_UPDATE_CLUSTERHOST_STATE
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_STATE_FIELDS)
def update_clusterhost_state(
    clusterhost_id, user=None, session=None, **kwargs
):
    """Update a clusterhost itself state."""
    clusterhost = _get_clusterhost(
        clusterhost_id, session=session
    )
    utils.update_db_object(session, clusterhost.state, **kwargs)
    return clusterhost.state_dict()


@util.deprecated
@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTERHOST_STATE_INTERNAL_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_UPDATE_CLUSTERHOST_STATE
)
@utils.wrap_to_dict(['status', 'clusterhost'])
def update_clusterhost_state_internal(
    clusterhost_id, from_database_only=False,
    user=None, session=None, **kwargs
):
    """Update a clusterhost state by installation process."""
    # TODO(xicheng): it should be merged into update_clusterhost_state
    clusterhost = _get_clusterhost(clusterhost_id, session=session)
    return _update_clusterhost_state(
        clusterhost, from_database_only=from_database_only,
        session=session, user=user, **kwargs
    )


@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTER_STATE_FIELDS,
    ignore_support_keys=(IGNORE_FIELDS + IGNORE_UPDATED_CLUSTER_STATE_FIELDS)
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_UPDATE_CLUSTER_STATE
)
@utils.wrap_to_dict(RESP_STATE_FIELDS)
def update_cluster_state(
    cluster_id, user=None, session=None, **kwargs
):
    """Update a cluster state."""
    cluster = _get_cluster(
        cluster_id, session=session
    )
    utils.update_db_object(session, cluster.state, **kwargs)
    return cluster.state_dict()


@util.deprecated
@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTER_STATE_INTERNAL_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_UPDATE_CLUSTER_STATE
)
@utils.wrap_to_dict(['status', 'cluster'])
def update_cluster_state_internal(
    cluster_id, from_database_only=False,
    user=None, session=None, **kwargs
):
    """Update a cluster state by installation process.

    If from_database_only, the state will only be updated in database.
    Otherwise a task sent to do state update in os installer and
    package installer.
    """
    # TODO(xicheng): it should be merged into update_cluster_state
    cluster = _get_cluster(cluster_id, session=session)
    if 'ready' in kwargs and kwargs['ready'] and not cluster.state.ready:
        ready_triggered = True
    else:
        ready_triggered = False
    clusterhost_ready = {}
    if ready_triggered:
        for clusterhost in cluster.clusterhosts:
            clusterhost_ready[clusterhost.host_id] = (
                not clusterhost.state.ready
            )

    logging.info('cluster %s ready: %s', cluster_id, ready_triggered)
    logging.info('clusterhost ready: %s', clusterhost_ready)

    if not ready_triggered or from_database_only:
        logging.info('%s state is set to %s', cluster.name, kwargs)
        utils.update_db_object(session, cluster.state, **kwargs)
        if not cluster.state.ready:
            for clusterhost in cluster.clusterhosts:
                logging.info('%s state ready is to False', clusterhost.name)
                utils.update_db_object(
                    session, clusterhost.state, ready=False
                )
        status = '%s state is updated' % cluster.name
    else:
        if not user:
            user_id = cluster.creator_id
            user_dict = user_api.get_user(user_id, session=session)
            user_email = user_dict['email']
        else:
            user_email = user.email
        from compass.tasks import client as celery_client
        celery_client.celery.send_task(
            'compass.tasks.cluster_installed',
            (clusterhost.cluster_id, clusterhost_ready),
            queue=user_email,
            exchange=user_email,
            routing_key=user_email
        )
        status = '%s installed action set clusterhost ready %s' % (
            cluster.name, clusterhost_ready
        )
        logging.info('action status: %s', status)
    return {
        'status': status,
        'cluster': cluster.state_dict()
    }


@utils.supported_filters([])
@database.run_in_session()
@utils.wrap_to_dict(RESP_CLUSTERHOST_LOG_FIELDS)
def get_cluster_host_log_histories(
    cluster_id, host_id, user=None, session=None, **kwargs
):
    """Get clusterhost log history by cluster id and host id."""
    return _get_cluster_host(
        cluster_id, host_id, session=session
    ).log_histories


@utils.supported_filters([])
@database.run_in_session()
@utils.wrap_to_dict(RESP_CLUSTERHOST_LOG_FIELDS)
def get_clusterhost_log_histories(
    clusterhost_id, user=None,
    session=None, **kwargs
):
    """Get clusterhost log history by clusterhost id."""
    return _get_clusterhost(
        clusterhost_id, session=session
    ).log_histories


def _get_cluster_host_log_history(
    cluster_id, host_id, filename, session=None, **kwargs
):
    """Get clusterhost log history by cluster id, host id and filename."""
    clusterhost = _get_cluster_host(cluster_id, host_id, session=session)
    return utils.get_db_object(
        session, models.ClusterHostLogHistory,
        clusterhost_id=clusterhost.clusterhost_id, filename=filename,
        **kwargs
    )


def _get_clusterhost_log_history(
    clusterhost_id, filename, session=None, **kwargs
):
    """Get clusterhost log history by clusterhost id and filename."""
    clusterhost = _get_clusterhost(clusterhost_id, session=session)
    return utils.get_db_object(
        session, models.ClusterHostLogHistory,
        clusterhost_id=clusterhost.clusterhost_id, filename=filename,
        **kwargs
    )


@utils.supported_filters([])
@database.run_in_session()
@utils.wrap_to_dict(RESP_CLUSTERHOST_LOG_FIELDS)
def get_cluster_host_log_history(
    cluster_id, host_id, filename, user=None, session=None, **kwargs
):
    """Get clusterhost log history by cluster id, host id and filename."""
    return _get_cluster_host_log_history(
        cluster_id, host_id, filename, session=session
    )


@utils.supported_filters([])
@database.run_in_session()
@utils.wrap_to_dict(RESP_CLUSTERHOST_LOG_FIELDS)
def get_clusterhost_log_history(
    clusterhost_id, filename, user=None, session=None, **kwargs
):
    """Get host log history by clusterhost id and filename."""
    return _get_clusterhost_log_history(
        clusterhost_id, filename, session=session
    )


@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTERHOST_LOG_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@utils.wrap_to_dict(RESP_CLUSTERHOST_LOG_FIELDS)
def update_cluster_host_log_history(
    cluster_id, host_id, filename, user=None, session=None, **kwargs
):
    """Update a host log history by cluster id, host id and filename."""
    cluster_host_log_history = _get_cluster_host_log_history(
        cluster_id, host_id, filename, session=session
    )
    return utils.update_db_object(
        session, cluster_host_log_history, **kwargs
    )


@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTERHOST_LOG_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@utils.wrap_to_dict(RESP_CLUSTERHOST_LOG_FIELDS)
def update_clusterhost_log_history(
    clusterhost_id, filename, user=None, session=None, **kwargs
):
    """Update a host log history by clusterhost id and filename."""
    clusterhost_log_history = _get_clusterhost_log_history(
        clusterhost_id, filename, session=session
    )
    return utils.update_db_object(session, clusterhost_log_history, **kwargs)


@utils.supported_filters(
    ADDED_CLUSTERHOST_LOG_FIELDS,
    optional_support_keys=UPDATED_CLUSTERHOST_LOG_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@utils.wrap_to_dict(RESP_CLUSTERHOST_LOG_FIELDS)
def add_clusterhost_log_history(
    clusterhost_id, exception_when_existing=False,
    filename=None, user=None, session=None, **kwargs
):
    """add a host log history by clusterhost id and filename."""
    clusterhost = _get_clusterhost(clusterhost_id, session=session)
    return utils.add_db_object(
        session, models.ClusterHostLogHistory,
        exception_when_existing,
        clusterhost.clusterhost_id, filename, **kwargs
    )


@utils.supported_filters(
    ADDED_CLUSTERHOST_LOG_FIELDS,
    optional_support_keys=UPDATED_CLUSTERHOST_LOG_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@utils.wrap_to_dict(RESP_CLUSTERHOST_LOG_FIELDS)
def add_cluster_host_log_history(
    cluster_id, host_id, exception_when_existing=False,
    filename=None, user=None, session=None, **kwargs
):
    """add a host log history by cluster id, host id and filename."""
    clusterhost = _get_cluster_host(
        cluster_id, host_id, session=session
    )
    return utils.add_db_object(
        session, models.ClusterHostLogHistory, exception_when_existing,
        clusterhost.clusterhost_id, filename, **kwargs
    )
