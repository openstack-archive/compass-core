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
    'id', 'name', 'os_name', 'reinstall_distributed_system',
    'distributed_system_name', 'distributed_system_installed',
    'owner', 'adapter_id',
    'created_at', 'updated_at'
]
RESP_CLUSTERHOST_FIELDS = [
    'id', 'host_id', 'machine_id', 'name', 'cluster_id',
    'mac', 'os_installed', 'distributed_system_installed',
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
RESP_CLUSTERHOST_CONFIG_FIELDS = [
    'package_config',
    'config_step',
    'config_validated',
    'created_at',
    'updated_at'
]
RESP_STATE_FIELDS = [
    'id', 'state', 'progress', 'message',
    'created_at', 'updated_at'
]
RESP_CLUSTERHOST_STATE_FIELDS = [
    'id', 'state', 'progress', 'message',
    'created_at', 'updated_at'
]
RESP_REVIEW_FIELDS = [
    'cluster', 'hosts'
]
RESP_ACTION_FIELDS = [
    'status', 'details'
]
ADDED_FIELDS = ['name', 'adapter_id']
UPDATED_FIELDS = ['name', 'reinstall_distributed_system']
ADDED_CLUSTERHOST_FIELDS = ['machine_id']
UPDATED_CLUSTERHOST_FIELDS = ['name', 'reinstall_os']
UPDATED_HOST_FIELDS = ['name', 'reinstall_os']
UPDATED_CONFIG_FIELDS = [
    'put_os_config', 'put_package_config', 'config_step'
]
PATCHED_CONFIG_FIELDS = [
    'patched_os_config', 'patched_package_config', 'config_step'
]
UPDATED_CLUSTERHOST_CONFIG_FIELDS = [
    'put_package_config'
]
PATCHED_CLUSTERHOST_CONFIG_FIELDS = [
    'patched_package_config'
]
UPDATED_CLUSTERHOST_STATE_FIELDS = [
    'state', 'progress', 'message'
]


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters(optional_support_keys=SUPPORTED_FIELDS)
def list_clusters(lister, **filters):
    """List clusters."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, lister, permission.PERMISSION_LIST_CLUSTERS)
        return [
            cluster.to_dict()
            for cluster in utils.list_db_objects(
                session, models.Cluster, **filters
            )
        ]


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters([])
def get_cluster(getter, cluster_id, **kwargs):
    """Get cluster info."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_LIST_CLUSTERS)
        return utils.get_db_object(
            session, models.Cluster, id=cluster_id
        ).to_dict()


def _conditional_exception(cluster, exception_when_not_editable):
    if exception_when_not_editable:
        raise exception.Forbidden(
            'cluster %s is not editable' % cluster.name
        )
    else:
        return False


def is_cluster_editable(
    session, cluster, user,
    reinstall_distributed_system_set=False,
    exception_when_not_editable=True
):
    with session.begin(subtransactions=True):
        if reinstall_distributed_system_set:
            if cluster.state.state == 'INSTALLING':
                return _conditional_exception(
                    cluster, exception_when_not_editable
                )
        elif not cluster.reinstall_distributed_system:
            return _conditional_exception(
                cluster, exception_when_not_editable
            )
        if not user.is_admin and cluster.creator_id != user.id:
            return _conditional_exception(
                cluster, exception_when_not_editable
            )
    return True


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters(ADDED_FIELDS)
def add_cluster(creator, name, adapter_id, **kwargs):
    """Create a cluster."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, creator, permission.PERMISSION_ADD_CLUSTER)
        cluster = utils.add_db_object(
            session, models.Cluster, True,
            name, adapter_id=adapter_id, creator_id=creator.id, **kwargs
        )
        cluster_dict = cluster.to_dict()
        return cluster_dict


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters(optional_support_keys=UPDATED_FIELDS)
def update_cluster(updater, cluster_id, **kwargs):
    """Update a cluster."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_ADD_CLUSTER)
        cluster = utils.get_db_object(
            session, models.Cluster, id=cluster_id
        )
        is_cluster_editable(
            session, cluster, updater,
            reinstall_distributed_system_set=(
                kwargs.get('reinstall_distributed_system', False)
            )
        )
        utils.update_db_object(session, cluster, **kwargs)
        return cluster.to_dict()


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters([])
def del_cluster(deleter, cluster_id, **kwargs):
    """Delete a cluster."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, deleter, permission.PERMISSION_DEL_CLUSTER)
        cluster = utils.get_db_object(
            session, models.Cluster, id=cluster_id
        )
        is_cluster_editable(session, cluster, deleter)
        utils.del_db_object(session, cluster)
        return cluster.to_dict()


@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
@utils.supported_filters([])
def get_cluster_config(getter, cluster_id, **kwargs):
    """Get cluster config."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_LIST_CLUSTER_CONFIG)
        return utils.get_db_object(
            session, models.Cluster, id=cluster_id
        ).to_dict()


def update_cluster_config_internal(session, updater, cluster, **kwargs):
    """Update a cluster config."""
    with session.begin(subtransactions=True):
        is_cluster_editable(session, cluster, updater)
        utils.update_db_object(
            session, cluster, config_validated=False, **kwargs
        )
        os_config = cluster.os_config
        if os_config:
            metadata_api.validate_os_config(
                os_config, cluster.adapter_id
            )
        package_config = cluster.package_config
        if package_config:
            metadata_api.validate_package_config(
                package_config, cluster.adapter_id
            )


@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
@utils.supported_filters(optional_support_keys=UPDATED_CONFIG_FIELDS)
def update_cluster_config(updater, cluster_id, **kwargs):
    """Update cluster config."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_ADD_CLUSTER_CONFIG)
        cluster = utils.get_db_object(
            session, models.Cluster, id=cluster_id
        )
        update_cluster_config_internal(
            session, updater, cluster, **kwargs
        )
        return cluster.to_dict()


@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
@utils.supported_filters(optional_support_keys=PATCHED_CONFIG_FIELDS)
def patch_cluster_config(updater, cluster_id, **kwargs):
    """patch cluster config."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_ADD_CLUSTER_CONFIG)
        cluster = utils.get_db_object(
            session, models.Cluster, id=cluster_id
        )
        update_cluster_config_internal(
            session, updater, cluster, **kwargs
        )
        return cluster.to_dict()


@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
@utils.supported_filters([])
def del_cluster_config(deleter, cluster_id):
    """Delete a cluster config."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, deleter, permission.PERMISSION_DEL_CLUSTER_CONFIG)
        cluster = utils.get_db_object(
            session, models.Cluster, id=cluster_id
        )
        is_cluster_editable(session, cluster, deleter)
        utils.update_db_object(
            session, cluster, os_config={},
            package_config={}, config_validated=False
        )
        return cluster.to_dict()


@utils.supported_filters(
    ADDED_CLUSTERHOST_FIELDS,
    optional_support_keys=UPDATED_CLUSTERHOST_FIELDS
)
def add_clusterhost_internal(
        session, cluster,
        exception_when_existing=False,
        machine_id=None, **kwargs
):
    from compass.db.api import host as host_api
    host_dict = {}
    clusterhost_dict = {}
    for key, value in kwargs.items():
        if key in UPDATED_HOST_FIELDS:
            host_dict[key] = value
        else:
            clusterhost_dict[key] = value
    with session.begin(subtransactions=True):
        host = utils.get_db_object(
            session, models.Host, False, id=machine_id
        )
        if host:
            if host_api.is_host_editable(
                session, host, cluster.creator,
                reinstall_os_set=host_dict.get('reinstall_os', False),
                exception_when_not_editable=False
            ):
                utils.update_db_object(
                    session, host, adapter=cluster.adapter.os_adapter,
                    **host_dict
                )
            else:
                logging.info('host %s is not editable', host.name)
        else:
            utils.add_db_object(
                session, models.Host, False, machine_id,
                os=cluster.os,
                adapter=cluster.adapter.os_adapter,
                creator=cluster.creator,
                **host_dict
            )
        return utils.add_db_object(
            session, models.ClusterHost, exception_when_existing,
            cluster.id, machine_id, **clusterhost_dict
        )


def _add_clusterhosts(session, cluster, machine_dicts):
    with session.begin(subtransactions=True):
        for machine_dict in machine_dicts:
            add_clusterhost_internal(
                session, cluster,
                **machine_dict
            )


def _remove_clusterhosts(session, cluster, host_ids):
    with session.begin(subtransactions=True):
        utils.del_db_objects(
            session, models.ClusterHost,
            cluster_id=cluster.id, host_id=host_ids
        )


def _set_clusterhosts(session, cluster, machine_dicts):
    with session.begin(subtransactions=True):
        utils.del_db_objects(
            session, models.ClusterHost,
            cluster_id=cluster.id
        )
        for machine_dict in machine_dicts:
            add_clusterhost_internal(
                session, cluster,
                True, **machine_dict
            )


@utils.wrap_to_dict(RESP_CLUSTERHOST_FIELDS)
@utils.supported_filters(optional_support_keys=SUPPORTED_CLUSTERHOST_FIELDS)
def list_cluster_hosts(lister, cluster_id, **filters):
    """Get cluster host info."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, lister, permission.PERMISSION_LIST_CLUSTERHOSTS)
        return [
            clusterhost.to_dict()
            for clusterhost in utils.list_db_objects(
                session, models.ClusterHost, cluster_id=cluster_id,
                **filters
            )
        ]


@utils.wrap_to_dict(RESP_CLUSTERHOST_FIELDS)
@utils.supported_filters(optional_support_keys=SUPPORTED_CLUSTERHOST_FIELDS)
def list_clusterhosts(lister, **filters):
    """Get cluster host info."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, lister, permission.PERMISSION_LIST_CLUSTERHOSTS)
        return [
            clusterhost.to_dict()
            for clusterhost in utils.list_db_objects(
                session, models.ClusterHost,
                **filters
            )
        ]


@utils.wrap_to_dict(RESP_CLUSTERHOST_FIELDS)
@utils.supported_filters([])
def get_cluster_host(getter, cluster_id, host_id, **kwargs):
    """Get clusterhost info."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_LIST_CLUSTERHOSTS)
        return utils.get_db_object(
            session, models.ClusterHost,
            cluster_id=cluster_id, host_id=host_id
        ).to_dict()


@utils.wrap_to_dict(RESP_CLUSTERHOST_FIELDS)
@utils.supported_filters([])
def get_clusterhost(getter, clusterhost_id, **kwargs):
    """Get clusterhost info."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_LIST_CLUSTERHOSTS)
        return utils.get_db_object(
            session, models.ClusterHost, id=clusterhost_id
        ).to_dict()


@utils.wrap_to_dict(RESP_CLUSTERHOST_FIELDS)
@utils.supported_filters(
    ADDED_CLUSTERHOST_FIELDS,
    optional_support_keys=UPDATED_CLUSTERHOST_FIELDS
)
def add_cluster_host(creator, cluster_id, machine_id, **kwargs):
    """Add cluster host."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, creator, permission.PERMISSION_UPDATE_CLUSTER_HOSTS)
        cluster = utils.get_db_object(
            session, models.Cluster, id=cluster_id
        )
        clusterhost = add_clusterhost_internal(
            session, cluster, True,
            machine_id=machine_id, **kwargs
        )
        return clusterhost.to_dict()


@utils.wrap_to_dict(RESP_CLUSTERHOST_FIELDS)
@utils.supported_filters([])
def del_cluster_host(deleter, cluster_id, host_id, **kwargs):
    """Delete cluster host."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, deleter, permission.PERMISSION_DEL_CLUSTER_HOST)
        clusterhost = utils.get_db_object(
            session, models.ClusterHost,
            cluster_id=cluster_id, host_id=host_id
        )
        utils.del_db_object(
            session, clusterhost
        )
        return clusterhost.to_dict()


@utils.wrap_to_dict(RESP_CLUSTERHOST_FIELDS)
@utils.supported_filters([])
def del_clusterhost(deleter, clusterhost_id, **kwargs):
    """Delete cluster host."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, deleter, permission.PERMISSION_DEL_CLUSTER_HOST)
        clusterhost = utils.get_db_object(
            session, models.ClusterHost,
            id=clusterhost_id
        )
        utils.del_db_object(
            session, clusterhost
        )
        return clusterhost.to_dict()


@utils.wrap_to_dict(RESP_CLUSTERHOST_CONFIG_FIELDS)
@utils.supported_filters([])
def get_cluster_host_config(getter, cluster_id, host_id, **kwargs):
    """Get clusterhost config."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_LIST_CLUSTERHOST_CONFIG)
        return utils.get_db_object(
            session, models.ClusterHost,
            cluster_id=cluster_id, host_id=host_id
        ).to_dict()


@utils.wrap_to_dict(RESP_CLUSTERHOST_CONFIG_FIELDS)
@utils.supported_filters([])
def get_clusterhost_config(getter, clusterhost_id, **kwargs):
    """Get clusterhost config."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_LIST_CLUSTERHOST_CONFIG)
        return utils.get_db_object(
            session, models.ClusterHost, id=clusterhost_id
        ).to_dict()


def update_clusterhost_config_internal(
    session, updater, clusterhost, **kwargs
):
    """Update clusterhost config internal."""
    with session.begin(subtransactions=True):
        is_cluster_editable(session, clusterhost.cluster, updater)
        utils.update_db_object(
            session, clusterhost, config_validated=False, **kwargs
        )
        package_config = clusterhost.package_config
        if package_config:
            metadata_api.validate_package_config(
                package_config, clusterhost.cluster.adapter_id
            )


@utils.wrap_to_dict(RESP_CLUSTERHOST_CONFIG_FIELDS)
@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTERHOST_CONFIG_FIELDS
)
def update_cluster_host_config(updater, cluster_id, host_id, **kwargs):
    """Update clusterhost config."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_ADD_CLUSTERHOST_CONFIG)
        clusterhost = utils.get_db_object(
            session, models.ClusterHost,
            cluster_id=cluster_id, host_id=host_id
        )
        update_clusterhost_config_internal(
            session, updater, clusterhost, **kwargs
        )
        return clusterhost.to_dict()


@utils.wrap_to_dict(RESP_CLUSTERHOST_CONFIG_FIELDS)
@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTERHOST_CONFIG_FIELDS
)
def update_clusterhost_config(updater, clusterhost_id, **kwargs):
    """Update clusterhost config."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_ADD_CLUSTERHOST_CONFIG)
        clusterhost = utils.get_db_object(
            session, models.ClusterHost, id=clusterhost_id
        )
        update_clusterhost_config_internal(
            session, updater, clusterhost, **kwargs
        )
        return clusterhost.to_dict()


@utils.wrap_to_dict(RESP_CLUSTERHOST_CONFIG_FIELDS)
@utils.supported_filters(PATCHED_CLUSTERHOST_CONFIG_FIELDS)
def patch_cluster_host_config(updater, cluster_id, host_id, **kwargs):
    """patch clusterhost config."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_ADD_CLUSTERHOST_CONFIG)
        clusterhost = utils.get_db_object(
            session, models.ClusterHost,
            cluster_id=cluster_id, host_id=host_id
        )
        update_clusterhost_config_internal(
            session, updater, clusterhost, **kwargs
        )
        return clusterhost.to_dict()


@utils.wrap_to_dict(RESP_CLUSTERHOST_CONFIG_FIELDS)
@utils.supported_filters(PATCHED_CLUSTERHOST_CONFIG_FIELDS)
def patch_clusterhost_config(updater, clusterhost_id, **kwargs):
    """patch clusterhost config."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_ADD_CLUSTERHOST_CONFIG)
        clusterhost = utils.get_db_object(
            session, models.ClusterHost, id=clusterhost_id
        )
        update_clusterhost_config_internal(
            session, updater, clusterhost, **kwargs
        )
        return clusterhost.to_dict()


@utils.wrap_to_dict(RESP_CLUSTERHOST_CONFIG_FIELDS)
@utils.supported_filters([])
def delete_cluster_host_config(deleter, cluster_id, host_id):
    """Delet a clusterhost config."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, deleter, permission.PERMISSION_DEL_CLUSTERHOST_CONFIG)
        clusterhost = utils.get_db_object(
            session, models.ClusterHost,
            cluster_id=cluster_id, hsot_id=host_id
        )
        is_cluster_editable(session, clusterhost.cluster, deleter)
        utils.update_db_object(
            session, clusterhost, package_config={}, config_validated=False
        )
        return clusterhost.to_dict()


@utils.wrap_to_dict(RESP_CLUSTERHOST_CONFIG_FIELDS)
@utils.supported_filters([])
def delete_clusterhost_config(deleter, clusterhost_id):
    """Delet a clusterhost config."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, deleter, permission.PERMISSION_DEL_CLUSTERHOST_CONFIG)
        clusterhost = utils.get_db_object(
            session, models.ClusterHost, id=clusterhost_id
        )
        is_cluster_editable(session, clusterhost.cluster, deleter)
        utils.update_db_object(
            session, clusterhost, package_config={}, config_validated=False
        )
        return clusterhost.to_dict()


@utils.wrap_to_dict(RESP_CLUSTERHOST_FIELDS)
@utils.supported_filters(
    optional_support_keys=['add_hosts', 'remove_hosts', 'set_hosts']
)
def update_cluster_hosts(
    updater, cluster_id, add_hosts=[], set_hosts=None,
    remove_hosts=[]
):
    """Update cluster hosts."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_UPDATE_CLUSTER_HOSTS)
        cluster = utils.get_db_object(
            session, models.Cluster, id=cluster_id
        )
        is_cluster_editable(session, cluster, updater)
        if remove_hosts:
            _remove_clusterhosts(session, cluster, remove_hosts)
        if add_hosts:
            _add_clusterhosts(session, cluster, add_hosts)
        if set_hosts is not None:
            _set_clusterhosts(session, cluster, set_hosts)
        return [host.to_dict() for host in cluster.clusterhosts]


@utils.wrap_to_dict(RESP_REVIEW_FIELDS)
@utils.supported_filters([])
def review_cluster(reviewer, cluster_id):
    """review cluster."""
    from compass.db.api import host as host_api
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, reviewer, permission.PERMISSION_REVIEW_CLUSTER)
        cluster = utils.get_db_object(
            session, models.Cluster, id=cluster_id
        )
        is_cluster_editable(session, cluster, reviewer)
        os_config = cluster.os_config
        if os_config:
            metadata_api.validate_os_config(
                os_config, cluster.adapter_id, True
            )
            for clusterhost in cluster.clusterhosts:
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
                    deployed_os_config, host.adapter_id, True
                )
                host.deployed_os_config = deployed_os_config
                host.config_validated = True
        package_config = cluster.package_config
        if package_config:
            metadata_api.validate_package_config(
                package_config, cluster.adapter_id, True
            )
            for clusterhost in cluster.clusterhosts:
                clusterhost_package_config = clusterhost.package_config
                deployed_package_config = util.mrege_dict(
                    package_config, clusterhost_package_config
                )
                metadata_api.validate_os_config(
                    deployed_package_config,
                    cluster.adapter_id, True
                )
                clusterhost.deployed_package_config = deployed_package_config
                clusterhost.config_validated = True
        cluster.config_validated = True
        return {
            'cluster': cluster.to_dict(),
            'clusterhosts': [
                clusterhost.to_dict()
                for clusterhost in cluster.clusterhosts
            ]
        }


@utils.wrap_to_dict(RESP_ACTION_FIELDS)
@utils.supported_filters(optional_support_keys=['clusterhosts'])
def deploy_cluster(deployer, cluster_id, clusterhosts=[], **kwargs):
    """deploy cluster."""
    from compass.tasks import client as celery_client
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, deployer, permission.PERMISSION_DEPLOY_CLUSTER)
        cluster = utils.get_db_object(
            session, models.Cluster, id=cluster_id
        )
        is_cluster_editable(session, cluster, deployer)
        celery_client.celery.send_task(
            'compass.tasks.deploy',
            (cluster_id, clusterhosts)
        )
        return {
            'status': 'deploy action sent',
            'details': {
            }
        }


@utils.wrap_to_dict(RESP_STATE_FIELDS)
@utils.supported_filters([])
def get_cluster_state(getter, cluster_id, **kwargs):
    """Get cluster state info."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_GET_CLUSTER_STATE)
        return utils.get_db_object(
            session, models.Cluster, id=cluster_id
        ).state_dict()


@utils.wrap_to_dict(RESP_CLUSTERHOST_STATE_FIELDS)
@utils.supported_filters([])
def get_cluster_host_state(getter, cluster_id, host_id, **kwargs):
    """Get clusterhost state info."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_GET_CLUSTERHOST_STATE)
        return utils.get_db_object(
            session, models.ClusterHost,
            cluster_id=cluster_id, host_id=host_id
        ).state_dict()


@utils.wrap_to_dict(RESP_CLUSTERHOST_STATE_FIELDS)
@utils.supported_filters([])
def get_clusterhost_state(getter, clusterhost_id, **kwargs):
    """Get clusterhost state info."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_GET_CLUSTERHOST_STATE)
        return utils.get_db_object(
            session, models.ClusterHost, id=clusterhost_id
        ).state_dict()


@utils.wrap_to_dict(RESP_CLUSTERHOST_STATE_FIELDS)
@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTERHOST_STATE_FIELDS
)
def update_cluster_host_state(updater, cluster_id, host_id, **kwargs):
    """Update a clusterhost state."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_UPDATE_CLUSTERHOST_STATE)
        clusterhost = utils.get_db_object(
            session, models.ClusterHost,
            cluster_id=cluster_id, host_id=host_id
        )
        utils.update_db_object(session, clusterhost.state, **kwargs)
        return clusterhost.state_dict()


@utils.wrap_to_dict(RESP_CLUSTERHOST_STATE_FIELDS)
@utils.supported_filters(
    optional_support_keys=UPDATED_CLUSTERHOST_STATE_FIELDS
)
def update_clusterhost_state(updater, clusterhost_id, **kwargs):
    """Update a clusterhost state."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_UPDATE_CLUSTERHOST_STATE)
        clusterhost = utils.get_db_object(
            session, models.ClusterHost, id=clusterhost_id
        )
        is_cluster_editable(session, clusterhost.cluster, updater)
        return clusterhost.state_dict()
