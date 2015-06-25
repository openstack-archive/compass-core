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
    'created_at', 'updated_at'
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
UPDATED_CLUSTERHOST_FIELDS = ['roles']
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
    return utils.list_db_objects(
        session, models.Cluster, **filters
    )


def _get_cluster(session, cluster_id, **kwargs):
    if isinstance(cluster_id, (int, long)):
        return utils.get_db_object(
            session, models.Cluster, id=cluster_id, **kwargs
        )
    raise exception.InvalidParameter(
        'cluster id %s type is not int compatible' % cluster_id
    )


def _get_clusterhost(session, clusterhost_id, user=None, **kwargs):
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
        session, cluster_id,
        exception_when_missing=exception_when_missing
    )


def _conditional_exception(cluster, exception_when_not_editable):
    if exception_when_not_editable:
        raise exception.Forbidden(
            'cluster %s is not editable' % cluster.name
        )
    else:
        return False


def is_cluster_validated(cluster):
    if not cluster.config_validated:
        raise exception.Forbidden(
            'cluster %s is not validated' % cluster.name
        )


def is_clusterhost_validated(clusterhost):
    if not clusterhost.config_validated:
        raise exception.Forbidden(
            'clusterhost %s is not validated' % clusterhost.name
        )


def is_cluster_editable(
    cluster, user=None,
    reinstall_distributed_system_set=False,
    exception_when_not_editable=True
):
    if reinstall_distributed_system_set:
        if cluster.state.state == 'INSTALLING':
            logging.debug(
                'cluster %s state is %s',
                cluster.name, cluster.state.state
            )
            return _conditional_exception(
                cluster, exception_when_not_editable
            )
    elif (
        cluster.flavor_name and
        not cluster.reinstall_distributed_system
    ):
        logging.debug(
            'cluster is not editable when not reinstall_distributed_system'
        )
        return _conditional_exception(
            cluster, exception_when_not_editable
        )
    if user and not user.is_admin and cluster.creator_id != user.id:
        return _conditional_exception(
            cluster, exception_when_not_editable
        )
    return True


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
    name=None, user=None, session=None, **kwargs
):
    """Create a cluster."""
    cluster = utils.add_db_object(
        session, models.Cluster, exception_when_existing,
        name, creator_id=user.id,
        **kwargs
    )
    if cluster.flavor_name:
        flavor = metadata_api.get_flavor(
            '%s:%s' % (cluster.adapter_name, cluster.flavor_name),
            user=user, session=session
        )
        cluster.flavor = flavor
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
        session, cluster_id
    )
    is_cluster_editable(
        cluster, user=user,
        reinstall_distributed_system_set=(
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
    """Delete a cluster."""
    cluster = _get_cluster(
        session, cluster_id
    )
    logging.debug(
        'delete cluster %s with force=%s '
        'from_database_only=%s delete_underlying_host=%s',
        cluster.id, force, from_database_only, delete_underlying_host
    )
    for clusterhost in cluster.clusterhosts:
        if clusterhost.state.state != 'UNINITIALIZED' and force:
            clusterhost.state.state = 'ERROR'
        if delete_underlying_host:
            host = clusterhost.host
            if host.state.state != 'UNINITIALIZED' and force:
                host.state.state = 'ERROR'
    if cluster.state.state != 'UNINITIALIZED' and force:
        cluster.state.state = 'ERROR'

    is_cluster_editable(
        cluster, user=user,
        reinstall_distributed_system_set=True
    )

    for clusterhost in cluster.clusterhosts:
        from compass.db.api import host as host_api
        host = clusterhost.host
        host_api.is_host_editable(
            host, user=user, reinstall_os_set=True
        )
        if host.state.state == 'UNINITIALIZED' or from_database_only:
            utils.del_db_object(
                session, host
            )
    if cluster.state.state == 'UNINITIALIZED' or from_database_only:
        return utils.del_db_object(
            session, cluster
        )
    else:
        from compass.tasks import client as celery_client
        clusterhosts = []
        for clusterhost in cluster.clusterhosts:
            clusterhosts.append(clusterhost)

        logging.info('send del cluster %s task to celery', cluster_id)
        celery_client.celery.send_task(
            'compass.tasks.delete_cluster',
            (
                user.email, cluster.id,
                [clusterhost.host_id for clusterhost in clusterhosts],
                delete_underlying_host
            )
        )
        return {
            'status': 'delete action sent',
            'cluster': cluster,
            'hosts': clusterhosts
        }


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_CLUSTER_CONFIG
)
@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
def get_cluster_config(cluster_id, user=None, session=None, **kwargs):
    """Get cluster config."""
    return _get_cluster(session, cluster_id)


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_CLUSTER_CONFIG
)
@utils.wrap_to_dict(RESP_DEPLOYED_CONFIG_FIELDS)
def get_cluster_deployed_config(cluster_id, user=None, session=None, **kwargs):
    """Get cluster deployed config."""
    return _get_cluster(session, cluster_id)


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_METADATAS
)
@utils.wrap_to_dict(RESP_METADATA_FIELDS)
def get_cluster_metadata(cluster_id, user=None, session=None, **kwargs):
    """Get cluster metadata."""
    cluster = _get_cluster(session, cluster_id)
    metadatas = {}
    os_name = cluster.os_name
    if os_name:
        metadatas.update(
            metadata_api.get_os_metadata(
                os_name, session=session
            )
        )
    adapter_name = cluster.adapter_name
    flavor_name = cluster.flavor_name
    if adapter_name and flavor_name:
        metadatas.update(
            metadata_api.get_flavor_metadata(
                '%s:%s' % (adapter_name, flavor_name),
                user=user, session=session
            )
        )
    return metadatas


@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
def _update_cluster_config(session, cluster, user=None, **kwargs):
    """Update a cluster config."""
    is_cluster_editable(cluster, user=user)
    return utils.update_db_object(
        session, cluster, **kwargs
    )


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
    cluster = _get_cluster(session, cluster_id)
    is_cluster_editable(cluster, user=user)
    is_cluster_validated(cluster)
    return utils.update_db_object(
        session, cluster, **kwargs
    )


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
    cluster = _get_cluster(session, cluster_id)

    def os_config_validates(config):
        metadata_api.validate_os_config(
            config, cluster.os_name
        )

    def package_config_validates(config):
        metadata_api.validate_flavor_config(
            config, cluster.adapter_name, cluster.flavor_name
        )

    @utils.input_validates(
        put_os_config=os_config_validates,
        put_package_config=package_config_validates
    )
    def update_config_internal(
        cluster, **in_kwargs
    ):
        return _update_cluster_config(
            session, cluster, user=user, **in_kwargs
        )

    return update_config_internal(
        cluster, **kwargs
    )


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
    cluster = _get_cluster(session, cluster_id)

    def os_config_validates(config):
        metadata_api.validate_os_config(
            config, cluster.os_name
        )

    def package_config_validates(config):
        metadata_api.validate_flavor_config(
            config, cluster.adapter_name, cluster.flavor_name
        )

    @utils.output_validates(
        os_config=os_config_validates,
        package_config=package_config_validates
    )
    def update_config_internal(cluster, **in_kwargs):
        return _update_cluster_config(
            session, cluster, user=user, **in_kwargs
        )

    return update_config_internal(
        cluster, **kwargs
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
        session, cluster_id
    )
    is_cluster_editable(cluster, user=user)
    return utils.update_db_object(
        session, cluster, os_config={},
        package_config={}, config_validated=False
    )


@utils.supported_filters(
    ADDED_HOST_FIELDS,
    optional_support_keys=(UPDATED_HOST_FIELDS + UPDATED_CLUSTERHOST_FIELDS),
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(name=utils.check_name)
def add_clusterhost_internal(
        session, cluster,
        exception_when_existing=False,
        user=None, machine_id=None, **kwargs
):
    clusterhost_dict = {}
    host_dict = {}
    for key, value in kwargs.items():
        if key in UPDATED_CLUSTERHOST_FIELDS:
            clusterhost_dict[key] = value
        else:
            host_dict[key] = value
    host = utils.get_db_object(
        session, models.Host, False, id=machine_id
    )
    if host:
        from compass.db.api import host as host_api
        if (
            host_dict and
            host_api.is_host_editable(
                host, user=cluster.creator,
                reinstall_os_set=kwargs.get('reinstall_os', False),
                exception_when_not_editable=False
            )
        ):
            utils.update_db_object(
                session, host,
                **host_dict
            )
        else:
            logging.info('host %s is not editable', host.name)
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
            **host_dict
        )

    roles = kwargs.get('roles')
    if roles:
        if not cluster.flavor_name:
            raise exception.InvalidParameter(
                'no flavor in cluster %s' % cluster.name
            )
        cluster_roles = [role['name'] for role in cluster.flavor['roles']]
        for role in roles:
            if role not in cluster_roles:
                raise exception.InvalidParameter(
                    'role %s is not in cluster roles %s' % (
                        role, cluster_roles
                    )
                )

    return utils.add_db_object(
        session, models.ClusterHost, exception_when_existing,
        cluster.id, host.id, **clusterhost_dict
    )


def _add_clusterhosts(session, cluster, machines, user=None):
    is_cluster_editable(
        cluster, user=user,
        reinstall_distributed_system_set=True
    )
    for machine_dict in machines:
        add_clusterhost_internal(
            session, cluster, user=user, **machine_dict
        )


def _remove_clusterhosts(session, cluster, hosts, user=None):
    is_cluster_editable(
        cluster, user=user,
        reinstall_distributed_system_set=True
    )
    utils.del_db_objects(
        session, models.ClusterHost,
        cluster_id=cluster.id, host_id=hosts
    )


def _set_clusterhosts(session, cluster, machines, user=None):
    is_cluster_editable(
        cluster, user=user,
        reinstall_distributed_system_set=True
    )
    utils.del_db_objects(
        session, models.ClusterHost,
        cluster_id=cluster.id
    )
    for machine_dict in machines:
        add_clusterhost_internal(
            session, cluster, True, user=user, **machine_dict
        )


@utils.supported_filters(optional_support_keys=SUPPORTED_CLUSTERHOST_FIELDS)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_CLUSTERHOSTS
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_FIELDS)
def list_cluster_hosts(cluster_id, user=None, session=None, **filters):
    """Get cluster host info."""
    cluster = _get_cluster(session, cluster_id)
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
    """Get cluster host info."""
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
    """Get clusterhost info."""
    from compass.db.api import host as host_api
    cluster = _get_cluster(session, cluster_id)
    host = host_api.get_host(host_id, user=user, session=session)
    return utils.get_db_object(
        session, models.ClusterHost,
        exception_when_missing=exception_when_missing,
        cluster_id=cluster.id, host_id=host['id']
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
    """Get clusterhost info."""
    return _get_clusterhost(
        session, clusterhost_id,
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
    """Add cluster host."""
    cluster = _get_cluster(session, cluster_id)
    is_cluster_editable(
        cluster, user=user,
        reinstall_distributed_system_set=True
    )
    return add_clusterhost_internal(
        session, cluster, exception_when_existing,
        user=user, **kwargs
    )


@utils.wrap_to_dict(RESP_CLUSTERHOST_FIELDS)
def _update_clusterhost(session, clusterhost, user=None, **kwargs):
    clusterhost_dict = {}
    host_dict = {}
    for key, value in kwargs.items():
        if key in UPDATED_HOST_FIELDS:
            host_dict[key] = value
        else:
            clusterhost_dict[key] = value

    host = clusterhost.host
    if host_dict:
        from compass.db.api import host as host_api
        if host_api.is_host_editable(
            host, user=clusterhost.cluster.creator,
            reinstall_os_set=kwargs.get('reinstall_os', False),
            exception_when_not_editable=False
        ):
            utils.update_db_object(
                session, host,
                **host_dict
            )
        else:
            logging.debug(
                'ignore no editable host %s', host.id
            )
    else:
        logging.debug(
            'nothing to update for host %s', host.id
        )

    def roles_validates(roles):
        cluster_roles = []
        cluster = clusterhost.cluster
        if not roles:
            if cluster.flavor_name:
                raise exception.InvalidParameter(
                    'roles %s is empty' % roles
                )
        else:
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

    @utils.input_validates(
        roles=roles_validates,
        patched_roles=roles_validates
    )
    def update_internal(clusterhost, **in_kwargs):
        return utils.update_db_object(
            session, clusterhost, **in_kwargs
        )

    is_cluster_editable(clusterhost.cluster, user=user)
    return update_internal(
        clusterhost, **clusterhost_dict
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
    """Update cluster host."""
    from compass.db.api import host as host_api
    cluster = _get_cluster(session, cluster_id)
    host = host_api.get_host(host_id, session=session, user=user)
    clusterhost = utils.get_db_object(
        session, models.ClusterHost, cluster_id=cluster.id, host_id=host['id']
    )
    return _update_clusterhost(session, clusterhost, user=user, **kwargs)


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
    """Update cluster host."""
    clusterhost = _get_clusterhost(
        session, clusterhost_id, user=user
    )
    return _update_clusterhost(session, clusterhost, user=user, **kwargs)


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
    """Update cluster host."""
    from compass.db.api import host as host_api
    cluster = _get_cluster(session, cluster_id)
    host = host_api.get_host(host_id, session=session, user=user)
    clusterhost = utils.get_db_object(
        session, models.ClusterHost, cluster_id=cluster.id, host_id=host['id']
    )
    return _update_clusterhost(session, clusterhost, user, **kwargs)


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
    """Update cluster host."""
    clusterhost = _get_clusterhost(
        session, clusterhost_id, user=user
    )
    return _update_clusterhost(session, clusterhost, user, **kwargs)


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
    if clusterhost.state.state != 'UNINITIALIZED' and force:
        clusterhost.state.state = 'ERROR'
    if not force:
        is_cluster_editable(
            clusterhost.cluster, user=user,
            reinstall_distributed_system_set=True
        )
    else:
        raise Exception(
            'cluster is not editable: %s', clusterhost.cluster.state.state
        )
    if delete_underlying_host:
        host = clusterhost.host
        if host.state.state != 'UNINITIALIZED' and force:
            host.state.state = 'ERROR'
        import compass.db.api.host as host_api
        host_api.is_host_editable(
            host, user=user,
            reinstall_os_set=True
        )
        if host.state.state == 'UNINITIALIZED' or from_database_only:
            utils.del_db_object(
                session, host
            )

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
            )
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
    """Delete cluster host."""
    from compass.db.api import host as host_api
    cluster = _get_cluster(session, cluster_id)
    host = host_api.get_host(host_id, session=session, user=user)
    clusterhost = utils.get_db_object(
        session, models.ClusterHost,
        cluster_id=cluster.id, host_id=host['id']
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
    """Delete cluster host."""
    clusterhost = _get_clusterhost(
        session, clusterhost_id, user=user
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
    """Get clusterhost config."""
    from compass.db.api import host as host_api
    cluster = _get_cluster(session, cluster_id)
    host = host_api.get_host(host_id, session=session, user=user)
    return utils.get_db_object(
        session, models.ClusterHost,
        cluster_id=cluster.id, host_id=host['id']
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
    """Get clusterhost deployed config."""
    from compass.db.api import host as host_api
    cluster = _get_cluster(session, cluster_id)
    host = host_api.get_host(host_id, session=session, user=user)
    return utils.get_db_object(
        session, models.ClusterHost,
        cluster_id=cluster.id, host_id=host['id']
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_CLUSTERHOST_CONFIG
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_CONFIG_FIELDS)
def get_clusterhost_config(clusterhost_id, user=None, session=None, **kwargs):
    """Get clusterhost config."""
    return _get_clusterhost(
        session, clusterhost_id, user=user
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
    """Get clusterhost deployed config."""
    return _get_clusterhost(
        session, clusterhost_id, user=user
    )


@utils.wrap_to_dict(RESP_CLUSTERHOST_CONFIG_FIELDS)
def _update_clusterhost_config(session, clusterhost, user=None, **kwargs):
    from compass.db.api import host as host_api
    ignore_keys = []
    if not host_api.is_host_editable(
        clusterhost.host, user=user,
        exception_when_not_editable=False
    ):
        ignore_keys.append('put_os_config')

    def os_config_validates(os_config):
        host = clusterhost.host
        metadata_api.validate_os_config(
            os_config, host.os_name)

    def package_config_validates(package_config):
        cluster = clusterhost.cluster
        is_cluster_editable(cluster, user=user)
        metadata_api.validate_flavor_config(
            package_config, cluster.adapter_name, cluster.flavor_name
        )

    @utils.supported_filters(
        optional_support_keys=UPDATED_CLUSTERHOST_CONFIG_FIELDS,
        ignore_support_keys=ignore_keys
    )
    @utils.input_validates(
        put_os_config=os_config_validates,
        put_package_config=package_config_validates
    )
    def update_config_internal(clusterihost, **in_kwargs):
        return utils.update_db_object(
            session, clusterhost, **in_kwargs
        )

    return update_config_internal(
        clusterhost, **kwargs
    )


@utils.wrap_to_dict(RESP_CLUSTERHOST_DEPLOYED_CONFIG_FIELDS)
def _update_clusterhost_deployed_config(
    session, clusterhost, user=None, **kwargs
):
    from compass.db.api import host as host_api
    ignore_keys = []
    if not host_api.is_host_editable(
        clusterhost.host, user=user,
        exception_when_not_editable=False
    ):
        ignore_keys.append('deployed_os_config')

    def os_config_validates(os_config):
        host = clusterhost.host
        host_api.is_host_validated(host)

    def package_config_validates(package_config):
        cluster = clusterhost.cluster
        is_cluster_editable(cluster, user=user)
        is_clusterhost_validated(clusterhost)

    @utils.supported_filters(
        optional_support_keys=UPDATED_CLUSTERHOST_DEPLOYED_CONFIG_FIELDS,
        ignore_support_keys=ignore_keys
    )
    @utils.input_validates(
        deployed_os_config=os_config_validates,
        deployed_package_config=package_config_validates
    )
    def update_config_internal(clusterhost, **in_kwargs):
        return utils.update_db_object(
            session, clusterhost, **in_kwargs
        )

    return update_config_internal(
        clusterhost, **kwargs
    )


@utils.replace_filters(
    os_config='put_os_config',
    package_config='put_package_config'
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_CLUSTERHOST_CONFIG
)
def update_cluster_host_config(
    cluster_id, host_id, user=None, session=None, **kwargs
):
    """Update clusterhost config."""
    from compass.db.api import host as host_api
    cluster = _get_cluster(session, cluster_id)
    host = host_api.get_host(host_id, session=session, user=user)
    clusterhost = utils.get_db_object(
        session, models.ClusterHost,
        cluster_id=cluster.id, host_id=host['id']
    )
    return _update_clusterhost_config(
        session, clusterhost, user=user, **kwargs
    )


@utils.replace_filters(
    os_config='deployed_os_config',
    package_config='deployed_package_config'
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_CLUSTERHOST_CONFIG
)
def update_cluster_host_deployed_config(
    cluster_id, host_id, user=None, session=None, **kwargs
):
    """Update clusterhost deployed config."""
    from compass.db.api import host as host_api
    cluster = _get_cluster(session, cluster_id)
    host = host_api.get_host(host_id, session=session, user=user)
    clusterhost = utils.get_db_object(
        session, models.ClusterHost,
        cluster_id=cluster.id, host_id=host['id']
    )
    return _update_clusterhost_deployed_config(
        session, clusterhost, user=user, **kwargs
    )


@utils.replace_filters(
    os_config='put_os_config',
    package_config='put_package_config'
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_CLUSTERHOST_CONFIG
)
def update_clusterhost_config(
    clusterhost_id, user=None, session=None, **kwargs
):
    """Update clusterhost config."""
    clusterhost = _get_clusterhost(
        session, clusterhost_id, user=user
    )
    return _update_clusterhost_config(
        session, clusterhost, user=user, **kwargs
    )


@utils.replace_filters(
    os_config='deployed_os_config',
    package_config='deployed_package_config'
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_CLUSTERHOST_CONFIG
)
def update_clusterhost_deployed_config(
    clusterhost_id, user=None, session=None, **kwargs
):
    """Update clusterhost deployed config."""
    clusterhost = _get_clusterhost(
        session, clusterhost_id, user=user
    )
    return _update_clusterhost_deployed_config(
        session, clusterhost, user=user, **kwargs
    )


@utils.wrap_to_dict(RESP_CLUSTERHOST_CONFIG_FIELDS)
def _patch_clusterhost_config(session, user, clusterhost, **kwargs):
    from compass.db.api import host as host_api
    ignore_keys = []
    if not host_api.is_host_editable(
        clusterhost.host, user=user,
        exception_when_not_editable=False
    ):
        ignore_keys.append('patched_os_config')

    def os_config_validates(os_config):
        host = clusterhost.host
        metadata_api.validate_os_config(os_config, host.os_name)

    def package_config_validates(package_config):
        cluster = clusterhost.cluster
        is_cluster_editable(cluster, user=user)
        metadata_api.validate_flavor_config(
            package_config, cluster.adapter_name, cluster.flavor_name
        )

    @utils.supported_filters(
        optional_support_keys=PATCHED_CLUSTERHOST_CONFIG_FIELDS,
        ignore_support_keys=ignore_keys
    )
    @utils.output_validates(
        os_config=os_config_validates,
        package_config=package_config_validates
    )
    def patch_config_internal(clusterhost, **in_kwargs):
        return utils.update_db_object(
            session, clusterhost, **in_kwargs
        )

    return patch_config_internal(
        clusterhost, **kwargs
    )


@utils.replace_filters(
    os_config='patched_os_config',
    package_config='patched_package_config'
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_CLUSTERHOST_CONFIG
)
def patch_cluster_host_config(
    cluster_id, host_id, user=None, session=None, **kwargs
):
    """patch clusterhost config."""
    from compass.db.api import host as host_api
    cluster = _get_cluster(session, cluster_id)
    host = host_api.get_host(host_id, session=session, user=user)
    clusterhost = utils.get_db_object(
        session, models.ClusterHost,
        cluster_id=cluster.id, host_id=host['id']
    )
    return _patch_clusterhost_config(
        session, user, clusterhost, **kwargs
    )


@utils.replace_filters(
    os_config='patched_os_config',
    package_config='patched_package_config'
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_CLUSTERHOST_CONFIG
)
def patch_clusterhost_config(
    clusterhost_id, user=None, session=None, **kwargs
):
    """patch clusterhost config."""
    clusterhost = _get_clusterhost(
        session, clusterhost_id, user=user
    )
    return _patch_clusterhost_config(
        session, user, clusterhost, **kwargs
    )


@utils.wrap_to_dict(RESP_CLUSTERHOST_CONFIG_FIELDS)
def _delete_clusterhost_config(
    session, user, clusterhost
):
    from compass.db.api import host as host_api
    ignore_keys = []
    if not host_api.is_host_editable(
        clusterhost.host, user=user,
        exception_when_not_editable=False
    ):
        ignore_keys.append('os_config')

    def package_config_validates(package_config):
        is_cluster_editable(clusterhost.cluster, user=user)

    @utils.supported_filters(
        optional_support_keys=['os_config', 'package_config'],
        ignore_support_keys=ignore_keys
    )
    @utils.output_validates(
        package_config=package_config_validates
    )
    def delete_config_internal(clusterhost, **in_kwargs):
        return utils.update_db_object(
            session, clusterhost, config_validated=False,
            **in_kwargs
        )

    return delete_config_internal(
        clusterhost, os_config={},
        package_config={}
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_DEL_CLUSTERHOST_CONFIG
)
def delete_cluster_host_config(
    cluster_id, host_id, user=None, session=None
):
    """Delete a clusterhost config."""
    from compass.db.api import host as host_api
    cluster = _get_cluster(session, cluster_id)
    host = host_api.get_host(host_id, session=session, user=user)
    clusterhost = utils.get_db_object(
        session, models.ClusterHost,
        cluster_id=cluster.id, host_id=host['id']
    )
    return _delete_clusterhost_config(
        session, user, clusterhost
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_DEL_CLUSTERHOST_CONFIG
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_CONFIG_FIELDS)
def delete_clusterhost_config(clusterhost_id, user=None, session=None):
    """Delet a clusterhost config."""
    clusterhost = _get_clusterhost(
        session, clusterhost_id, user=user
    )
    return _delete_clusterhost_config(
        session, user, clusterhost
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
    cluster = _get_cluster(session, cluster_id)
    if remove_hosts:
        _remove_clusterhosts(session, cluster, **remove_hosts)
    if add_hosts:
        _add_clusterhosts(session, cluster, user=user, **add_hosts)
    if set_hosts is not None:
        _set_clusterhosts(session, cluster, user=user, **set_hosts)
    clusterhosts = utils.list_db_objects(
        session, models.ClusterHost, cluster_id=cluster.id
    )
    logging.info('updated clusterhosts: %s', clusterhosts)
    for clusterhost in clusterhosts:
        logging.info('clusterhost state: %s', clusterhost.state)
    return {
        'hosts': clusterhosts
    }


def validate_clusterhost(session, clusterhost):
    roles = clusterhost.roles
    if not roles:
        if clusterhost.cluster.flavor_name:
            raise exception.InvalidParameter(
                'empty roles for clusterhost %s' % clusterhost.name
            )


def validate_cluster(session, cluster):
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
    """review cluster."""
    from compass.db.api import host as host_api
    cluster = _get_cluster(session, cluster_id)
    is_cluster_editable(cluster, user=user)
    host_ids = review.get('hosts', [])
    clusterhost_ids = review.get('clusterhosts', [])
    clusterhosts = []
    for clusterhost in cluster.clusterhosts:
        if (
            clusterhost.clusterhost_id in clusterhost_ids or
            clusterhost.host_id in host_ids
        ):
            clusterhosts.append(clusterhost)
    os_config = copy.deepcopy(cluster.os_config)
    os_config = metadata_api.autofill_os_config(
        os_config, cluster.os_name, cluster=cluster
    )
    if os_config:
        metadata_api.validate_os_config(
            os_config, cluster.os_name, True
        )
        for clusterhost in clusterhosts:
            host = clusterhost.host
            if not host_api.is_host_editable(
                host, user=user, reinstall_os_set=False
            ):
                logging.info(
                    'ignore update host %s config '
                    'since it is not editable' % host.name
                )
                continue
            host_os_config = copy.deepcopy(host.os_config)
            host_os_config = metadata_api.autofill_os_config(
                host_os_config, host.os_name,
                host=host
            )
            deployed_os_config = util.merge_dict(
                os_config, host_os_config
            )
            metadata_api.validate_os_config(
                deployed_os_config, host.os_name, True
            )
            host_api.validate_host(host)
            utils.update_db_object(
                session, host, os_config=host_os_config, config_validated=True
            )
    package_config = copy.deepcopy(cluster.package_config)
    package_config = metadata_api.autofill_flavor_config(
        package_config, cluster.adapter_name, cluster.flavor_name,
        cluster=cluster
    )
    if package_config:
        metadata_api.validate_flavor_config(
            package_config, cluster.adapter_name, cluster.flavor_name, True
        )
        for clusterhost in clusterhosts:
            clusterhost_package_config = copy.deepcopy(
                clusterhost.package_config
            )
            clusterhost_package_config = metadata_api.autofill_flavor_config(
                clusterhost_package_config,
                cluster.adapter_name, cluster.flavor_name,
                clusterhost=clusterhost
            )
            deployed_package_config = util.merge_dict(
                package_config, clusterhost_package_config
            )
            metadata_api.validate_flavor_config(
                deployed_package_config,
                cluster.adapter_name, cluster.flavor_name, True
            )
            validate_clusterhost(session, clusterhost)
            utils.update_db_object(
                session, clusterhost,
                package_config=clusterhost_package_config,
                config_validated=True
            )
    validate_cluster(session, cluster)
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
    """deploy cluster."""
    from compass.db.api import host as host_api
    from compass.tasks import client as celery_client
    cluster = _get_cluster(session, cluster_id)
    host_ids = deploy.get('hosts', [])
    clusterhost_ids = deploy.get('clusterhosts', [])
    clusterhosts = []
    for clusterhost in cluster.clusterhosts:
        if (
            clusterhost.clusterhost_id in clusterhost_ids or
            clusterhost.host_id in host_ids
        ):
            clusterhosts.append(clusterhost)
    is_cluster_editable(cluster, user=user)
    is_cluster_validated(cluster)
    utils.update_db_object(session, cluster.state, state='INITIALIZED')
    for clusterhost in clusterhosts:
        host = clusterhost.host
        if host_api.is_host_editable(
            host, user=user,
            exception_when_not_editable=False
        ):
            host_api.is_host_validated(host)
            utils.update_db_object(session, host.state, state='INITIALIZED')
        if cluster.flavor_name:
            is_clusterhost_validated(clusterhost)
            utils.update_db_object(
                session, clusterhost.state, state='INITIALIZED'
            )

    celery_client.celery.send_task(
        'compass.tasks.deploy_cluster',
        (
            user.email, cluster_id,
            [clusterhost.host_id for clusterhost in clusterhosts]
        )
    )
    return {
        'status': 'deploy action sent',
        'cluster': cluster,
        'hosts': clusterhosts
    }


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_GET_CLUSTER_STATE
)
@utils.wrap_to_dict(RESP_STATE_FIELDS)
def get_cluster_state(cluster_id, user=None, session=None, **kwargs):
    """Get cluster state info."""
    return _get_cluster(session, cluster_id).state_dict()


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_GET_CLUSTERHOST_STATE
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_STATE_FIELDS)
def get_cluster_host_state(
    cluster_id, host_id, user=None, session=None, **kwargs
):
    """Get clusterhost state info."""
    from compass.db.api import host as host_api
    cluster = _get_cluster(session, cluster_id)
    host = host_api.get_host(host_id, session=session, user=user)
    return utils.get_db_object(
        session, models.ClusterHost,
        cluster_id=cluster.id, host_id=host['id']
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
    """Get clusterhost state info."""
    from compass.db.api import host as host_api
    cluster = _get_cluster(session, cluster_id)
    host = host_api.get_host(host_id, session=session, user=user)
    clusterhost = utils.get_db_object(
        session, models.ClusterHost,
        cluster_id=cluster.id, host_id=host['id']
    )
    return utils.get_db_object(
        session, models.ClusterHostState,
        id=clusterhost.clusterhost_id
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_GET_CLUSTERHOST_STATE
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_STATE_FIELDS)
def get_clusterhost_state(
    clusterhost_id, user=None, session=None, **kwargs
):
    """Get clusterhost state info."""
    return _get_clusterhost(
        session, clusterhost_id, user=user
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
    """Get clusterhost state info."""
    return _get_clusterhost(
        session, clusterhost_id
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
    """Update a clusterhost state."""
    from compass.db.api import host as host_api
    cluster = _get_cluster(session, cluster_id)
    host = host_api.get_host(host_id, session=session, user=user)
    clusterhost = utils.get_db_object(
        session, models.ClusterHost,
        cluster_id=cluster.id, host_id=host['id']
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
def update_cluster_host_state_internal(
    cluster_id, host_id, from_database_only=False,
    user=None, session=None, **kwargs
):
    """Update a clusterhost state."""
    # TODO(xicheng): it should be merged into update_cluster_host_state
    from compass.db.api import host as host_api
    cluster = _get_cluster(session, cluster_id)
    host = host_api.get_host(host_id, session=session, user=user)
    clusterhost = utils.get_db_object(
        session, models.ClusterHost,
        cluster_id=cluster.id, host_id=host['id']
    )
    if 'ready' in kwargs and kwargs['ready'] and not clusterhost.state.ready:
        ready_triggered = True
    else:
        ready_triggered = False
    cluster_ready = False
    host = clusterhost.host
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
        'cluster %s host %s ready: %s',
        cluster_id, host_id, ready_triggered
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
        from compass.tasks import client as celery_client
        celery_client.celery.send_task(
            'compass.tasks.package_installed',
            (
                clusterhost.cluster_id, clusterhost.host_id,
                cluster_ready, host_ready
            )
        )
        status = '%s: cluster ready %s host ready %s' % (
            clusterhost.name, cluster_ready, host_ready
        )
        logging.info('action status: %s', status)
    return {
        'status': status,
        'clusterhost': clusterhost.state_dict()
    }


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
    """Update a clusterhost state."""
    clusterhost = _get_clusterhost(
        session, clusterhost_id, user=user
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
    """Update a clusterhost state."""
    # TODO(xicheng): it should be merged into update_clusterhost_state
    clusterhost = _get_clusterhost(session, clusterhost_id)
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
        clusterhost_id, ready_triggered
    )
    logging.info('cluster ready: %s', cluster_ready)
    logging.info('host ready: %s', host_ready)
    if not ready_triggered or from_database_only:
        logging.info('%s set state to %s', clusterhost.name, kwargs)
        utils.update_db_object(session, clusterhost.state, **kwargs)
        if not clusterhost.state.ready:
            logging.info('%s state ready is to False', cluster.name)
            utils.update_db_object(session, cluster.state, ready=False)
        status = '%s state is updated' % clusterhost.name
    else:
        from compass.tasks import client as celery_client
        celery_client.celery.send_task(
            'compass.tasks.package_installed',
            (
                clusterhost.cluster_id, clusterhost.host_id,
                cluster_ready, host_ready
            )
        )
        status = '%s: cluster ready %s host ready %s' % (
            clusterhost.name, cluster_ready, host_ready
        )
        logging.info('action status: %s', status)
    return {
        'status': status,
        'clusterhost': clusterhost.state_dict()
    }


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
        session, cluster_id
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
    """Update a cluster state."""
    # TODO(xicheng): it should be merged into update_cluster_state
    cluster = _get_cluster(session, cluster_id)
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
        from compass.tasks import client as celery_client
        celery_client.celery.send_task(
            'compass.tasks.cluster_installed',
            (clusterhost.cluster_id, clusterhost_ready)
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
    """Get clusterhost log history."""
    from compass.db.api import host as host_api
    cluster = _get_cluster(session, cluster_id)
    host = host_api.get_host(host_id, session=session, user=user)
    return utils.list_db_objects(
        session, models.ClusterHostLogHistory,
        cluster_id=cluster.id, host_id=host['id']
    )


@utils.supported_filters([])
@database.run_in_session()
@utils.wrap_to_dict(RESP_CLUSTERHOST_LOG_FIELDS)
def get_clusterhost_log_histories(
    clusterhost_id, user=None,
    session=None, **kwargs
):
    """Get clusterhost log history."""
    clusterhost = _get_clusterhost(session, clusterhost_id, user=user)
    return utils.list_db_objects(
        session, models.ClusterHostLogHistory,
        clusterhost_id=clusterhost.clusterhost_id
    )


@utils.supported_filters([])
@database.run_in_session()
@utils.wrap_to_dict(RESP_CLUSTERHOST_LOG_FIELDS)
def get_cluster_host_log_history(
    cluster_id, host_id, filename, user=None, session=None, **kwargs
):
    """Get clusterhost log history."""
    from compass.db.api import host as host_api
    cluster = _get_cluster(session, cluster_id)
    host = host_api.get_host(host_id, session=session, user=user)
    return utils.get_db_object(
        session, models.ClusterHostLogHistory,
        cluster_id=cluster.id, host_id=host['id'], filename=filename
    )


@utils.supported_filters([])
@database.run_in_session()
@utils.wrap_to_dict(RESP_CLUSTERHOST_LOG_FIELDS)
def get_clusterhost_log_history(
    clusterhost_id, filename, user=None, session=None, **kwargs
):
    """Get host log history."""
    clusterhost = _get_clusterhost(session, clusterhost_id, user=user)
    return utils.get_db_object(
        session, models.ClusterHostLogHistory,
        clusterhost_id=clusterhost.clusterhost_id, filename=filename
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
    """Update a host log history."""
    from compass.db.api import host as host_api
    cluster = _get_cluster(session, cluster_id)
    host = host_api.get_host(host_id, session=session, user=user)
    cluster_host_log_history = utils.get_db_object(
        session, models.ClusterHostLogHistory,
        cluster_id=cluster.id, host_id=host['id'], filename=filename
    )
    return utils.update_db_object(session, cluster_host_log_history, **kwargs)


@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTERHOST_LOG_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@utils.wrap_to_dict(RESP_CLUSTERHOST_LOG_FIELDS)
def update_clusterhost_log_history(
    clusterhost_id, filename, user=None, session=None, **kwargs
):
    """Update a host log history."""
    clusterhost = _get_clusterhost(session, clusterhost_id, user=user)
    clusterhost_log_history = utils.get_db_object(
        session, models.ClusterHostLogHistory,
        clusterhost_id=clusterhost.clusterhost_id, filename=filename
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
    """add a host log history."""
    clusterhost = _get_clusterhost(session, clusterhost_id, user=user)
    return utils.add_db_object(
        session, models.ClusterHostLogHistory, exception_when_existing,
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
    """add a host log history."""
    from compass.db.api import host as host_api
    cluster = _get_cluster(session, cluster_id)
    host = host_api.get_host(host_id, session=session, user=user)
    clusterhost = utils.get_db_object(
        session, models.ClusterHost,
        cluster_id=cluster.id, host_id=host['id']
    )
    return utils.add_db_object(
        session, models.ClusterHostLogHistory, exception_when_existing,
        clusterhost.clusterhost_id, filename, **kwargs
    )
