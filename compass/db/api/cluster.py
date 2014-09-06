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
import functools
import logging

from compass.db.api import database
from compass.db.api import metadata_holder as metadata_api
from compass.db.api import permission
from compass.db.api import user as user_api
from compass.db.api import utils
from compass.db import exception
from compass.db import models
from compass.utils import util


SUPPORTED_FIELDS = [
    'name', 'os_name', 'distributed_system_name', 'owner', 'adapter_id'
]
SUPPORTED_CLUSTERHOST_FIELDS = []
RESP_FIELDS = [
    'id', 'name', 'os_name', 'os_id', 'distributed_system_id',
    'reinstall_distributed_system', 'flavor',
    'distributed_system_name', 'distributed_system_installed',
    'owner', 'adapter_id',
    'created_at', 'updated_at'
]
RESP_CLUSTERHOST_FIELDS = [
    'id', 'host_id', 'clusterhost_id', 'machine_id',
    'name', 'hostname', 'roles', 'os_installer',
    'cluster_id', 'clustername', 'location', 'tag',
    'networks', 'mac', 'switch_ip', 'port', 'switches',
    'os_installed', 'distributed_system_installed',
    'os_name', 'distributed_system_name',
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
    'status',
    'created_at', 'updated_at'
]
RESP_CLUSTERHOST_STATE_FIELDS = [
    'id', 'state', 'percentage', 'message', 'severity',
    'created_at', 'updated_at'
]
RESP_REVIEW_FIELDS = [
    'cluster', 'clusterhosts'
]
RESP_DEPLOY_FIELDS = [
    'status', 'cluster', 'clusterhosts'
]
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
UPDATED_CLUSTER_STATE_FIELDS = [
    'state'
]
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
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_CLUSTERS
)
@utils.wrap_to_dict(RESP_FIELDS)
def list_clusters(session, lister, **filters):
    """List clusters."""
    return utils.list_db_objects(
        session, models.Cluster, **filters
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_CLUSTERS
)
@utils.wrap_to_dict(RESP_FIELDS)
def get_cluster(
    session, getter, cluster_id,
    exception_when_missing=True, **kwargs
):
    """Get cluster info."""
    return utils.get_db_object(
        session, models.Cluster, exception_when_missing, id=cluster_id
    )


def _conditional_exception(cluster, exception_when_not_editable):
    if exception_when_not_editable:
        raise exception.Forbidden(
            'cluster %s is not editable' % cluster.name
        )
    else:
        return False


def is_cluster_validated(
    session, cluster
):
    if not cluster.config_validated:
        raise exception.Forbidden(
            'cluster %s is not validated' % cluster.name
        )


def is_clusterhost_validated(
    session, clusterhost
):
    if not clusterhost.config_validated:
        raise exception.Forbidden(
            'clusterhost %s is not validated' % clusterhost.name
        )


def is_cluster_editable(
    session, cluster, user,
    reinstall_distributed_system_set=False,
    exception_when_not_editable=True
):
    if reinstall_distributed_system_set:
        if cluster.state.state == 'INSTALLING':
            return _conditional_exception(
                cluster, exception_when_not_editable
            )
    elif (
        cluster.distributed_system and
        not cluster.reinstall_distributed_system
    ):
        return _conditional_exception(
            cluster, exception_when_not_editable
        )
    if not user.is_admin and cluster.creator_id != user.id:
        return _conditional_exception(
            cluster, exception_when_not_editable
        )
    return True


@utils.supported_filters(
    ADDED_FIELDS,
    optional_support_keys=OPTIONAL_ADDED_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_CLUSTER
)
@utils.wrap_to_dict(RESP_FIELDS)
def add_cluster(
    session, creator,
    exception_when_existing=True,
    name=None, **kwargs
):
    """Create a cluster."""
    return utils.add_db_object(
        session, models.Cluster, exception_when_existing,
        name, creator_id=creator.id,
        **kwargs
    )


@utils.supported_filters(optional_support_keys=UPDATED_FIELDS)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_CLUSTER
)
@utils.wrap_to_dict(RESP_FIELDS)
def update_cluster(session, updater, cluster_id, **kwargs):
    """Update a cluster."""
    cluster = utils.get_db_object(
        session, models.Cluster, id=cluster_id
    )
    is_cluster_editable(
        session, cluster, updater,
        reinstall_distributed_system_set=(
            kwargs.get('reinstall_distributed_system', False)
        )
    )
    return utils.update_db_object(session, cluster, **kwargs)


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_DEL_CLUSTER
)
@utils.wrap_to_dict(RESP_FIELDS)
def del_cluster(session, deleter, cluster_id, **kwargs):
    """Delete a cluster."""
    cluster = utils.get_db_object(
        session, models.Cluster, id=cluster_id
    )
    is_cluster_editable(session, cluster, deleter)
    return utils.del_db_object(session, cluster)


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_CLUSTER_CONFIG
)
@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
def get_cluster_config(session, getter, cluster_id, **kwargs):
    """Get cluster config."""
    return utils.get_db_object(
        session, models.Cluster, id=cluster_id
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_CLUSTER_CONFIG
)
@utils.wrap_to_dict(RESP_DEPLOYED_CONFIG_FIELDS)
def get_cluster_deployed_config(session, getter, cluster_id, **kwargs):
    """Get cluster deployed config."""
    return utils.get_db_object(
        session, models.Cluster, id=cluster_id
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_METADATAS
)
@utils.wrap_to_dict(RESP_METADATA_FIELDS)
def get_cluster_metadata(session, getter, cluster_id, **kwargs):
    """Get cluster metadata."""
    cluster = utils.get_db_object(
        session, models.Cluster, id=cluster_id
    )
    metadatas = {}
    os = cluster.os
    if os:
        metadatas['os_config'] = metadata_api.get_os_metadata_internal(
            os.id
        )
    adapter = cluster.adapter
    if adapter:
        metadatas['package_config'] = (
            metadata_api.get_package_metadata_internal(adapter.id)
        )
    return metadatas


@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_CLUSTER_CONFIG
)
@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
def _update_cluster_config(session, updater, cluster, **kwargs):
    """Update a cluster config."""
    is_cluster_editable(session, cluster, updater)
    return utils.update_db_object(
        session, cluster, **kwargs
    )


@utils.replace_filters(
    os_config='deployed_os_config',
    package_config='deployed_package_config'
)
@utils.supported_filters(
    optional_support_keys=UPDATED_DEPLOYED_CONFIG_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_CLUSTER_CONFIG
)
@utils.wrap_to_dict(RESP_DEPLOYED_CONFIG_FIELDS)
def update_cluster_deployed_config(
    session, updater, cluster_id, **kwargs
):
    """Update cluster deployed config."""
    cluster = utils.get_db_object(
        session, models.Cluster, id=cluster_id
    )
    is_cluster_editable(session, cluster, updater)
    is_cluster_validated(session, cluster)
    return utils.update_db_object(
        session, cluster, **kwargs
    )


@utils.replace_filters(
    os_config='put_os_config',
    package_config='put_package_config'
)
@utils.supported_filters(optional_support_keys=UPDATED_CONFIG_FIELDS)
@database.run_in_session()
def update_cluster_config(session, updater, cluster_id, **kwargs):
    """Update cluster config."""
    cluster = utils.get_db_object(
        session, models.Cluster, id=cluster_id
    )
    os_config_validates = functools.partial(
        metadata_api.validate_os_config, os_id=cluster.os_id)
    package_config_validates = functools.partial(
        metadata_api.validate_package_config, adapter_id=cluster.adapter_id)

    @utils.input_validates(
        put_os_config=os_config_validates,
        put_package_config=package_config_validates
    )
    def update_config_internal(
        cluster, **in_kwargs
    ):
        return _update_cluster_config(
            session, updater, cluster, **in_kwargs
        )

    return update_config_internal(
        cluster, **kwargs
    )


@utils.replace_filters(
    os_config='patched_os_config',
    package_config='patched_package_config'
)
@utils.supported_filters(optional_support_keys=PATCHED_CONFIG_FIELDS)
@database.run_in_session()
def patch_cluster_config(session, updater, cluster_id, **kwargs):
    """patch cluster config."""
    cluster = utils.get_db_object(
        session, models.Cluster, id=cluster_id
    )

    os_config_validates = functools.partial(
        metadata_api.validate_os_config, os_id=cluster.os_id)
    package_config_validates = functools.partial(
        metadata_api.validate_package_config, adapter_id=cluster.adapter_id)

    @utils.output_validates(
        os_config=os_config_validates,
        package_config=package_config_validates
    )
    def update_config_internal(cluster, **in_kwargs):
        return _update_cluster_config(
            session, updater, cluster, **in_kwargs
        )

    return update_config_internal(
        cluster, **kwargs
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_DEL_CLUSTER_CONFIG
)
@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
def del_cluster_config(session, deleter, cluster_id):
    """Delete a cluster config."""
    cluster = utils.get_db_object(
        session, models.Cluster, id=cluster_id
    )
    is_cluster_editable(session, cluster, deleter)
    return utils.update_db_object(
        session, cluster, os_config={},
        package_config={}, config_validated=False
    )


@utils.supported_filters(
    ADDED_HOST_FIELDS,
    optional_support_keys=UPDATED_HOST_FIELDS
)
def add_clusterhost_internal(
        session, cluster,
        exception_when_existing=False,
        machine_id=None, **kwargs
):
    from compass.db.api import host as host_api
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
        if host_api.is_host_editable(
            session, host, cluster.creator,
            reinstall_os_set=kwargs.get('reinstall_os', False),
            exception_when_not_editable=False
        ):
            if 'name' in host_dict:
                hostname = host_dict['name']
                host_by_name = utils.get_db_object(
                    session, models.Host, False, name=hostname
                )
                if host_by_name and host_by_name.id != host.id:
                    raise exception.InvalidParameter(
                        'host name %s exists in host %s' % (
                            hostname, host_by_name.to_dict()
                        )
                    )
            utils.update_db_object(
                session, host,
                **host_dict
            )
        else:
            logging.info('host %s is not editable', host.name)
    else:
        if 'name' in host_dict:
            hostname = host_dict['name']
            host = utils.get_db_object(
                session, models.Host, False, name=hostname
            )
            if host and host.machine_id != machine_id:
                raise exception.InvalidParameter(
                    'host name %s exists in host %s' % (
                        hostname, host.to_dict()
                    )
                )
        host = utils.add_db_object(
            session, models.Host, False, machine_id,
            os=cluster.os,
            os_installer=cluster.adapter.adapter_os_installer,
            creator=cluster.creator,
            **host_dict
        )
    return utils.add_db_object(
        session, models.ClusterHost, exception_when_existing,
        cluster.id, host.id, **clusterhost_dict
    )


def _add_clusterhosts(session, cluster, machines):
    for machine_dict in machines:
        add_clusterhost_internal(
            session, cluster, **machine_dict
        )


def _remove_clusterhosts(session, cluster, hosts):
    utils.del_db_objects(
        session, models.ClusterHost,
        cluster_id=cluster.id, host_id=hosts
    )


def _set_clusterhosts(session, cluster, machines):
    utils.del_db_objects(
        session, models.ClusterHost,
        cluster_id=cluster.id
    )
    for machine_dict in machines:
        add_clusterhost_internal(
            session, cluster, True, **machine_dict
        )


@utils.supported_filters(optional_support_keys=SUPPORTED_CLUSTERHOST_FIELDS)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_CLUSTERHOSTS
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_FIELDS)
def list_cluster_hosts(session, lister, cluster_id, **filters):
    """Get cluster host info."""
    return utils.list_db_objects(
        session, models.ClusterHost, cluster_id=cluster_id,
        **filters
    )


@utils.supported_filters(optional_support_keys=SUPPORTED_CLUSTERHOST_FIELDS)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_CLUSTERHOSTS
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_FIELDS)
def list_clusterhosts(session, lister, **filters):
    """Get cluster host info."""
    return utils.list_db_objects(
        session, models.ClusterHost, **filters
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_CLUSTERHOSTS
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_FIELDS)
def get_cluster_host(
    session, getter, cluster_id, host_id,
    exception_when_missing=True, **kwargs
):
    """Get clusterhost info."""
    return utils.get_db_object(
        session, models.ClusterHost,
        exception_when_missing,
        cluster_id=cluster_id, host_id=host_id
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_CLUSTERHOSTS
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_FIELDS)
def get_clusterhost(
    session, getter, clusterhost_id,
    exception_when_missing=True, **kwargs
):
    """Get clusterhost info."""
    return utils.get_db_object(
        session, models.ClusterHost,
        exception_when_missing,
        clusterhost_id=clusterhost_id
    )


@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_UPDATE_CLUSTER_HOSTS
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_FIELDS)
def add_cluster_host(
    session, creator, cluster_id,
    exception_when_existing=True, **kwargs
):
    """Add cluster host."""
    cluster = utils.get_db_object(
        session, models.Cluster, id=cluster_id
    )
    is_cluster_editable(session, cluster, creator)
    return add_clusterhost_internal(
        session, cluster, exception_when_existing,
        **kwargs
    )


@user_api.check_user_permission_in_session(
    permission.PERMISSION_UPDATE_CLUSTER_HOSTS
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_FIELDS)
def _update_clusterhost(session, updater, clusterhost, **kwargs):
    def roles_validates(roles):
        cluster_roles = []
        cluster = clusterhost.cluster
        flavor = cluster.flavor
        if not flavor:
            raise exception.InvalidParameter(
                'not flavor in cluster %s' % cluster.name
            )
        for flavor_roles in flavor.flavor_roles:
            cluster_roles.append(flavor_roles.role.name)
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

    return update_internal(
        clusterhost, **kwargs
    )

    is_cluster_editable(session, clusterhost.cluster, updater)
    return utils.update_db_object(
        session, clusterhost, **kwargs
    )


@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTERHOST_FIELDS
)
@database.run_in_session()
def update_cluster_host(
    session, updater, cluster_id, host_id,
    **kwargs
):
    """Update cluster host."""
    clusterhost = utils.get_db_object(
        session, models.ClusterHost, cluster_id=cluster_id, host_id=host_id
    )
    return _update_clusterhost(session, updater, clusterhost, **kwargs)


@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTERHOST_FIELDS
)
@database.run_in_session()
def update_clusterhost(
    session, updater, clusterhost_id,
    **kwargs
):
    """Update cluster host."""
    clusterhost = utils.get_db_object(
        session, models.ClusterHost, clusterhost_id=clusterhost_id
    )
    return _update_clusterhost(session, updater, clusterhost, **kwargs)


@utils.replace_filters(
    roles='patched_roles'
)
@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTERHOST_FIELDS
)
@database.run_in_session()
def patch_cluster_host(
    session, updater, cluster_id, host_id,
    **kwargs
):
    """Update cluster host."""
    clusterhost = utils.get_db_object(
        session, models.Cluster, cluster_id=cluster_id, host_id=host_id
    )
    return _update_clusterhost(session, updater, clusterhost, **kwargs)


@utils.replace_filters(
    roles='patched_roles'
)
@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTERHOST_FIELDS
)
@database.run_in_session()
def patch_clusterhost(
    session, updater, clusterhost_id,
    **kwargs
):
    """Update cluster host."""
    clusterhost = utils.get_db_object(
        session, models.Cluster, clusterhost_id=clusterhost_id
    )
    return _update_clusterhost(session, updater, clusterhost, **kwargs)


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_DEL_CLUSTER_HOST
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_FIELDS)
def del_cluster_host(session, deleter, cluster_id, host_id, **kwargs):
    """Delete cluster host."""
    clusterhost = utils.get_db_object(
        session, models.ClusterHost,
        cluster_id=cluster_id, host_id=host_id
    )
    return utils.del_db_object(
        session, clusterhost
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_DEL_CLUSTER_HOST
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_FIELDS)
def del_clusterhost(session, deleter, clusterhost_id, **kwargs):
    """Delete cluster host."""
    clusterhost = utils.get_db_object(
        session, models.ClusterHost,
        clusterhost_id=clusterhost_id
    )
    return utils.del_db_object(
        session, clusterhost
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_CLUSTERHOST_CONFIG
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_CONFIG_FIELDS)
def get_cluster_host_config(session, getter, cluster_id, host_id, **kwargs):
    """Get clusterhost config."""
    return utils.get_db_object(
        session, models.ClusterHost,
        cluster_id=cluster_id, host_id=host_id
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_CLUSTERHOST_CONFIG
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_DEPLOYED_CONFIG_FIELDS)
def get_cluster_host_deployed_config(
    session, getter, cluster_id, host_id, **kwargs
):
    """Get clusterhost deployed config."""
    return utils.get_db_object(
        session, models.ClusterHost,
        cluster_id=cluster_id, host_id=host_id
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_CLUSTERHOST_CONFIG
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_CONFIG_FIELDS)
def get_clusterhost_config(session, getter, clusterhost_id, **kwargs):
    """Get clusterhost config."""
    return utils.get_db_object(
        session, models.ClusterHost, clusterhost_id=clusterhost_id
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_CLUSTERHOST_CONFIG
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_DEPLOYED_CONFIG_FIELDS)
def get_clusterhost_deployed_config(session, getter, clusterhost_id, **kwargs):
    """Get clusterhost deployed config."""
    return utils.get_db_object(
        session, models.ClusterHost, clusterhost_id=clusterhost_id
    )


@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_CLUSTERHOST_CONFIG
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_CONFIG_FIELDS)
def _update_clusterhost_config(session, updater, clusterhost, **kwargs):
    from compass.db.api import host as host_api
    ignore_keys = []
    if host_api.is_host_editable(
        session, clusterhost.host, updater,
        exception_when_not_editable=False
    ):
        ignore_keys.append('put_os_config')

    def os_config_validates(os_config):
        from compass.db.api import host as host_api
        host = clusterhost.host
        metadata_api.validate_os_config(os_config, host.os_id)

    def package_config_validates(package_config):
        cluster = clusterhost.cluster
        is_cluster_editable(session, cluster, updater)
        metadata_api.validate_package_config(
            package_config, cluster.adapter_id
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


@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_CLUSTERHOST_CONFIG
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_DEPLOYED_CONFIG_FIELDS)
def _update_clusterhost_deployed_config(
    session, updater, clusterhost, **kwargs
):
    from compass.db.api import host as host_api
    ignore_keys = []
    if host_api.is_host_editable(
        session, clusterhost.host, updater,
        exception_when_not_editable=False
    ):
        ignore_keys.append('deployed_os_config')

    def os_config_validates(os_config):
        host = clusterhost.host
        host_api.is_host_validated(session, host)

    def package_config_validates(package_config):
        cluster = clusterhost.cluster
        is_cluster_editable(session, cluster, updater)
        is_clusterhost_validated(session, clusterhost)

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
def update_cluster_host_config(
    session, updater, cluster_id, host_id, **kwargs
):
    """Update clusterhost config."""
    clusterhost = utils.get_db_object(
        session, models.ClusterHost,
        cluster_id=cluster_id, host_id=host_id
    )
    return _update_clusterhost_config(
        session, updater, clusterhost, **kwargs
    )


@utils.replace_filters(
    os_config='deployed_os_config',
    package_config='deployed_package_config'
)
@database.run_in_session()
def update_cluster_host_deployed_config(
    session, updater, cluster_id, host_id, **kwargs
):
    """Update clusterhost deployed config."""
    clusterhost = utils.get_db_object(
        session, models.ClusterHost,
        cluster_id=cluster_id, host_id=host_id
    )
    return _update_clusterhost_deployed_config(
        session, updater, clusterhost, **kwargs
    )


@utils.replace_filters(
    os_config='put_os_config',
    package_config='put_package_config'
)
@database.run_in_session()
def update_clusterhost_config(
    session, updater, clusterhost_id, **kwargs
):
    """Update clusterhost config."""
    clusterhost = utils.get_db_object(
        session, models.ClusterHost, clusterhost_id=clusterhost_id
    )
    return _update_clusterhost_config(
        session, updater, clusterhost, **kwargs
    )


@utils.replace_filters(
    os_config='deployed_os_config',
    package_config='deployed_package_config'
)
@database.run_in_session()
def update_clusterhost_deployed_config(
    session, updater, clusterhost_id, **kwargs
):
    """Update clusterhost deployed config."""
    clusterhost = utils.get_db_object(
        session, models.ClusterHost, clusterhost_id=clusterhost_id
    )
    return _update_clusterhost_deployed_config(
        session, updater, clusterhost, **kwargs
    )


@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_CLUSTERHOST_CONFIG
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_CONFIG_FIELDS)
def _patch_clusterhost_config(session, updater, clusterhost, **kwargs):
    from compass.db.api import host as host_api
    ignore_keys = []
    if host_api.is_host_editable(
        session, clusterhost.host, updater,
        exception_when_not_editable=False
    ):
        ignore_keys.append('patched_os_config')

    def os_config_validates(os_config):
        host = clusterhost.host
        metadata_api.validate_os_config(os_config, host.os_id)

    def package_config_validates(package_config):
        cluster = clusterhost.cluster
        is_cluster_editable(session, cluster, updater)
        metadata_api.validate_package_config(
            package_config, cluster.adapter_id
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
def patch_cluster_host_config(
    session, updater, cluster_id, host_id, **kwargs
):
    """patch clusterhost config."""
    clusterhost = utils.get_db_object(
        session, models.ClusterHost,
        cluster_id=cluster_id, host_id=host_id
    )
    return _patch_clusterhost_config(
        session, updater, clusterhost, **kwargs
    )


@utils.replace_filters(
    os_config='patched_os_config',
    package_config='patched_package_config'
)
@database.run_in_session()
def patch_clusterhost_config(
    session, updater, clusterhost_id, **kwargs
):
    """patch clusterhost config."""
    clusterhost = utils.get_db_object(
        session, models.ClusterHost, clusterhost_id=clusterhost_id
    )
    return _patch_clusterhost_config(
        session, updater, clusterhost, **kwargs
    )


@user_api.check_user_permission_in_session(
    permission.PERMISSION_DEL_CLUSTERHOST_CONFIG
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_CONFIG_FIELDS)
def _delete_clusterhost_config(
    session, deleter, clusterhost
):
    from compass.db.api import host as host_api
    ignore_keys = []
    if host_api.is_host_editable(
        session, clusterhost.host, deleter,
        exception_when_not_editable=False
    ):
        ignore_keys.append('os_config')

    def package_config_validates(package_config):
        is_cluster_editable(session, clusterhost.cluster, deleter)

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
def delete_cluster_host_config(
    session, deleter, cluster_id, host_id
):
    """Delete a clusterhost config."""
    clusterhost = utils.get_db_object(
        session, models.ClusterHost,
        cluster_id=cluster_id, host_id=host_id
    )
    return _delete_clusterhost_config(
        session, deleter, clusterhost
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_DEL_CLUSTERHOST_CONFIG
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_CONFIG_FIELDS)
def delete_clusterhost_config(session, deleter, clusterhost_id):
    """Delet a clusterhost config."""
    clusterhost = utils.get_db_object(
        session, models.ClusterHost, clusterhost_id=clusterhost_id
    )
    return _delete_clusterhost_config(
        session, deleter, clusterhost
    )


@utils.supported_filters(
    optional_support_keys=['add_hosts', 'remove_hosts', 'set_hosts']
)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_UPDATE_CLUSTER_HOSTS
)
@utils.wrap_to_dict(
    ['hosts'],
    hosts=RESP_CLUSTERHOST_FIELDS
)
def update_cluster_hosts(
    session, updater, cluster_id, add_hosts={}, set_hosts=None,
    remove_hosts={}
):
    """Update cluster hosts."""
    cluster = utils.get_db_object(
        session, models.Cluster, id=cluster_id
    )
    is_cluster_editable(session, cluster, updater)
    if remove_hosts:
        _remove_clusterhosts(session, cluster, **remove_hosts)
    if add_hosts:
        _add_clusterhosts(session, cluster, **add_hosts)
    if set_hosts is not None:
        _set_clusterhosts(session, cluster, **set_hosts)
    return {
        'hosts': cluster.clusterhosts
    }


def validate_clusterhost(session, clusterhost):
    roles = clusterhost.roles
    if not roles:
        raise exception.InvalidParameter(
            'empty roles for clusterhost %s' % clusterhost.name
        )


def validate_cluster(session, cluster):
    if not cluster.clusterhosts:
        raise exception.InvalidParameter(
            '%s does not have any hosts' % cluster.name
        )
    cluster_roles = [
        flavor_role.role
        for flavor_role in cluster.flavor.flavor_roles
    ]
    necessary_roles = set([
        role.name for role in cluster_roles if not role.optional
    ])
    clusterhost_roles = set([])
    for clusterhost in cluster.clusterhosts:
        roles = clusterhost.roles
        for role in roles:
            clusterhost_roles.add(role.name)
    missing_roles = necessary_roles - clusterhost_roles
    if missing_roles:
        raise exception.InvalidParameter(
            'some roles %s are not assigned to any host in cluster %s' % (
                list(missing_roles), cluster.name
            )
        )


@utils.supported_filters(optional_support_keys=['review'])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_REVIEW_CLUSTER
)
@utils.wrap_to_dict(
    RESP_REVIEW_FIELDS,
    cluster=RESP_CONFIG_FIELDS,
    clusterhosts=RESP_CLUSTERHOST_CONFIG_FIELDS
)
def review_cluster(session, reviewer, cluster_id, review={}, **kwargs):
    """review cluster."""
    from compass.db.api import host as host_api
    cluster = utils.get_db_object(
        session, models.Cluster, id=cluster_id
    )
    is_cluster_editable(session, cluster, reviewer)
    host_ids = review.get('hosts', [])
    clusterhost_ids = review.get('clusterhosts', [])
    clusterhosts = []
    for clusterhost in cluster.clusterhosts:
        if (
            clusterhost.clusterhost_id in clusterhost_ids or
            clusterhost.host_id in host_ids
        ):
            clusterhosts.append(clusterhost)
    os_config = cluster.os_config
    if os_config:
        metadata_api.validate_os_config(
            os_config, cluster.os_id, True
        )
        for clusterhost in clusterhosts:
            host = clusterhost.host
            if not host_api.is_host_editable(
                session, host, reviewer, False
            ):
                logging.info(
                    'ignore update host %s config '
                    'since it is not editable' % host.name
                )
                continue
            host_os_config = host.os_config
            deployed_os_config = util.merge_dict(
                os_config, host_os_config
            )
            metadata_api.validate_os_config(
                deployed_os_config, host.os_id, True
            )
            host_api.validate_host(session, host)
            utils.update_db_object(session, host, config_validated=True)
    package_config = cluster.package_config
    if package_config:
        metadata_api.validate_package_config(
            package_config, cluster.adapter_id, True
        )
        for clusterhost in clusterhosts:
            clusterhost_package_config = clusterhost.package_config
            deployed_package_config = util.merge_dict(
                package_config, clusterhost_package_config
            )
            metadata_api.validate_package_config(
                deployed_package_config,
                cluster.adapter_id, True
            )
            validate_clusterhost(session, clusterhost)
            utils.update_db_object(session, clusterhost, config_validated=True)
    validate_cluster(session, cluster)
    utils.update_db_object(session, cluster, config_validated=True)
    return {
        'cluster': cluster,
        'hosts': clusterhosts
    }


@utils.supported_filters(optional_support_keys=['deploy'])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_DEPLOY_CLUSTER
)
@utils.wrap_to_dict(
    RESP_DEPLOY_FIELDS,
    cluster=RESP_CONFIG_FIELDS,
    clusterhosts=RESP_CLUSTERHOST_FIELDS
)
def deploy_cluster(
    session, deployer, cluster_id, deploy={}, **kwargs
):
    """deploy cluster."""
    from compass.db.api import host as host_api
    from compass.tasks import client as celery_client
    cluster = utils.get_db_object(
        session, models.Cluster, id=cluster_id
    )
    host_ids = deploy.get('hosts', [])
    clusterhost_ids = deploy.get('clusterhosts', [])
    clusterhosts = []
    for clusterhost in cluster.clusterhosts:
        if (
            clusterhost.clusterhost_id in clusterhost_ids or
            clusterhost.host_id in host_ids
        ):
            clusterhosts.append(clusterhost)
    is_cluster_editable(session, cluster, deployer)
    is_cluster_validated(session, cluster)
    utils.update_db_object(session, cluster.state, state='INITIALIZED')
    for clusterhost in clusterhosts:
        host = clusterhost.host
        if host_api.is_host_editable(
            session, host, deployer,
            exception_when_not_editable=False
        ):
            host_api.is_host_validated(
                session, host
            )
            utils.update_db_object(session, host.state, state='INITIALIZED')
        if cluster.distributed_system:
            is_clusterhost_validated(session, clusterhost)
            utils.update_db_object(
                session, clusterhost.state, state='INITIALIZED'
            )

    celery_client.celery.send_task(
        'compass.tasks.deploy_cluster',
        (
            deployer.email, cluster_id,
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
@user_api.check_user_permission_in_session(
    permission.PERMISSION_GET_CLUSTER_STATE
)
@utils.wrap_to_dict(RESP_STATE_FIELDS)
def get_cluster_state(session, getter, cluster_id, **kwargs):
    """Get cluster state info."""
    return utils.get_db_object(
        session, models.Cluster, id=cluster_id
    ).state_dict()


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_GET_CLUSTERHOST_STATE
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_STATE_FIELDS)
def get_cluster_host_state(
    session, getter, cluster_id, host_id, **kwargs
):
    """Get clusterhost state info."""
    return utils.get_db_object(
        session, models.ClusterHost,
        cluster_id=cluster_id, host_id=host_id
    ).state_dict()


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_GET_CLUSTERHOST_STATE
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_STATE_FIELDS)
def get_cluster_host_self_state(
    session, getter, cluster_id, host_id, **kwargs
):
    """Get clusterhost state info."""
    clusterhost = utils.get_db_object(
        session, models.ClusterHost,
        cluster_id=cluster_id, host_id=host_id
    )
    return utils.get_db_object(
        session, models.ClusterHostState,
        id=clusterhost.clusterhost_id
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_GET_CLUSTERHOST_STATE
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_STATE_FIELDS)
def get_clusterhost_state(
    session, getter, clusterhost_id, **kwargs
):
    """Get clusterhost state info."""
    return utils.get_db_object(
        session, models.ClusterHost,
        clusterhost_id=clusterhost_id
    ).state_dict()


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_GET_CLUSTERHOST_STATE
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_STATE_FIELDS)
def get_clusterhost_self_state(
    session, getter, clusterhost_id, **kwargs
):
    """Get clusterhost state info."""
    return utils.get_db_object(
        session, models.ClusterHost,
        clusterhost_id=clusterhost_id
    ).state


@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTERHOST_STATE_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_UPDATE_CLUSTERHOST_STATE
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_STATE_FIELDS)
def update_cluster_host_state(
    session, updater, cluster_id, host_id, **kwargs
):
    """Update a clusterhost state."""
    clusterhost = utils.get_db_object(
        session, models.ClusterHost,
        cluster_id=cluster_id, host_id=host_id
    )
    utils.update_db_object(session, clusterhost.state, **kwargs)
    return clusterhost.state_dict()


@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTERHOST_STATE_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_UPDATE_CLUSTERHOST_STATE
)
@utils.wrap_to_dict(RESP_CLUSTERHOST_STATE_FIELDS)
def update_clusterhost_state(
    session, updater, clusterhost_id, **kwargs
):
    """Update a clusterhost state."""
    clusterhost = utils.get_db_object(
        session, models.ClusterHost,
        clusterhost_id=clusterhost_id
    )
    utils.update_db_object(session, clusterhost.state, **kwargs)
    return clusterhost.state_dict()


@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTER_STATE_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_UPDATE_CLUSTER_STATE
)
@utils.wrap_to_dict(RESP_STATE_FIELDS)
def update_cluster_state(
    session, updater, cluster_id, **kwargs
):
    """Update a cluster state."""
    cluster = utils.get_db_object(
        session, models.Cluster, id=cluster_id
    )
    utils.update_db_object(session, cluster.state, **kwargs)
    return cluster.state_dict()


@utils.supported_filters([])
@database.run_in_session()
@utils.wrap_to_dict(RESP_CLUSTERHOST_LOG_FIELDS)
def get_cluster_host_log_histories(
    session, getter, cluster_id, host_id, **kwargs
):
    """Get clusterhost log history."""
    return utils.list_db_objects(
        session, models.ClusterHostLogHistory,
        cluster_id=cluster_id, host_id=host_id
    )


@utils.supported_filters([])
@database.run_in_session()
@utils.wrap_to_dict(RESP_CLUSTERHOST_LOG_FIELDS)
def get_clusterhost_log_histories(session, getter, clusterhost_id, **kwargs):
    """Get clusterhost log history."""
    return utils.list_db_objects(
        session, models.ClusterHostLogHistory, clusterhost_id=clusterhost_id
    )


@utils.supported_filters([])
@database.run_in_session()
@utils.wrap_to_dict(RESP_CLUSTERHOST_LOG_FIELDS)
def get_cluster_host_log_history(
    session, getter, cluster_id, host_id, filename, **kwargs
):
    """Get clusterhost log history."""
    return utils.get_db_object(
        session, models.ClusterHostLogHistory,
        cluster_id=cluster_id, host_id=host_id, filename=filename
    )


@utils.supported_filters([])
@database.run_in_session()
@utils.wrap_to_dict(RESP_CLUSTERHOST_LOG_FIELDS)
def get_clusterhost_log_history(
    session, getter, clusterhost_id, filename, **kwargs
):
    """Get host log history."""
    return utils.get_db_object(
        session, models.ClusterHostLogHistory,
        clusterhost_id=clusterhost_id, filename=filename
    )


@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTERHOST_LOG_FIELDS
)
@database.run_in_session()
@utils.wrap_to_dict(RESP_CLUSTERHOST_LOG_FIELDS)
def update_cluster_host_log_history(
    session, updater, cluster_id, host_id, filename, **kwargs
):
    """Update a host log history."""
    cluster_host_log_history = utils.get_db_object(
        session, models.HostLogHistory,
        cluster_id=cluster_id, host_id=host_id, filename=filename
    )
    return utils.update_db_object(session, cluster_host_log_history, **kwargs)


@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTERHOST_LOG_FIELDS
)
@database.run_in_session()
@utils.wrap_to_dict(RESP_CLUSTERHOST_LOG_FIELDS)
def update_clusterhost_log_history(
    session, updater, clusterhost_id, filename, **kwargs
):
    """Update a host log history."""
    clusterhost_log_history = utils.get_db_object(
        session, models.ClusterHostLogHistory,
        clusterhost_id=clusterhost_id, filename=filename
    )
    return utils.update_db_object(session, clusterhost_log_history, **kwargs)


@utils.supported_filters(
    ADDED_CLUSTERHOST_LOG_FIELDS,
    optional_support_keys=UPDATED_CLUSTERHOST_LOG_FIELDS
)
@database.run_in_session()
@utils.wrap_to_dict(RESP_CLUSTERHOST_LOG_FIELDS)
def add_clusterhost_log_history(
    session, creator, clusterhost_id, exception_when_existing=False,
    filename=None, **kwargs
):
    """add a host log history."""
    return utils.add_db_object(
        session, models.ClusterHostLogHistory, exception_when_existing,
        clusterhost_id, filename, **kwargs
    )


@utils.supported_filters(
    ADDED_CLUSTERHOST_LOG_FIELDS,
    optional_support_keys=UPDATED_CLUSTERHOST_LOG_FIELDS
)
@database.run_in_session()
@utils.wrap_to_dict(RESP_CLUSTERHOST_LOG_FIELDS)
def add_cluster_host_log_history(
    session, creator, cluster_id, host_id, exception_when_existing=False,
    filename=None, **kwargs
):
    """add a host log history."""
    clusterhost = utils.get_db_object(
        session, models.ClusterHost,
        cluster_id=cluster_id, host_id=host_id
    )
    return utils.add_db_object(
        session, models.ClusterHostLogHistory, exception_when_existing,
        clusterhost.clusterhost_id, filename, **kwargs
    )
