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
import functools
import logging
import netaddr
import re

from compass.db.api import database
from compass.db.api import metadata_holder as metadata_api
from compass.db.api import permission
from compass.db.api import user as user_api
from compass.db.api import utils
from compass.db import exception
from compass.db import models
from compass.utils import util


SUPPORTED_FIELDS = ['name', 'os_name', 'owner', 'mac', 'id']
SUPPORTED_MACHINE_HOST_FIELDS = [
    'mac', 'tag', 'location', 'os_name', 'os_id'
]
SUPPORTED_NETOWORK_FIELDS = [
    'interface', 'ip', 'is_mgmt', 'is_promiscuous'
]
RESP_FIELDS = [
    'id', 'name', 'hostname', 'os_name', 'owner', 'mac',
    'switch_ip', 'port', 'switches', 'os_installer', 'os_id', 'ip',
    'reinstall_os', 'os_installed', 'tag', 'location', 'networks',
    'created_at', 'updated_at'
]
RESP_CLUSTER_FIELDS = [
    'id', 'name', 'os_name', 'reinstall_distributed_system',
    'owner', 'adapter_name', 'flavor_name',
    'distributed_system_installed', 'created_at', 'updated_at'
]
RESP_NETWORK_FIELDS = [
    'id', 'ip', 'interface', 'netmask', 'is_mgmt', 'is_promiscuous',
    'created_at', 'updated_at'
]
RESP_CONFIG_FIELDS = [
    'os_config',
    'config_setp',
    'config_validated',
    'networks',
    'created_at',
    'updated_at'
]
RESP_DEPLOYED_CONFIG_FIELDS = [
    'deployed_os_config'
]
RESP_DEPLOY_FIELDS = [
    'status', 'host'
]
UPDATED_FIELDS = ['name', 'reinstall_os']
UPDATED_CONFIG_FIELDS = [
    'put_os_config'
]
PATCHED_CONFIG_FIELDS = [
    'patched_os_config'
]
UPDATED_DEPLOYED_CONFIG_FIELDS = [
    'deployed_os_config'
]
ADDED_NETWORK_FIELDS = [
    'interface', 'ip', 'subnet_id'
]
OPTIONAL_ADDED_NETWORK_FIELDS = ['is_mgmt', 'is_promiscuous']
UPDATED_NETWORK_FIELDS = [
    'interface', 'ip', 'subnet_id', 'subnet', 'is_mgmt',
    'is_promiscuous'
]
IGNORE_FIELDS = [
    'id', 'created_at', 'updated_at'
]
RESP_STATE_FIELDS = [
    'id', 'state', 'percentage', 'message', 'severity', 'ready'
]
UPDATED_STATE_FIELDS = [
    'state', 'percentage', 'message', 'severity'
]
UPDATED_STATE_INTERNAL_FIELDS = [
    'ready'
]
RESP_LOG_FIELDS = [
    'id', 'filename', 'position', 'partial_line', 'percentage',
    'message', 'severity', 'line_matcher_name'
]
ADDED_LOG_FIELDS = [
    'filename'
]
UPDATED_LOG_FIELDS = [
    'position', 'partial_line', 'percentage',
    'message', 'severity', 'line_matcher_name'
]


@utils.supported_filters(optional_support_keys=SUPPORTED_FIELDS)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_HOSTS
)
@utils.wrap_to_dict(RESP_FIELDS)
def list_hosts(user=None, session=None, **filters):
    """List hosts."""
    return utils.list_db_objects(
        session, models.Host, **filters
    )


@utils.supported_filters(
    optional_support_keys=SUPPORTED_MACHINE_HOST_FIELDS)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_HOSTS
)
@utils.output_filters(
    missing_ok=True,
    tag=utils.general_filter_callback,
    location=utils.general_filter_callback,
    os_name=utils.general_filter_callback,
    os_id=utils.general_filter_callback
)
@utils.wrap_to_dict(RESP_FIELDS)
def list_machines_or_hosts(user=None, session=None, **filters):
    """List machines or hosts if possible."""
    machines = utils.list_db_objects(
        session, models.Machine, **filters
    )
    machines_or_hosts = []
    for machine in machines:
        host = machine.host
        if host:
            machines_or_hosts.append(host)
        else:
            machines_or_hosts.append(machine)
    return machines_or_hosts


def _get_host(host_id, session=None, **kwargs):
    """Get host by id."""
    if isinstance(host_id, (int, long)):
        return utils.get_db_object(
            session, models.Host,
            id=host_id, **kwargs
        )
    else:
        raise exception.InvalidParameter(
            'host id %s type is not int compatible' % host_id
        )


def get_host_internal(host_id, session=None, **kwargs):
    """Helper function to get host.

    Used by other files under db/api.
    """
    return _get_host(host_id, session=session, **kwargs)


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_HOSTS
)
@utils.wrap_to_dict(RESP_FIELDS)
def get_host(
    host_id, exception_when_missing=True,
    user=None, session=None, **kwargs
):
    """get host info."""
    return _get_host(
        host_id,
        exception_when_missing=exception_when_missing,
        session=session
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_HOSTS
)
@utils.wrap_to_dict(RESP_FIELDS)
def get_machine_or_host(
    host_id, exception_when_missing=True,
    user=None, session=None, **kwargs
):
    """get machine or host if possible."""
    from compass.db.api import machine as machine_api
    machine = machine_api.get_machine_internal(
        host_id,
        exception_when_missing=exception_when_missing,
        session=session
    )
    if machine.host:
        return machine.host
    else:
        return machine


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_HOST_CLUSTERS
)
@utils.wrap_to_dict(RESP_CLUSTER_FIELDS)
def get_host_clusters(host_id, user=None, session=None, **kwargs):
    """get host clusters."""
    host = _get_host(host_id, session=session)
    return [clusterhost.cluster for clusterhost in host.clusterhosts]


def check_host_validated(host):
    """Check host is validated."""
    if not host.config_validated:
        raise exception.Forbidden(
            'host %s is not validated' % host.name
        )


def check_host_editable(
    host, user=None,
    check_in_installing=False
):
    """Check host is editable.

    If we try to set reinstall_os or check the host is not in installing
    state, we should set check_in_installing to True.
    Otherwise we will check the host is not in installing or installed.
    We also make sure the user is admin or the owner of the host to avoid
    unauthorized user to update host attributes.
    """
    if check_in_installing:
        if host.state.state == 'INSTALLING':
            raise exception.Forbidden(
                'host %s is not editable '
                'when state is in installing' % host.name
            )
    elif not host.reinstall_os:
        raise exception.Forbidden(
            'host %s is not editable '
            'when not to be reinstalled' % host.name
        )
    if user and not user.is_admin and host.creator_id != user.id:
        raise exception.Forbidden(
            'host %s is not editable '
            'when user is not admin or the owner of the host' % host.name
        )


def is_host_editable(
    host, user=None,
    check_in_installing=False
):
    """Get if host is editable."""
    try:
        check_host_editable(
            host, user=user,
            check_in_installing=check_in_installing
        )
        return True
    except exception.Forbidden:
        return False


def validate_host(host):
    """Validate host.

    Makesure hostname is not empty, there is only one mgmt network,
    The mgmt network is not in promiscuous mode.
    """
    if not host.hostname:
        raise exception.Invalidparameter(
            'host %s does not set hostname' % host.name
        )
    if not host.host_networks:
        raise exception.InvalidParameter(
            'host %s does not have any network' % host.name
        )
    mgmt_interface_set = False
    for host_network in host.host_networks:
        if host_network.is_mgmt:
            if mgmt_interface_set:
                raise exception.InvalidParameter(
                    'host %s multi interfaces set mgmt ' % host.name
                )
            if host_network.is_promiscuous:
                raise exception.InvalidParameter(
                    'host %s interface %s is mgmt but promiscuous' % (
                        host.name, host_network.interface
                    )
                )
            mgmt_interface_set = True
    if not mgmt_interface_set:
        raise exception.InvalidParameter(
            'host %s has no mgmt interface' % host.name
        )


@utils.supported_filters(
    optional_support_keys=UPDATED_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(name=utils.check_name)
@utils.wrap_to_dict(RESP_FIELDS)
def _update_host(host_id, session=None, user=None, **kwargs):
    """Update a host internal."""
    host = _get_host(host_id, session=session)
    if host.state.state == "SUCCESSFUL" and not host.reinstall_os:
        logging.info("ignoring successful host: %s", host_id)
        return {}
    check_host_editable(
        host, user=user,
        check_in_installing=kwargs.get('reinstall_os', False)
    )
    return utils.update_db_object(session, host, **kwargs)


@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_UPDATE_HOST
)
def update_host(host_id, user=None, session=None, **kwargs):
    """Update a host."""
    return _update_host(host_id, session=session, user=user, **kwargs)


@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_UPDATE_HOST
)
def update_hosts(data=[], user=None, session=None):
    """Update hosts."""
    # TODO(xicheng): this batch function is not similar as others.
    # try to make it similar output as others and batch update should
    # tolerate partial failure.
    hosts = []
    for host_data in data:
        hosts.append(_update_host(session=session, user=user, **host_data))
    return hosts


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_DEL_HOST
)
@utils.wrap_to_dict(
    RESP_FIELDS + ['status', 'host'],
    host=RESP_FIELDS
)
def del_host(
    host_id, force=False, from_database_only=False,
    user=None, session=None, **kwargs
):
    """Delete a host.

    If force, we delete the host anyway.
    If from_database_only, we only delete the host record in databaes.
    Otherwise we send to del host task to celery to delete the host
    record in os installer and package installer, clean installation logs
    and at last clean database record.
    The backend will call this function again after it deletes the record
    in os installer and package installer with from_database_only set.
    """
    from compass.db.api import cluster as cluster_api
    host = _get_host(host_id, session=session)
    # force set host state to ERROR when we want to delete the
    # host anyway even the host is in installing or already
    # installed. It let the api know the deleting is in doing when backend
    # is doing the real deleting. In future we may import a new state like
    # INDELETE to indicate the deleting is processing.
    # We need discuss about if we can delete a host when it is already
    # installed by api.
    if host.state.state != 'UNINITIALIZED' and force:
        host.state.state = 'ERROR'
    check_host_editable(
        host, user=user,
        check_in_installing=True
    )
    cluster_ids = []
    for clusterhost in host.clusterhosts:
        if clusterhost.state.state != 'UNINITIALIZED' and force:
            clusterhost.state.state = 'ERROR'
        # TODO(grace): here we check all clusters which use this host editable.
        # Because in backend we do not have functions to delete host without
        # reference its cluster. After deleting pure host supported in backend,
        # we should change code here to is_cluster_editable.
        # Here delete a host may fail even we set force flag.
        cluster_api.check_cluster_editable(
            clusterhost.cluster, user=user,
            check_in_installing=True
        )
        cluster_ids.append(clusterhost.cluster_id)

    # Delete host record directly if there is no need to delete it
    # in backend or from_database_only is set.
    if host.state.state == 'UNINITIALIZED' or from_database_only:
        return utils.del_db_object(session, host)
    else:
        logging.info(
            'send del host %s task to celery', host_id
        )
        if not user:
            user_id = host.creator_id
            user_dict = user_api.get_user(user_id, session=session)
            user_email = user_dict['email']
        else:
            user_email = user.email
        from compass.tasks import client as celery_client
        celery_client.celery.send_task(
            'compass.tasks.delete_host',
            (
                user.email, host.id, cluster_ids
            ),
            queue=user_email,
            exchange=user_email,
            routing_key=user_email
        )
        return {
            'status': 'delete action sent',
            'host': host,
        }


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_HOST_CONFIG
)
@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
def get_host_config(host_id, user=None, session=None, **kwargs):
    """Get host config."""
    return _get_host(host_id, session=session)


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_HOST_CONFIG
)
@utils.wrap_to_dict(RESP_DEPLOYED_CONFIG_FIELDS)
def get_host_deployed_config(host_id, user=None, session=None, **kwargs):
    """Get host deployed config."""
    return _get_host(host_id, session=session)


# replace os_config to deployed_os_config in kwargs.
@utils.replace_filters(
    os_config='deployed_os_config'
)
@utils.supported_filters(
    UPDATED_DEPLOYED_CONFIG_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_HOST_CONFIG
)
@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
def update_host_deployed_config(host_id, user=None, session=None, **kwargs):
    """Update host deployed config."""
    host = _get_host(host_id, session=session)
    check_host_editable(host, user=user)
    check_host_validated(host)
    return utils.update_db_object(session, host, **kwargs)


def _host_os_config_validates(
    config, host, session=None, user=None, **kwargs
):
    """Check host os config's validation."""
    metadata_api.validate_os_config(
        config, host.os_id
    )


@utils.input_validates_with_args(
    put_os_config=_host_os_config_validates
)
@utils.output_validates_with_args(
    os_config=_host_os_config_validates
)
@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
def _update_host_config(host, session=None, user=None, **kwargs):
    """Update host config."""
    check_host_editable(host, user=user)
    return utils.update_db_object(session, host, **kwargs)


# replace os_config to put_os_config in kwargs.
# It tells db the os_config will be updated not patched.
@utils.replace_filters(
    os_config='put_os_config'
)
@utils.supported_filters(
    UPDATED_CONFIG_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_HOST_CONFIG
)
def update_host_config(host_id, user=None, session=None, **kwargs):
    """Update host config."""
    host = _get_host(host_id, session=session)
    return _update_host_config(
        host, session=session, user=user, **kwargs
    )


# replace os_config to patched_os_config in kwargs.
# It tells db os_config will be patched not be updated.
@utils.replace_filters(
    os_config='patched_os_config'
)
@utils.supported_filters(
    PATCHED_CONFIG_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_HOST_CONFIG
)
def patch_host_config(host_id, user=None, session=None, **kwargs):
    """Patch host config."""
    host = _get_host(host_id, session=session)
    return _update_host_config(
        host, session=session, user=user, **kwargs
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_DEL_HOST_CONFIG
)
@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
def del_host_config(host_id, user=None, session=None):
    """delete a host config."""
    host = _get_host(host_id, session=session)
    check_host_editable(host, user=user)
    return utils.update_db_object(
        session, host, os_config={}, config_validated=False
    )


@utils.supported_filters(
    optional_support_keys=SUPPORTED_NETOWORK_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_HOST_NETWORKS
)
@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
def list_host_networks(host_id, user=None, session=None, **filters):
    """Get host networks for a host."""
    host = _get_host(host_id, session=session)
    return utils.list_db_objects(
        session, models.HostNetwork,
        host_id=host.id, **filters
    )


@utils.supported_filters(
    optional_support_keys=SUPPORTED_NETOWORK_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_HOST_NETWORKS
)
@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
def list_hostnetworks(user=None, session=None, **filters):
    """Get host networks."""
    return utils.list_db_objects(
        session, models.HostNetwork, **filters
    )


def _get_hostnetwork(host_network_id, session=None, **kwargs):
    """Get hostnetwork by hostnetwork id."""
    if isinstance(host_network_id, (int, long)):
        return utils.get_db_object(
            session, models.HostNetwork,
            id=host_network_id, **kwargs
        )
    raise exception.InvalidParameter(
        'host network id %s type is not int compatible' % host_network_id
    )


def _get_host_network(host_id, host_network_id, session=None, **kwargs):
    """Get hostnetwork by host id and hostnetwork id."""
    host = _get_host(host_id, session=session)
    host_network = _get_hostnetwork(host_network_id, session=session, **kwargs)
    if host_network.host_id != host.id:
        raise exception.RecordNotExists(
            'host %s does not own host network %s' % (
                host.id, host_network.id
            )
        )
    return host_network


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_HOST_NETWORKS
)
@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
def get_host_network(
    host_id, host_network_id,
    user=None, session=None, **kwargs
):
    """Get host network."""
    return _get_host_network(
        host_id, host_network_id, session=session
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_HOST_NETWORKS
)
@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
def get_hostnetwork(host_network_id, user=None, session=None, **kwargs):
    """Get host network."""
    return _get_hostnetwork(host_network_id, session=session)


@utils.supported_filters(
    ADDED_NETWORK_FIELDS,
    optional_support_keys=OPTIONAL_ADDED_NETWORK_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(
    ip=utils.check_ip
)
@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
def _add_host_network(
    host_id, exception_when_existing=True,
    session=None, user=None, interface=None, ip=None, **kwargs
):
    """Add hostnetwork to a host."""
    host = _get_host(host_id, session=session)
    check_host_editable(host, user=user)
    user_id = user.id
    return utils.add_db_object(
        session, models.HostNetwork,
        exception_when_existing,
        host.id, interface, user_id, ip=ip, **kwargs
    )


@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_HOST_NETWORK
)
def add_host_network(
    host_id, exception_when_existing=True,
    interface=None, user=None, session=None, **kwargs
):
    """Create a hostnetwork to a host."""
    return _add_host_network(
        host_id,
        exception_when_existing,
        interface=interface, session=session, user=user, **kwargs
    )


def _get_hostnetwork_by_ip(
    ip, session=None, **kwargs
):
    ip_int = long(netaddr.IPAddress(ip))
    return utils.get_db_object(
        session, models.HostNetwork,
        ip_int=ip_int, **kwargs
    )


@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_HOST_NETWORK
)
def add_host_networks(
    exception_when_existing=False,
    data=[], user=None, session=None
):
    """Create host networks."""
    hosts = []
    failed_hosts = []
    for host_data in data:
        host_id = host_data['host_id']
        host = _get_host(host_id, session=session)
        networks = host_data['networks']
        host_networks = []
        failed_host_networks = []
        for network in networks:
            host_network = _get_hostnetwork_by_ip(
                network['ip'], session=session,
                exception_when_missing=False
            )
            if (
                host_network and not (
                    host_network.host_id == host.id and
                    host_network.interface == network['interface']
                )
            ):
                logging.error('ip %s exists in host network %s' % (
                    network['ip'], host_network.id
                ))
                failed_host_networks.append(network)
            else:
                host_networks.append(_add_host_network(
                    host.id, exception_when_existing,
                    session=session, user=user, **network
                ))
        if host_networks:
            hosts.append({'host_id': host.id, 'networks': host_networks})
        if failed_host_networks:
            failed_hosts.append({
                'host_id': host.id, 'networks': failed_host_networks
            })
    return {
        'hosts': hosts,
        'failed_hosts': failed_hosts
    }


@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
def _update_host_network(
    host_network, session=None, user=None, **kwargs
):
    """Update host network."""
    check_host_editable(host_network.host, user=user)
    return utils.update_db_object(session, host_network, **kwargs)


@utils.supported_filters(
    optional_support_keys=UPDATED_NETWORK_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(
    ip=utils.check_ip
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_HOST_NETWORK
)
def update_host_network(
    host_id, host_network_id, user=None, session=None, **kwargs
):
    """Update a host network by host id and host network id."""
    host = _get_host(
        host_id, session=session
    )
    if host.state.state == "SUCCESSFUL" and not host.reinstall_os:
        logging.info("ignoring updating request for successful hosts")
        return {}

    host_network = _get_host_network(
        host_id, host_network_id, session=session
    )
    return _update_host_network(
        host_network, session=session, user=user, **kwargs
    )


@utils.supported_filters(
    optional_support_keys=UPDATED_NETWORK_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(
    ip=utils.check_ip
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_HOST_NETWORK
)
def update_hostnetwork(host_network_id, user=None, session=None, **kwargs):
    """Update a host network by host network id."""
    host_network = _get_hostnetwork(
        host_network_id, session=session
    )
    return _update_host_network(
        host_network, session=session, user=user, **kwargs
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_DEL_HOST_NETWORK
)
@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
def del_host_network(
    host_id, host_network_id, user=None,
    session=None, **kwargs
):
    """Delete a host network by host id and host network id."""
    host_network = _get_host_network(
        host_id, host_network_id, session=session
    )
    check_host_editable(host_network.host, user=user)
    return utils.del_db_object(session, host_network)


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_DEL_HOST_NETWORK
)
@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
def del_hostnetwork(host_network_id, user=None, session=None, **kwargs):
    """Delete a host network by host network id."""
    host_network = _get_hostnetwork(
        host_network_id, session=session
    )
    check_host_editable(host_network.host, user=user)
    return utils.del_db_object(session, host_network)


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_GET_HOST_STATE
)
@utils.wrap_to_dict(RESP_STATE_FIELDS)
def get_host_state(host_id, user=None, session=None, **kwargs):
    """Get host state info."""
    return _get_host(host_id, session=session).state


@utils.supported_filters(
    optional_support_keys=UPDATED_STATE_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_UPDATE_HOST_STATE
)
@utils.wrap_to_dict(RESP_STATE_FIELDS)
def update_host_state(host_id, user=None, session=None, **kwargs):
    """Update a host state."""
    host = _get_host(host_id, session=session)
    utils.update_db_object(session, host.state, **kwargs)
    return host.state


@util.deprecated
@utils.supported_filters(
    optional_support_keys=UPDATED_STATE_INTERNAL_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_UPDATE_HOST_STATE
)
@utils.wrap_to_dict(['status', 'host'])
def update_host_state_internal(
    host_id, from_database_only=False,
    user=None, session=None, **kwargs
):
    """Update a host state.

    This function is called when host os is installed.
    If from_database_only, the state is updated in database.
    Otherwise a celery task sent to os installer and package installer
    to do some future actions.
    """
    # TODO(xicheng): should be merged into update_host_state
    host = _get_host(host_id, session=session)
    logging.info("======host state: %s", host.state)
    if 'ready' in kwargs and kwargs['ready'] and not host.state.ready:
        ready_triggered = True
    else:
        ready_triggered = False
    clusterhosts_ready = {}
    clusters_os_ready = {}
    if ready_triggered:
        for clusterhost in host.clusterhosts:
            cluster = clusterhost.cluster
            if cluster.flavor_name:
                clusterhosts_ready[cluster.id] = False
            else:
                clusterhosts_ready[cluster.id] = True
            all_os_ready = True
            for clusterhost_in_cluster in cluster.clusterhosts:
                host_in_cluster = clusterhost_in_cluster.host
                if host_in_cluster.id == host.id:
                    continue
                if not host_in_cluster.state.ready:
                    all_os_ready = False
            clusters_os_ready[cluster.id] = all_os_ready
    logging.debug('host %s ready: %s', host_id, ready_triggered)
    logging.debug("clusterhosts_ready is: %s", clusterhosts_ready)
    logging.debug("clusters_os_ready is %s", clusters_os_ready)

    if not ready_triggered or from_database_only:
        logging.debug('%s state is set to %s', host.name, kwargs)
        utils.update_db_object(session, host.state, **kwargs)
        if not host.state.ready:
            for clusterhost in host.clusterhosts:
                utils.update_db_object(
                    session, clusterhost.state, ready=False
                )
                utils.update_db_object(
                    session, clusterhost.cluster.state, ready=False
                )
        status = '%s state is updated' % host.name
    else:
        if not user:
            user_id = host.creator_id
            user_dict = user_api.get_user(user_id, session=session)
            user_email = user_dict['email']
        else:
            user_email = user.email
        from compass.tasks import client as celery_client
        celery_client.celery.send_task(
            'compass.tasks.os_installed',
            (
                host.id, clusterhosts_ready,
                clusters_os_ready
            ),
            queue=user_email,
            exchange=user_email,
            routing_key=user_email
        )
        status = '%s: clusterhosts ready %s clusters os ready %s' % (
            host.name, clusterhosts_ready, clusters_os_ready
        )
        logging.info('action status: %s', status)
    return {
        'status': status,
        'host': host.state
    }


@utils.supported_filters([])
@database.run_in_session()
@utils.wrap_to_dict(RESP_LOG_FIELDS)
def get_host_log_histories(host_id, user=None, session=None, **kwargs):
    """Get host log history."""
    host = _get_host(host_id, session=session)
    return utils.list_db_objects(
        session, models.HostLogHistory, id=host.id, **kwargs
    )


def _get_host_log_history(host_id, filename, session=None, **kwargs):
    host = _get_host(host_id, session=session)
    return utils.get_db_object(
        session, models.HostLogHistory, id=host.id,
        filename=filename, **kwargs
    )


@utils.supported_filters([])
@database.run_in_session()
@utils.wrap_to_dict(RESP_LOG_FIELDS)
def get_host_log_history(host_id, filename, user=None, session=None, **kwargs):
    """Get host log history."""
    return _get_host_log_history(
        host_id, filename, session=session
    )


@utils.supported_filters(
    optional_support_keys=UPDATED_LOG_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@utils.wrap_to_dict(RESP_LOG_FIELDS)
def update_host_log_history(
    host_id, filename, user=None,
    session=None, **kwargs
):
    """Update a host log history."""
    host_log_history = _get_host_log_history(
        host_id, filename, session=session
    )
    return utils.update_db_object(session, host_log_history, **kwargs)


@utils.supported_filters(
    ADDED_LOG_FIELDS,
    optional_support_keys=UPDATED_LOG_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@utils.wrap_to_dict(RESP_LOG_FIELDS)
def add_host_log_history(
    host_id, exception_when_existing=False,
    filename=None, user=None, session=None, **kwargs
):
    """add a host log history."""
    host = _get_host(host_id, session=session)
    return utils.add_db_object(
        session, models.HostLogHistory, exception_when_existing,
        host.id, filename, **kwargs
    )


@utils.supported_filters(optional_support_keys=['poweron'])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_DEPLOY_HOST
)
@utils.wrap_to_dict(
    RESP_DEPLOY_FIELDS,
    host=RESP_CONFIG_FIELDS
)
def poweron_host(
    host_id, poweron={}, user=None, session=None, **kwargs
):
    """power on host."""
    from compass.tasks import client as celery_client
    host = _get_host(host_id, session=session)
    check_host_validated(host)
    if not user:
        user_id = host.creator_id
        user_dict = user_api.get_user(user_id, session=session)
        user_email = user_dict['email']
    else:
        user_email = user.email
    celery_client.celery.send_task(
        'compass.tasks.poweron_host',
        (host.id,),
        queue=user_email,
        exchange=user_email,
        routing_key=user_email
    )
    return {
        'status': 'poweron %s action sent' % host.name,
        'host': host
    }


@utils.supported_filters(optional_support_keys=['poweroff'])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_DEPLOY_HOST
)
@utils.wrap_to_dict(
    RESP_DEPLOY_FIELDS,
    host=RESP_CONFIG_FIELDS
)
def poweroff_host(
    host_id, poweroff={}, user=None, session=None, **kwargs
):
    """power off host."""
    from compass.tasks import client as celery_client
    host = _get_host(host_id, session=session)
    check_host_validated(host)
    if not user:
        user_id = host.creator_id
        user_dict = user_api.get_user(user_id, session=session)
        user_email = user_dict['email']
    else:
        user_email = user.email
    celery_client.celery.send_task(
        'compass.tasks.poweroff_host',
        (host.id,),
        queue=user_email,
        exchange=user_email,
        routing_key=user_email
    )
    return {
        'status': 'poweroff %s action sent' % host.name,
        'host': host
    }


@utils.supported_filters(optional_support_keys=['reset'])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_DEPLOY_HOST
)
@utils.wrap_to_dict(
    RESP_DEPLOY_FIELDS,
    host=RESP_CONFIG_FIELDS
)
def reset_host(
    host_id, reset={}, user=None, session=None, **kwargs
):
    """reset host."""
    from compass.tasks import client as celery_client
    host = _get_host(host_id, session=session)
    check_host_validated(host)
    if not user:
        user_id = host.creator_id
        user_dict = user_api.get_user(user_id, session=session)
        user_email = user_dict['email']
    else:
        user_email = user.email
    celery_client.celery.send_task(
        'compass.tasks.reset_host',
        (host.id,),
        queue=user_email,
        exchange=user_email,
        routing_key=user_email
    )
    return {
        'status': 'reset %s action sent' % host.name,
        'host': host
    }
