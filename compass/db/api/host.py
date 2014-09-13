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

from compass.db.api import database
from compass.db.api import metadata_holder as metadata_api
from compass.db.api import permission
from compass.db.api import user as user_api
from compass.db.api import utils
from compass.db import exception
from compass.db import models


SUPPORTED_FIELDS = ['name', 'os_name', 'owner', 'mac']
SUPPORTED_MACHINE_HOST_FIELDS = ['mac', 'tag', 'location', 'os_name', 'os_id']
SUPPORTED_NETOWORK_FIELDS = [
    'interface', 'ip', 'is_mgmt', 'is_promiscuous'
]
RESP_FIELDS = [
    'id', 'name', 'hostname', 'os_name', 'os_id', 'owner', 'mac',
    'switch_ip', 'port', 'switches', 'os_installer',
    'reinstall_os', 'os_installed', 'tag', 'location', 'networks',
    'created_at', 'updated_at'
]
RESP_CLUSTER_FIELDS = [
    'id', 'name', 'os_name', 'reinstall_distributed_system',
    'distributed_system_name', 'owner', 'adapter_id',
    'distributed_system_installed',
    'adapter_id', 'created_at', 'updated_at'
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
UPDATED_FIELDS = ['host_id', 'name', 'reinstall_os']
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
    'id', 'state', 'percentage', 'message', 'severity'
]
UPDATED_STATE_FIELDS = [
    'state', 'percentage', 'message', 'severity'
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
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_HOSTS
)
@utils.wrap_to_dict(RESP_FIELDS)
def list_hosts(session, lister, **filters):
    """List hosts."""
    return utils.list_db_objects(
        session, models.Host, **filters
    )


@utils.supported_filters(
    optional_support_keys=SUPPORTED_MACHINE_HOST_FIELDS)
@database.run_in_session()
@user_api.check_user_permission_in_session(
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
def list_machines_or_hosts(session, lister, **filters):
    """List hosts."""
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


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_HOSTS
)
@utils.wrap_to_dict(RESP_FIELDS)
def get_host(
    session, getter, host_id,
    exception_when_missing=True, **kwargs
):
    """get host info."""
    return utils.get_db_object(
        session, models.Host,
        exception_when_missing, id=host_id
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_HOSTS
)
@utils.wrap_to_dict(RESP_FIELDS)
def get_machine_or_host(
    session, getter, host_id,
    exception_when_missing=True, **kwargs
):
    """get host info."""
    machine = utils.get_db_object(
        session, models.Machine,
        exception_when_missing, id=host_id
    )
    if not machine:
        return None
    host = machine.host
    if host:
        return host
    else:
        return machine


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_HOST_CLUSTERS
)
@utils.wrap_to_dict(RESP_CLUSTER_FIELDS)
def get_host_clusters(session, getter, host_id, **kwargs):
    """get host clusters."""
    host = utils.get_db_object(
        session, models.Host, id=host_id
    )
    return [clusterhost.cluster for clusterhost in host.clusterhosts]


def _conditional_exception(host, exception_when_not_editable):
    if exception_when_not_editable:
        raise exception.Forbidden(
            'host %s is not editable' % host.name
        )
    else:
        return False


def is_host_validated(session, host):
    if not host.config_validated:
        raise exception.Forbidden(
            'host %s is not validated' % host.name
        )


def is_host_editable(
    session, host, user,
    reinstall_os_set=False, exception_when_not_editable=True
):
    if reinstall_os_set:
        if host.state.state == 'DEPLOYING':
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


def validate_host(session, host):
    if not host.host_networks:
        raise exception.InvalidParameter(
            '%s does not have any network' % host.name
        )
    mgmt_interface_set = False
    for host_network in host.host_networks:
        if host_network.is_mgmt:
            if mgmt_interface_set:
                raise exception.InvalidParameter(
                    '%s multi interfaces set mgmt ' % host.name
                )
            if host_network.is_promiscuous:
                raise exception.InvalidParameter(
                    '%s interface %s is mgmt but promiscuous' % (
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
def _update_host(session, updater, host_id, **kwargs):
    """Update a host internal."""
    host = utils.get_db_object(
        session, models.Host, id=host_id
    )
    is_host_editable(
        session, host, updater,
        reinstall_os_set=kwargs.get('reinstall_os', False)
    )
    if 'name' in kwargs:
        hostname = kwargs['name']
        host_by_name = utils.get_db_object(
            session, models.Host, False, name=hostname
        )
        if host_by_name and host_by_name.id != host.id:
            raise exception.InvalidParameter(
                'hostname %s is already exists in host %s' % (
                    hostname, host_by_name.id
                )
            )
    return utils.update_db_object(session, host, **kwargs)


@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_UPDATE_HOST
)
def update_host(session, updater, host_id, **kwargs):
    """Update a host."""
    return _update_host(session, updater, host_id=host_id, **kwargs)


@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_UPDATE_HOST
)
def update_hosts(session, updater, data=[]):
    hosts = []
    for host_data in data:
        hosts.append(_update_host(session, updater, **host_data))
    return hosts


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_DEL_HOST
)
@utils.wrap_to_dict(RESP_FIELDS)
def del_host(session, deleter, host_id, **kwargs):
    """Delete a host."""
    host = utils.get_db_object(
        session, models.Host, id=host_id
    )
    is_host_editable(session, host, deleter)
    return utils.del_db_object(session, host)


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_HOST_CONFIG
)
@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
def get_host_config(session, getter, host_id, **kwargs):
    """Get host config."""
    return utils.get_db_object(
        session, models.Host, id=host_id
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_HOST_CONFIG
)
@utils.wrap_to_dict(RESP_DEPLOYED_CONFIG_FIELDS)
def get_host_deployed_config(session, getter, host_id, **kwargs):
    """Get host deployed config."""
    return utils.get_db_object(
        session, models.Host, id=host_id
    )


@utils.replace_filters(
    os_config='deployed_os_config'
)
@utils.supported_filters(
    UPDATED_DEPLOYED_CONFIG_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_HOST_CONFIG
)
@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
def update_host_deployed_config(session, updater, host_id, **kwargs):
    """Update host deployed config."""
    host = utils.get_db_object(
        session, models.Host, id=host_id
    )
    is_host_editable(session, host, updater)
    is_host_validated(session, host)
    return utils.update_db_object(session, host, **kwargs)


@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_HOST_CONFIG
)
@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
def _update_host_config(session, updater, host, **kwargs):
    """Update host config."""
    is_host_editable(session, host, updater)
    return utils.update_db_object(session, host, **kwargs)


@utils.replace_filters(
    os_config='put_os_config'
)
@utils.supported_filters(
    UPDATED_CONFIG_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
def update_host_config(session, updater, host_id, **kwargs):
    host = utils.get_db_object(
        session, models.Host, id=host_id
    )

    os_config_validates = functools.partial(
        metadata_api.validate_os_config, os_id=host.os_id)

    @utils.input_validates(
        put_os_config=os_config_validates,
    )
    def update_config_internal(host, **in_kwargs):
        return _update_host_config(
            session, updater, host, **kwargs
        )

    return update_config_internal(
        host, **kwargs
    )


@utils.replace_filters(
    os_config='patched_os_config'
)
@utils.supported_filters(
    PATCHED_CONFIG_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
def patch_host_config(session, updater, host_id, **kwargs):
    host = utils.get_db_object(
        session, models.Host, id=host_id
    )

    os_config_validates = functools.partial(
        metadata_api.validate_os_config, os_id=host.os_id)

    @utils.output_validates(
        os_config=os_config_validates,
    )
    def patch_config_internal(host, **in_kwargs):
        return _update_host_config(
            session, updater, host, **in_kwargs
        )

    return patch_config_internal(
        session, updater, host, **kwargs
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_DEL_HOST_CONFIG
)
@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
def del_host_config(session, deleter, host_id):
    """delete a host config."""
    host = utils.get_db_object(
        session, models.Host, id=host_id
    )
    is_host_editable(session, host, deleter)
    return utils.update_db_object(
        session, host, os_config={}, config_validated=False
    )


@utils.supported_filters(
    optional_support_keys=SUPPORTED_NETOWORK_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_HOST_NETWORKS
)
@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
def list_host_networks(session, lister, host_id, **filters):
    """Get host networks."""
    return utils.list_db_objects(
        session, models.HostNetwork,
        host_id=host_id, **filters
    )


@utils.supported_filters(
    optional_support_keys=SUPPORTED_NETOWORK_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_HOST_NETWORKS
)
@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
def list_hostnetworks(session, lister, **filters):
    """Get host networks."""
    return utils.list_db_objects(
        session, models.HostNetwork, **filters
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_HOST_NETWORKS
)
@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
def get_host_network(
    session, getter, host_id,
    host_network_id, **kwargs
):
    """Get host network."""
    host_network = utils.get_db_object(
        session, models.HostNetwork,
        id=host_network_id
    )
    if host_network.host_id != host_id:
        raise exception.RecordNotExists(
            'host %s does not own host network %s' % (
                host_id, host_network_id
            )
        )
    return host_network


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_HOST_NETWORKS
)
@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
def get_hostnetwork(session, getter, host_network_id, **kwargs):
    """Get host network."""
    return utils.get_db_object(
        session, models.HostNetwork,
        id=host_network_id
    )


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
    session, creator, host_id, exception_when_existing=True,
    interface=None, ip=None, **kwargs
):
    host = utils.get_db_object(
        session, models.Host, id=host_id
    )
    host_network = utils.get_db_object(
        session, models.HostNetwork, False,
        host_id=host_id, interface=interface
    )
    if (
        host_network and not (
            host_network.host_id == host_id and
            host_network.interface == interface
        )
    ):
        raise exception.InvalidParameter(
            'interface %s exists in host network %s' % (
                interface, host_network.id
            )
        )
    ip_int = long(netaddr.IPAddress(ip))
    host_network = utils.get_db_object(
        session, models.HostNetwork, False,
        ip_int=ip_int
    )
    if (
        host_network and not (
            host_network.host_id == host_id and
            host_network.interface == interface
        )
    ):
        raise exception.InvalidParameter(
            'ip %s exists in host network %s' % (
                ip, host_network.id
            )
        )
    is_host_editable(session, host, creator)
    return utils.add_db_object(
        session, models.HostNetwork,
        exception_when_existing,
        host_id, interface, ip=ip, **kwargs
    )


@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_HOST_NETWORK
)
def add_host_network(
    session, creator, host_id,
    exception_when_existing=True,
    interface=None, **kwargs
):
    """Create a host network."""
    return _add_host_network(
        session, creator, host_id, exception_when_existing,
        interface=interface, **kwargs
    )


@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_HOST_NETWORK
)
def add_host_networks(
    session, creator,
    exception_when_existing=False,
    data=[]
):
    """Create host networks."""
    hosts = []
    failed_hosts = []
    for host_data in data:
        host_id = host_data['host_id']
        networks = host_data['networks']
        host_networks = []
        failed_host_networks = []
        for network in networks:
            try:
                host_networks.append(_add_host_network(
                    session, creator, host_id, exception_when_existing,
                    **network
                ))
            except exception.DatabaseException as error:
                logging.exception(error)
                failed_host_networks.append(network)
        if host_networks:
            hosts.append({'host_id': host_id, 'networks': host_networks})
        if failed_host_networks:
            failed_hosts.append({
                'host_id': host_id, 'networks': failed_host_networks
            })
    return {
        'hosts': hosts,
        'failed_hosts': failed_hosts
    }


@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_HOST_NETWORK
)
@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
def _update_host_network(
    session, updater, host_network, **kwargs
):
    if 'interface' in kwargs:
        interface = kwargs['interface']
        host_network_by_interface = utils.get_db_object(
            session, models.HostNetwork, False,
            host_id=host_network.host_id,
            interface=interface
        )
        if (
            host_network_by_interface and
            host_network_by_interface.id != host_network.id
        ):
            raise exception.InvalidParameter(
                'interface %s exists in host network %s' % (
                    interface, host_network_by_interface.id
                )
            )
    if 'ip' in kwargs:
        ip = kwargs['ip']
        ip_int = long(netaddr.IPAddress(ip))
        host_network_by_ip = utils.get_db_object(
            session, models.HostNetwork, False,
            ip_int=ip_int
        )
        if host_network_by_ip and host_network_by_ip.id != host_network.id:
            raise exception.InvalidParameter(
                'ip %s exist in host network %s' % (
                    ip, host_network_by_ip.id
                )
            )
    is_host_editable(session, host_network.host, updater)
    return utils.update_db_object(session, host_network, **kwargs)


@utils.supported_filters(
    optional_support_keys=UPDATED_NETWORK_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(
    ip=utils.check_ip
)
@database.run_in_session()
def update_host_network(
    session, updater, host_id, host_network_id, **kwargs
):
    """Update a host network."""
    host_network = utils.get_db_object(
        session, models.HostNetwork,
        id=host_network_id
    )
    if host_network.host_id != host_id:
        raise exception.RecordNotExists(
            'host %s does not own host network %s' % (
                host_id, host_network_id
            )
        )
    return _update_host_network(
        session, updater, host_network, **kwargs
    )


@utils.supported_filters(
    optional_support_keys=UPDATED_NETWORK_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(
    ip=utils.check_ip
)
@database.run_in_session()
def update_hostnetwork(session, updater, host_network_id, **kwargs):
    """Update a host network."""
    host_network = utils.get_db_object(
        session, models.HostNetwork, id=host_network_id
    )
    return _update_host_network(
        session, updater, host_network, **kwargs
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_DEL_HOST_NETWORK
)
@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
def del_host_network(session, deleter, host_id, host_network_id, **kwargs):
    """Delete a host network."""
    host_network = utils.get_db_object(
        session, models.HostNetwork,
        id=host_network_id
    )
    if host_network.host_id != host_id:
        raise exception.RecordNotExists(
            'host %s does not own host network %s' % (
                host_id, host_network_id
            )
        )
    is_host_editable(session, host_network.host, deleter)
    return utils.del_db_object(session, host_network)


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_DEL_HOST_NETWORK
)
@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
def del_hostnetwork(session, deleter, host_network_id, **kwargs):
    """Delete a host network."""
    host_network = utils.get_db_object(
        session, models.HostNetwork, id=host_network_id
    )
    is_host_editable(session, host_network.host, deleter)
    return utils.del_db_object(session, host_network)


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_GET_HOST_STATE
)
@utils.wrap_to_dict(RESP_STATE_FIELDS)
def get_host_state(session, getter, host_id, **kwargs):
    """Get host state info."""
    return utils.get_db_object(
        session, models.Host, id=host_id
    ).state_dict()


@utils.supported_filters(
    optional_support_keys=UPDATED_STATE_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_UPDATE_HOST_STATE
)
@utils.wrap_to_dict(RESP_STATE_FIELDS)
def update_host_state(session, updater, host_id, **kwargs):
    """Update a host state."""
    host = utils.get_db_object(
        session, models.Host, id=host_id
    )
    utils.update_db_object(session, host.state, **kwargs)
    return host.state_dict()


@utils.supported_filters([])
@database.run_in_session()
@utils.wrap_to_dict(RESP_LOG_FIELDS)
def get_host_log_histories(session, getter, host_id, **kwargs):
    """Get host log history."""
    return utils.list_db_objects(
        session, models.HostLogHistory, id=host_id
    )


@utils.supported_filters([])
@database.run_in_session()
@utils.wrap_to_dict(RESP_LOG_FIELDS)
def get_host_log_history(session, getter, host_id, filename, **kwargs):
    """Get host log history."""
    return utils.get_db_object(
        session, models.HostLogHistory, id=host_id, filename=filename
    )


@utils.supported_filters(
    optional_support_keys=UPDATED_LOG_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@database.run_in_session()
@utils.wrap_to_dict(RESP_LOG_FIELDS)
def update_host_log_history(session, updater, host_id, filename, **kwargs):
    """Update a host log history."""
    host_log_history = utils.get_db_object(
        session, models.HostLogHistory, id=host_id, filename=filename
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
    session, creator, host_id, exception_when_existing=False,
    filename=None, **kwargs
):
    """add a host log history."""
    return utils.add_db_object(
        session, models.HostLogHistory, exception_when_existing,
        host_id, filename, **kwargs
    )


@utils.supported_filters(optional_support_keys=['poweron'])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_DEPLOY_HOST
)
@utils.wrap_to_dict(
    RESP_DEPLOY_FIELDS,
    host=RESP_CONFIG_FIELDS
)
def poweron_host(
    session, deployer, host_id, poweron={}, **kwargs
):
    """power on host."""
    from compass.tasks import client as celery_client
    host = utils.get_db_object(
        session, models.host, id=host_id
    )
    is_host_validated(session, host)
    celery_client.celery.send_task(
        'compass.tasks.poweron_host',
        (host_id,)
    )
    return {
        'status': 'poweron %s action sent' % host.name,
        'host': host
    }


@utils.supported_filters(optional_support_keys=['poweroff'])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_DEPLOY_HOST
)
@utils.wrap_to_dict(
    RESP_DEPLOY_FIELDS,
    host=RESP_CONFIG_FIELDS
)
def poweroff_host(
    session, deployer, host_id, poweroff={}, **kwargs
):
    """power off host."""
    from compass.tasks import client as celery_client
    host = utils.get_db_object(
        session, models.host, id=host_id
    )
    is_host_validated(session, host)
    celery_client.celery.send_task(
        'compass.tasks.poweroff_host',
        (host_id,)
    )
    return {
        'status': 'poweroff %s action sent' % host.name,
        'host': host
    }


@utils.supported_filters(optional_support_keys=['reset'])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_DEPLOY_HOST
)
@utils.wrap_to_dict(
    RESP_DEPLOY_FIELDS,
    host=RESP_CONFIG_FIELDS
)
def reset_host(
    session, deployer, host_id, reset={}, **kwargs
):
    """reset host."""
    from compass.tasks import client as celery_client
    host = utils.get_db_object(
        session, models.host, id=host_id
    )
    is_host_validated(session, host)
    celery_client.celery.send_task(
        'compass.tasks.reset_host',
        (host_id,)
    )
    return {
        'status': 'reset %s action sent' % host.name,
        'host': host
    }
