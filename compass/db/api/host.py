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

"""Host database operations."""
import logging

from compass.db.api import database
from compass.db.api import metadata_holder as metadata_api
from compass.db.api import permission
from compass.db.api import user as user_api
from compass.db.api import utils
from compass.db import exception
from compass.db import models


SUPPORTED_FIELDS = ['name', 'os_name', 'owner', 'mac']
RESP_FIELDS = [
    'id', 'name', 'os_name', 'owner', 'mac',
    'os_installed', 'networks', 'tag', 'location',
    'created_at', 'updated_at'
]
RESP_CLUSTER_FIELDS = [
    'id', 'name', 'os_name',
    'distributed_system_name', 'owner', 'adapter_id',
    'adapter_id', 'created_at', 'updated_at'
]
RESP_NETWORK_FIELDS = [
    'id', 'ip', 'interface', 'netmask', 'is_mgmt', 'is_promiscuous'
]
RESP_CONFIG_FIELDS = [
    'os_config',
]
UPDATED_FIELDS = ['name']
UPDATED_CONFIG_FIELDS = [
    'put_os_config'
]
PATCHED_CONFIG_FIELDS = [
    'patched_os_config'
]
ADDED_NETWORK_FIELDS = ['interface', 'ip', 'subnet_id']
OPTIONAL_ADDED_NETWORK_FIELDS = ['is_mgmt', 'is_promiscuous']
UPDATED_NETWORK_FIELDS = [
    'interface', 'ip', 'subnet_id', 'is_mgmt', 'is_promiscuous'
]
RESP_STATE_FIELDS = [
    'id', 'state', 'progress', 'message'
]
UPDATED_STATE_FIELDS = [
    'state', 'progress', 'message'
]


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters(optional_support_keys=SUPPORTED_FIELDS)
def list_hosts(lister, **filters):
    """List hosts."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, lister, permission.PERMISSION_LIST_HOSTS)
        return [
            host.to_dict()
            for host in utils.list_db_object(
                session, models.Host, **filters
            )
        ]


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters([])
def get_host(getter, host_id, **kwargs):
    """get host info."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_LIST_HOSTS)
        return utils.get_db_object(
            session, models.Host, id=host_id
        ).to_dict()


@utils.wrap_to_dict(RESP_CLUSTER_FIELDS)
@utils.supported_filters([])
def get_host_clusters(getter, host_id, **kwargs):
    """get host clusters."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_LIST_HOST_CLUSTERS)
        host = utils.get_db_object(
            session, models.Host, id=host_id
        )
        clusterhosts = host.clusterhosts
        return [clusterhost.cluster.to_dict() for clusterhost in clusterhosts]


def _conditional_exception(host, exception_when_not_editable):
    if exception_when_not_editable:
        raise exception.Forbidden(
            'host %s is not editable' % host.name
        )
    else:
        return False


def is_host_editable(
    session, host, user,
    reinstall_os_set=False, exception_when_not_editable=True
):
    with session.begin(subtransactions=True):
        if reinstall_os_set:
            if host.state.state == 'INSTALLING':
                return _conditional_exception(
                    host, exception_when_not_editable
                )
        elif not host.reinstall_os:
            return _conditional_exception(
                host, exception_when_not_editable
            )
        if not user.is_admin and host.creator_id != user.id:
            return _conditional_exception(
                host, exception_when_not_editable
            )
    return True


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters(UPDATED_FIELDS)
def update_host(updater, host_id, **kwargs):
    """Update a host."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_UPDATE_HOST)
        host = utils.get_db_object(
            session, models.Host, id=host_id
        )
        is_host_editable(
            session, host, updater,
            reinstall_os_set=kwargs.get('reinstall_os', False)
        )
        utils.update_db_object(session, host, **kwargs)
        return host.to_dict()


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters([])
def del_host(deleter, host_id, **kwargs):
    """Delete a host."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, deleter, permission.PERMISSION_DEL_HOST)
        host = utils.get_db_object(
            session, models.Host, id=host_id
        )
        is_host_editable(session, host, deleter)
        utils.del_db_object(session, host)
        return host.to_dict()


@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
@utils.supported_filters([])
def get_host_config(getter, host_id, **kwargs):
    """Get host config."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_LIST_HOST_CONFIG)
        return utils.get_db_object(
            session, models.Host, id=host_id
        ).to_dict()


def _update_host_config(updater, host_id, **kwargs):
    """Update host config."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_ADD_HOST_CONFIG)
        host = utils.get_db_object(
            session, models.Host, id=host_id
        )
        is_host_editable(session, host, updater)
        utils.update_db_object(session, host, config_validated=False, **kwargs)
        os_config = host.os_config
        if os_config:
            metadata_api.validate_os_config(
                os_config, host.adapter_id
            )
        return host.to_dict()


@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
@utils.supported_filters(UPDATED_CONFIG_FIELDS)
def update_host_config(updater, host_id, **kwargs):
    return _update_host_config(updater, host_id, **kwargs)


@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
@utils.supported_filters(PATCHED_CONFIG_FIELDS)
def patch_host_config(updater, host_id, **kwargs):
    return _update_host_config(updater, host_id, **kwargs)


@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
@utils.supported_filters([])
def del_host_config(deleter, host_id):
    """delete a host config."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, deleter, permission.PERMISSION_DEL_HOST_CONFIG)
        host = utils.get_db_object(
            session, models.Host, id=host_id
        )
        is_host_editable(session, host, deleter)
        utils.update_db_object(
            session, host, os_config={}, config_validated=False
        )
        return host.to_dict()


@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
@utils.supported_filters([])
def list_host_networks(lister, host_id):
    """Get host networks."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, lister, permission.PERMISSION_LIST_HOST_NETWORKS)
        host_networks = utils.list_db_objects(
            session, models.HostNetwork, host_id=host_id
        )
        return [host_network.to_dict() for host_network in host_networks]


@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
@utils.supported_filters(
    ADDED_NETWORK_FIELDS, optional_support_keys=OPTIONAL_ADDED_NETWORK_FIELDS
)
def add_host_network(creator, host_id, **kwargs):
    """Create a host network."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, creator, permission.PERMISSION_ADD_HOST_NETWORK)
        host = utils.get_db_object(
            session, models.Host, id=host_id
        )
        is_host_editable(session, host, creator)
        host_network = utils.add_db_object(
            session, models.HostNetwork, True,
            host_id, **kwargs
        )
        return host_network.to_dict()


@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
@utils.supported_filters(UPDATED_NETWORK_FIELDS)
def update_host_network(updater, host_network_id, **kwargs):
    """Update a host network."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_ADD_HOST_NETWORK)
        host_network = utils.get_db_object(
            session, models.HostNetwork, id=host_network_id
        )
        is_host_editable(session, host_network.host, updater)
        utils.update_db_object(session, host_network, **kwargs)
        return host_network.to_dict()


@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
@utils.supported_filters([])
def del_host_network(deleter, host_network_id, **kwargs):
    """Delete a host network."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, deleter, permission.PERMISSION_DEL_HOST_NETWORK)
        host_network = utils.get_db_object(
            session, models.HostNetwork, id=host_network_id
        )
        is_host_editable(session, host_network.host, deleter)
        utils.del_db_object(session, host_network)
        return host_network.to_dict()


@utils.wrap_to_dict(RESP_STATE_FIELDS)
@utils.supported_filters([])
def get_host_state(getter, host_id, **kwargs):
    """Get host state info."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_GET_HOST_STATE)
        return utils.get_db_object(
            session, models.Host, id=host_id
        ).state_dict()


@utils.wrap_to_dict(RESP_STATE_FIELDS)
@utils.supported_filters(UPDATED_STATE_FIELDS)
def update_host_state(updater, host_id, **kwargs):
    """Update a host state."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_UPDATE_HOST_STATE)
        host = utils.get_db_object(
            session, models.Host, id=host_id
        )
        is_host_editable(session, host, updater)
        utils.update_db_object(session, host.state, **kwargs)
        return host.state_dict()
