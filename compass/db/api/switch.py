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

"""Switch database operations."""
import logging
import netaddr
import re

from compass.db.api import database
from compass.db.api import permission
from compass.db.api import user as user_api
from compass.db.api import utils
from compass.db import exception
from compass.db import models
from compass.utils import setting_wrapper as setting
from compass.utils import util


SUPPORTED_FIELDS = ['ip_int', 'vendor', 'state']
SUPPORTED_FILTER_FIELDS = ['ip_int', 'vendor', 'state']
SUPPORTED_SWITCH_MACHINES_FIELDS = [
    'switch_ip_int', 'port', 'vlans', 'mac', 'tag', 'location',
    'owner_id'
]
SUPPORTED_MACHINES_FIELDS = [
    'port', 'vlans', 'mac', 'tag', 'location', 'owner_id'
]
SUPPORTED_SWITCH_MACHINES_HOSTS_FIELDS = [
    'switch_ip_int', 'port', 'vlans', 'mac',
    'tag', 'location', 'os_name'
]
SUPPORTED_MACHINES_HOSTS_FIELDS = [
    'port', 'vlans', 'mac', 'tag', 'location',
    'os_name'
]
IGNORE_FIELDS = ['id', 'created_at', 'updated_at']
ADDED_FIELDS = ['ip']
OPTIONAL_ADDED_FIELDS = [
    'credentials', 'vendor', 'state', 'err_msg', 'machine_filters'
]
UPDATED_FIELDS = [
    'ip', 'credentials', 'vendor', 'state',
    'err_msg', 'put_machine_filters'
]
PATCHED_FIELDS = ['patched_credentials', 'patched_machine_filters']
UPDATED_FILTERS_FIELDS = ['put_machine_filters']
PATCHED_FILTERS_FIELDS = ['patched_machine_filters']
ADDED_MACHINES_FIELDS = ['mac']
OPTIONAL_ADDED_MACHINES_FIELDS = [
    'ipmi_credentials', 'tag', 'location', 'owner_id'
]
ADDED_SWITCH_MACHINES_FIELDS = ['port']
OPTIONAL_ADDED_SWITCH_MACHINES_FIELDS = ['vlans']
UPDATED_MACHINES_FIELDS = [
    'ipmi_credentials',
    'tag', 'location'
]
UPDATED_SWITCH_MACHINES_FIELDS = ['port', 'vlans', 'owner_id']
PATCHED_MACHINES_FIELDS = [
    'patched_ipmi_credentials',
    'patched_tag', 'patched_location'
]
PATCHED_SWITCH_MACHINES_FIELDS = ['patched_vlans']
RESP_FIELDS = [
    'id', 'ip', 'credentials', 'vendor', 'state', 'err_msg',
    'filters', 'created_at', 'updated_at'
]
RESP_FILTERS_FIELDS = [
    'id', 'ip', 'filters', 'created_at', 'updated_at'
]
RESP_ACTION_FIELDS = [
    'status', 'details'
]
RESP_MACHINES_FIELDS = [
    'id', 'switch_id', 'switch_ip', 'machine_id', 'switch_machine_id',
    'port', 'vlans', 'mac', 'owner_id',
    'ipmi_credentials', 'tag', 'location',
    'created_at', 'updated_at'
]
RESP_MACHINES_HOSTS_FIELDS = [
    'id', 'switch_id', 'switch_ip', 'machine_id', 'switch_machine_id',
    'port', 'vlans', 'mac',
    'ipmi_credentials', 'tag', 'location', 'ip',
    'name', 'hostname', 'os_name', 'owner',
    'os_installer', 'reinstall_os', 'os_installed',
    'clusters', 'created_at', 'updated_at'
]
RESP_CLUSTER_FIELDS = [
    'name', 'id'
]


def _check_machine_filters(machine_filters):
    """Check if machine filters format is acceptable."""
    logging.debug('check machine filters: %s', machine_filters)
    models.Switch.parse_filters(machine_filters)


def _check_vlans(vlans):
    """Check vlans format is acceptable."""
    for vlan in vlans:
        if not isinstance(vlan, int):
            raise exception.InvalidParameter(
                'vlan %s is not int' % vlan
            )


@utils.supported_filters(
    ADDED_FIELDS,
    optional_support_keys=OPTIONAL_ADDED_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(
    ip=utils.check_ip,
    credentials=utils.check_switch_credentials,
    machine_filters=_check_machine_filters
)
@utils.wrap_to_dict(RESP_FIELDS)
def _add_switch(
    ip, exception_when_existing=True,
    machine_filters=setting.SWITCHES_DEFAULT_FILTERS,
    session=None, **kwargs
):
    """Add switch by switch ip."""
    ip_int = long(netaddr.IPAddress(ip))
    return utils.add_db_object(
        session, models.Switch, exception_when_existing, ip_int,
        machine_filters=machine_filters, **kwargs
    )


def get_switch_internal(
    switch_id, session=None, **kwargs
):
    """Get switch by switch id.

    Should only be used by other files under db/api
    """
    return _get_switch(switch_id, session=session, **kwargs)


def _get_switch(switch_id, session=None, **kwargs):
    """Get Switch object switch id."""
    if isinstance(switch_id, (int, long)):
        return utils.get_db_object(
            session, models.Switch,
            id=switch_id, **kwargs
        )
    raise exception.InvalidParameter(
        'switch id %s type is not int compatible' % switch_id)


def _get_switch_by_ip(switch_ip, session=None, **kwargs):
    """Get switch by switch ip."""
    switch_ip_int = long(netaddr.IPAddress(switch_ip))
    return utils.get_db_object(
        session, models.Switch,
        ip_int=switch_ip_int, **kwargs
    )


def _get_switch_machine(switch_id, machine_id, session=None, **kwargs):
    """Get switch machine by switch id and machine id."""
    switch = _get_switch(switch_id, session=session)
    from compass.db.api import machine as machine_api
    machine = machine_api.get_machine_internal(machine_id, session=session)
    return utils.get_db_object(
        session, models.SwitchMachine,
        switch_id=switch.id, machine_id=machine.id, **kwargs
    )


def _get_switchmachine(switch_machine_id, session=None, **kwargs):
    """Get switch machine by switch_machine_id."""
    if not isinstance(switch_machine_id, (int, long)):
        raise exception.InvalidParameter(
            'switch machine id %s type is not int compatible' % (
                switch_machine_id
            )
        )
    return utils.get_db_object(
        session, models.SwitchMachine,
        switch_machine_id=switch_machine_id, **kwargs
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_SWITCHES
)
@utils.wrap_to_dict(RESP_FIELDS)
def get_switch(
    switch_id, exception_when_missing=True,
    user=None, session=None, **kwargs
):
    """get a switch by switch id."""
    return _get_switch(
        switch_id, session=session,
        exception_when_missing=exception_when_missing
    )


@utils.supported_filters(optional_support_keys=SUPPORTED_FIELDS)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_SWITCHES
)
@utils.wrap_to_dict(RESP_FIELDS)
def list_switches(user=None, session=None, **filters):
    """List switches."""
    # TODO(xicheng): should discuss with weidong.
    # If we can deprecate the use of DEFAULT_SWITCH_IP,
    # The code will be simpler.
    # The UI should use /machines-hosts instead of
    # /switches-machines-hosts and can show multi switch ip/port
    # under one row of machine info.
    switches = utils.list_db_objects(
        session, models.Switch, **filters
    )
    if 'ip_int' in filters:
        return switches
    else:
        return [
            switch for switch in switches
            if switch.ip != setting.DEFAULT_SWITCH_IP
        ]


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_DEL_SWITCH
)
@utils.wrap_to_dict(RESP_FIELDS)
def del_switch(switch_id, user=None, session=None, **kwargs):
    """Delete a switch.

    If switch is not the default switch, and the machine under this switch
    is only connected to this switch, the machine will be moved to connect
    to default switch. Otherwise we can only simply delete the switch
    machine. The purpose here to make sure there is no machine not
    connecting to any switch.
    """
    # TODO(xicheng): Simplify the logic if the default switch feature
    # can be deprecated.
    switch = _get_switch(switch_id, session=session)
    default_switch = _get_switch_by_ip(
        setting.DEFAULT_SWITCH_IP, session=session
    )
    if switch.id != default_switch.id:
        for switch_machine in switch.switch_machines:
            machine = switch_machine.machine
            if len(machine.switch_machines) <= 1:
                utils.add_db_object(
                    session, models.SwitchMachine,
                    False,
                    default_switch.id, machine.id,
                    port=switch_machine.port
                )
    return utils.del_db_object(session, switch)


@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_SWITCH
)
def add_switch(
    exception_when_existing=True, ip=None,
    user=None, session=None, **kwargs
):
    """Create a switch."""
    return _add_switch(
        ip,
        exception_when_existing=exception_when_existing,
        session=session, **kwargs
    )


@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_SWITCH
)
def add_switches(
    exception_when_existing=False,
    data=[], user=None, session=None
):
    """Create switches."""
    # TODO(xicheng): simplify the batch api.
    switches = []
    fail_switches = []
    for switch_data in data:
        switch_object = _get_switch_by_ip(
            switch_data['ip'], session=session,
            exception_when_missing=False
        )
        if switch_object:
            logging.error('ip %s exists in switch %s' % (
                switch_data['ip'], switch_object.id
            ))
            fail_switches.append(switch_data)
        else:
            switches.append(
                _add_switch(
                    exception_when_existing=exception_when_existing,
                    session=session,
                    **switch_data
                )
            )
    return {
        'switches': switches,
        'fail_switches': fail_switches
    }


@utils.wrap_to_dict(RESP_FIELDS)
def _update_switch(switch_id, session=None, **kwargs):
    """Update a switch."""
    switch = _get_switch(switch_id, session=session)
    return utils.update_db_object(session, switch, **kwargs)


# replace machine_filters in kwargs to put_machine_filters,
# which is used to tell db this is a put action for the field.
@utils.replace_filters(
    machine_filters='put_machine_filters'
)
@utils.supported_filters(
    optional_support_keys=UPDATED_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(
    credentials=utils.check_switch_credentials,
    put_machine_filters=_check_machine_filters
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_SWITCH
)
def update_switch(switch_id, user=None, session=None, **kwargs):
    """Update fields of a switch."""
    return _update_switch(switch_id, session=session, **kwargs)


# replace credentials to patched_credentials,
# machine_filters to patched_machine_filters in kwargs.
# This is to tell db they are patch action to the above fields.
@utils.replace_filters(
    credentials='patched_credentials',
    machine_filters='patched_machine_filters'
)
@utils.supported_filters(
    optional_support_keys=PATCHED_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(
    patched_machine_filters=_check_machine_filters
)
@database.run_in_session()
@utils.output_validates(
    credentials=utils.check_switch_credentials
)
@user_api.check_user_permission(
    permission.PERMISSION_ADD_SWITCH
)
def patch_switch(switch_id, user=None, session=None, **kwargs):
    """Patch fields of a switch."""
    return _update_switch(switch_id, session=session, **kwargs)


@util.deprecated
@utils.supported_filters(optional_support_keys=SUPPORTED_FILTER_FIELDS)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_SWITCH_FILTERS
)
@utils.wrap_to_dict(RESP_FILTERS_FIELDS)
def list_switch_filters(user=None, session=None, **filters):
    """List all switches' filters."""
    return utils.list_db_objects(
        session, models.Switch, **filters
    )


@util.deprecated
@utils.supported_filters()
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_SWITCH_FILTERS
)
@utils.wrap_to_dict(RESP_FILTERS_FIELDS)
def get_switch_filters(
    switch_id, exception_when_missing=True,
    user=None, session=None, **kwargs
):
    """get filters of a switch."""
    return _get_switch(
        switch_id, session=session,
        exception_when_missing=exception_when_missing
    )


@util.deprecated
@utils.replace_filters(
    machine_filters='put_machine_filters'
)
@utils.supported_filters(
    optional_support_keys=UPDATED_FILTERS_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(put_machine_filters=_check_machine_filters)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_UPDATE_SWITCH_FILTERS
)
@utils.wrap_to_dict(RESP_FILTERS_FIELDS)
def update_switch_filters(switch_id, user=None, session=None, **kwargs):
    """Update filters of a switch."""
    switch = _get_switch(switch_id, session=session)
    return utils.update_db_object(session, switch, **kwargs)


@util.deprecated
@utils.replace_filters(
    machine_filters='patched_machine_filters'
)
@utils.supported_filters(
    optional_support_keys=PATCHED_FILTERS_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(patched_machine_filters=_check_machine_filters)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_UPDATE_SWITCH_FILTERS
)
@utils.wrap_to_dict(RESP_FILTERS_FIELDS)
def patch_switch_filter(switch_id, user=None, session=None, **kwargs):
    """Patch filters to a switch."""
    switch = _get_switch(switch_id, session=session)
    return utils.update_db_object(session, switch, **kwargs)


@util.deprecated
def get_switch_machines_internal(session, **filters):
    return utils.list_db_objects(
        session, models.SwitchMachine, **filters
    )


def _filter_port(port_filter, obj):
    """filter switch machines by port.

    supported port_filter keys: [
        'startswith', 'endswith', 'resp_lt',
        'resp_le', 'resp_gt', 'resp_ge', 'resp_range'
    ]

    port_filter examples:
        {
            'startswitch': 'ae', 'endswith': '',
            'resp_ge': 20, 'resp_le': 30,
        }
    """
    port_prefix = port_filter.get('startswith', '')
    port_suffix = port_filter.get('endswith', '')
    pattern = re.compile(r'%s(\d+)%s' % (port_prefix, port_suffix))
    match = pattern.match(obj)
    if not match:
        return False
    port_number = int(match.group(1))
    if (
        'resp_lt' in port_filter and
        port_number >= port_filter['resp_lt']
    ):
        return False
    if (
        'resp_le' in port_filter and
        port_number > port_filter['resp_le']
    ):
        return False
    if (
        'resp_gt' in port_filter and
        port_number <= port_filter['resp_gt']
    ):
        return False
    if (
        'resp_ge' in port_filter and
        port_number < port_filter['resp_ge']
    ):
        return False
    if 'resp_range' in port_filter:
        resp_range = port_filter['resp_range']
        if not isinstance(resp_range, list):
            resp_range = [resp_range]
        in_range = False
        for port_start, port_end in resp_range:
            if port_start <= port_number <= port_end:
                in_range = True
                break
        if not in_range:
            return False
    return True


def _filter_vlans(vlan_filter, obj):
    """Filter switch machines by vlan.

    supported keys in vlan_filter:
        ['resp_in']
    """
    vlans = set(obj)
    if 'resp_in' in vlan_filter:
        resp_vlans = set(vlan_filter['resp_in'])
        if not (vlans & resp_vlans):
            return False
    return True


@utils.output_filters(
    port=_filter_port, vlans=_filter_vlans,
    tag=utils.general_filter_callback,
    location=utils.general_filter_callback
)
@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
def _filter_switch_machines(switch_machines):
    """Get filtered switch machines.

    The filters are defined in each switch.
    """
    return [
        switch_machine for switch_machine in switch_machines
        if not switch_machine.filtered
    ]


@utils.output_filters(
    missing_ok=True,
    port=_filter_port, vlans=_filter_vlans,
    tag=utils.general_filter_callback,
    location=utils.general_filter_callback,
    os_name=utils.general_filter_callback,
)
@utils.wrap_to_dict(
    RESP_MACHINES_HOSTS_FIELDS,
    clusters=RESP_CLUSTER_FIELDS
)
def _filter_switch_machines_hosts(switch_machines):
    """Similar as _filter_switch_machines, but also return host info."""
    filtered_switch_machines = [
        switch_machine for switch_machine in switch_machines
        if not switch_machine.filtered
    ]
    switch_machines_hosts = []
    for switch_machine in filtered_switch_machines:
        machine = switch_machine.machine
        host = machine.host
        if host:
            switch_machine_host_dict = host.to_dict()
        else:
            switch_machine_host_dict = machine.to_dict()
        switch_machine_host_dict.update(
            switch_machine.to_dict()
        )
        switch_machines_hosts.append(switch_machine_host_dict)
    return switch_machines_hosts


@utils.supported_filters(
    optional_support_keys=SUPPORTED_MACHINES_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_SWITCH_MACHINES
)
def list_switch_machines(
    switch_id, user=None, session=None, **filters
):
    """Get switch machines of a switch."""
    switch = _get_switch(switch_id, session=session)
    switch_machines = utils.list_db_objects(
        session, models.SwitchMachine, switch_id=switch.id, **filters
    )
    if not user.is_admin and len(switch_machines):
        switch_machines = [m for m in switch_machines if m.machine.owner_id == user.id]
    return _filter_switch_machines(switch_machines)


# replace ip_int to switch_ip_int in kwargs
@utils.replace_filters(
    ip_int='switch_ip_int'
)
@utils.supported_filters(
    optional_support_keys=SUPPORTED_SWITCH_MACHINES_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_SWITCH_MACHINES
)
def list_switchmachines(user=None, session=None, **filters):
    """List switch machines."""
    switch_machines = utils.list_db_objects(
        session, models.SwitchMachine, **filters
    )
    return _filter_switch_machines(
        switch_machines
    )


@utils.supported_filters(
    optional_support_keys=SUPPORTED_MACHINES_HOSTS_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_SWITCH_MACHINES
)
def list_switch_machines_hosts(
    switch_id, user=None, session=None, **filters
):
    """Get switch machines and possible hosts of a switch."""
    switch = _get_switch(switch_id, session=session)
    switch_machines = utils.list_db_objects(
        session, models.SwitchMachine, switch_id=switch.id, **filters
    )
    return _filter_switch_machines_hosts(
        switch_machines
    )


# replace ip_int to switch_ip_int in kwargs
@utils.replace_filters(
    ip_int='switch_ip_int'
)
@utils.supported_filters(
    optional_support_keys=SUPPORTED_SWITCH_MACHINES_HOSTS_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_SWITCH_MACHINES
)
def list_switchmachines_hosts(user=None, session=None, **filters):
    """List switch machines hnd possible hosts."""
    switch_machines = utils.list_db_objects(
        session, models.SwitchMachine, **filters
    )
    if not user.is_admin and len(switch_machines):
        switch_machines = [m for m in switch_machines if m.machine.owner_id == user.id]
    return _filter_switch_machines_hosts(
        switch_machines
    )


@utils.supported_filters(
    ADDED_MACHINES_FIELDS,
    optional_support_keys=OPTIONAL_ADDED_MACHINES_FIELDS,
    ignore_support_keys=OPTIONAL_ADDED_SWITCH_MACHINES_FIELDS
)
@utils.input_validates(mac=utils.check_mac)
def _add_machine_if_not_exist(mac=None, session=None, **kwargs):
    """Add machine if the mac does not exist in any machine."""
    return utils.add_db_object(
        session, models.Machine, False,
        mac, **kwargs)


@utils.supported_filters(
    ADDED_SWITCH_MACHINES_FIELDS,
    optional_support_keys=OPTIONAL_ADDED_SWITCH_MACHINES_FIELDS,
    ignore_support_keys=OPTIONAL_ADDED_MACHINES_FIELDS
)
@utils.input_validates(vlans=_check_vlans)
def _add_switch_machine_only(
    switch, machine, exception_when_existing=True,
    session=None, owner_id=None, port=None, **kwargs
):
    """add a switch machine."""
    return utils.add_db_object(
        session, models.SwitchMachine,
        exception_when_existing,
        switch.id, machine.id, port=port,
        owner_id=owner_id,
        **kwargs
    )


@utils.supported_filters(
    ADDED_MACHINES_FIELDS + ADDED_SWITCH_MACHINES_FIELDS,
    optional_support_keys=(
        OPTIONAL_ADDED_MACHINES_FIELDS +
        OPTIONAL_ADDED_SWITCH_MACHINES_FIELDS
    ),
    ignore_support_keys=IGNORE_FIELDS
)
@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
def _add_switch_machine(
    switch_id, exception_when_existing=True,
    mac=None, port=None, session=None, owner_id=None, **kwargs
):
    """Add switch machine.

    If underlying machine does not exist, also create the underlying
    machine.
    """
    switch = _get_switch(switch_id, session=session)
    machine = _add_machine_if_not_exist(
        mac=mac, session=session, owner_id=owner_id, **kwargs
    )
    return _add_switch_machine_only(
        switch, machine,
        exception_when_existing,
        port=port, session=session, **kwargs
    )


@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_SWITCH_MACHINE
)
def add_switch_machine(
    switch_id, exception_when_existing=True,
    mac=None, user=None, session=None,
    owner_id=None, **kwargs
):
    """Add switch machine to a switch."""
    return _add_switch_machine(
        switch_id,
        exception_when_existing=exception_when_existing,
        mac=mac, session=session, owner_id=owner_id, **kwargs
    )


@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_SWITCH_MACHINE
)
@utils.wrap_to_dict(
    [
        'switches_machines',
        'duplicate_switches_machines',
        'fail_switches_machines'
    ],
    switches_machines=RESP_MACHINES_FIELDS,
    duplicate_switches_machines=RESP_MACHINES_FIELDS
)
def add_switch_machines(
    exception_when_existing=False,
    data=[], user=None, session=None, owner_id=None
):
    """Add switch machines."""
    switch_machines = []
    duplicate_switch_machines = []
    failed_switch_machines = []
    switches_mapping = {}
    switch_machines_mapping = {}
    switch_ips = []
    for item_data in data:
        switch_ip = item_data['switch_ip']
        if switch_ip not in switches_mapping:
            switch_object = _get_switch_by_ip(
                switch_ip, session=session,
                exception_when_missing=False
            )
            if switch_object:
                switch_ips.append(switch_ip)
                switches_mapping[switch_ip] = switch_object
            else:
                logging.error(
                    'switch %s does not exist' % switch_ip
                )
                item_data.pop('switch_ip')
                failed_switch_machines.append(item_data)
        else:
            switch_object = switches_mapping[switch_ip]
        if switch_object:
            item_data.pop('switch_ip')
            switch_machines_mapping.setdefault(
                switch_object.id, []
            ).append(item_data)

    for switch_ip in switch_ips:
        switch_object = switches_mapping[switch_ip]
        switch_id = switch_object.id
        machines = switch_machines_mapping[switch_id]
        for machine in machines:
            mac = machine['mac']
            machine_object = _add_machine_if_not_exist(
                mac=mac, session=session
            )
            switch_machine_object = _get_switch_machine(
                switch_id, machine_object.id, session=session,
                exception_when_missing=False
            )
            if switch_machine_object:
                port = machine['port']
                switch_machine_id = switch_machine_object.switch_machine_id
                exist_port = switch_machine_object.port
                if exist_port != port:
                    logging.error(
                        'switch machine %s exist port %s is '
                        'different from added port %s' % (
                            switch_machine_id,
                            exist_port, port
                        )
                    )
                    failed_switch_machines.append(machine)
                else:
                    logging.error(
                        'iswitch machine %s is dulicate, '
                        'will not be override' % switch_machine_id
                    )
                    duplicate_switch_machines.append(machine)
            else:
                del machine['mac']
                switch_machines.append(_add_switch_machine_only(
                    switch_object, machine_object,
                    exception_when_existing,
                    session=session, owner_id=owner_id, **machine
                ))
    return {
        'switches_machines': switch_machines,
        'duplicate_switches_machines': duplicate_switch_machines,
        'fail_switches_machines': failed_switch_machines
    }


@utils.supported_filters(optional_support_keys=['find_machines'])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_UPDATE_SWITCH_MACHINES
)
@utils.wrap_to_dict(RESP_ACTION_FIELDS)
def poll_switch(switch_id, user=None, session=None, **kwargs):
    """poll switch to get machines."""
    from compass.tasks import client as celery_client
    switch = _get_switch(switch_id, session=session)
    celery_client.celery.send_task(
        'compass.tasks.pollswitch',
        (user.email, switch.ip, switch.credentials),
        queue=user.email,
        exchange=user.email,
        routing_key=user.email
    )
    return {
        'status': 'action %s sent' % kwargs,
        'details': {
        }
    }


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_SWITCH_MACHINES
)
@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
def get_switch_machine(
    switch_id, machine_id, exception_when_missing=True,
    user=None, session=None, **kwargs
):
    """get a switch machine by switch id and machine id."""
    return _get_switch_machine(
        switch_id, machine_id, session=session,
        exception_when_missing=exception_when_missing
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_LIST_SWITCH_MACHINES
)
@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
def get_switchmachine(
    switch_machine_id, exception_when_missing=True,
    user=None, session=None, **kwargs
):
    """get a switch machine by switch_machine_id."""
    return _get_switchmachine(
        switch_machine_id, session=session,
        exception_when_missing=exception_when_missing
    )


@utils.supported_filters(
    optional_support_keys=(
        UPDATED_MACHINES_FIELDS + PATCHED_MACHINES_FIELDS
    ),
    ignore_support_keys=(
        UPDATED_SWITCH_MACHINES_FIELDS + PATCHED_SWITCH_MACHINES_FIELDS
    )
)
def _update_machine_if_necessary(
    machine, session=None, **kwargs
):
    """Update machine is there is something to update."""
    utils.update_db_object(
        session, machine, **kwargs
    )


@utils.supported_filters(
    optional_support_keys=(
        UPDATED_SWITCH_MACHINES_FIELDS + PATCHED_SWITCH_MACHINES_FIELDS
    ),
    ignore_support_keys=(
        UPDATED_MACHINES_FIELDS + PATCHED_MACHINES_FIELDS
    )
)
def _update_switch_machine_only(switch_machine, session=None, **kwargs):
    """Update switch machine."""
    return utils.update_db_object(
        session, switch_machine, **kwargs
    )


def _update_switch_machine(
    switch_machine, session=None, **kwargs
):
    """Update switch machine.

    If there are some attributes of underlying machine need to update,
    also update them in underlying machine.
    """
    _update_machine_if_necessary(
        switch_machine.machine, session=session, **kwargs
    )
    return _update_switch_machine_only(
        switch_machine, session=session, **kwargs
    )


@utils.supported_filters(
    optional_support_keys=(
        UPDATED_MACHINES_FIELDS + UPDATED_SWITCH_MACHINES_FIELDS
    ),
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(vlans=_check_vlans)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_SWITCH_MACHINE
)
@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
def update_switch_machine(
    switch_id, machine_id, user=None,
    session=None, **kwargs
):
    """Update switch machine by switch id and machine id."""
    switch_machine = _get_switch_machine(
        switch_id, machine_id, session=session
    )
    return _update_switch_machine(
        switch_machine,
        session=session, **kwargs
    )


@utils.supported_filters(
    optional_support_keys=(
        UPDATED_MACHINES_FIELDS + UPDATED_SWITCH_MACHINES_FIELDS
    ),
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(vlans=_check_vlans)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_SWITCH_MACHINE
)
@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
def update_switchmachine(switch_machine_id, user=None, session=None, **kwargs):
    """Update switch machine by switch_machine_id."""
    switch_machine = _get_switchmachine(
        switch_machine_id, session=session
    )
    return _update_switch_machine(
        switch_machine,
        session=session, **kwargs
    )


# replace [vlans, ipmi_credentials, tag, location] to
# [patched_vlans, patched_ipmi_credentials, patched_tag,
# patched_location] in kwargs. It tells db these fields will
# be patched.
@utils.replace_filters(
    vlans='patched_vlans',
    ipmi_credentials='patched_ipmi_credentials',
    tag='patched_tag',
    location='patched_location'
)
@utils.supported_filters(
    optional_support_keys=(
        PATCHED_MACHINES_FIELDS + PATCHED_SWITCH_MACHINES_FIELDS
    ),
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(patched_vlans=_check_vlans)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_SWITCH_MACHINE
)
@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
def patch_switch_machine(
    switch_id, machine_id, user=None,
    session=None, **kwargs
):
    """Patch switch machine by switch_id and machine_id."""
    switch_machine = _get_switch_machine(
        switch_id, machine_id, session=session
    )
    return _update_switch_machine(
        switch_machine,
        session=session, **kwargs
    )


# replace [vlans, ipmi_credentials, tag, location] to
# [patched_vlans, patched_ipmi_credentials, patched_tag,
# patched_location] in kwargs. It tells db these fields will
# be patched.
@utils.replace_filters(
    vlans='patched_vlans',
    ipmi_credentials='patched_ipmi_credentials',
    tag='patched_tag',
    location='patched_location'
)
@utils.supported_filters(
    optional_support_keys=(
        PATCHED_MACHINES_FIELDS + PATCHED_SWITCH_MACHINES_FIELDS
    ),
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(patched_vlans=_check_vlans)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_ADD_SWITCH_MACHINE
)
@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
def patch_switchmachine(switch_machine_id, user=None, session=None, **kwargs):
    """Patch switch machine by switch_machine_id."""
    switch_machine = _get_switchmachine(
        switch_machine_id, session=session
    )
    return _update_switch_machine(
        switch_machine,
        session=session, **kwargs
    )


def _del_switch_machine(
    switch_machine, session=None
):
    """Delete switch machine.

    If this is the last switch machine associated to underlying machine,
    add a switch machine record to default switch to make the machine
    searchable.
    """
    default_switch = _get_switch_by_ip(
        setting.DEFAULT_SWITCH_IP, session=session
    )
    machine = switch_machine.machine
    if len(machine.switch_machines) <= 1:
        utils.add_db_object(
            session, models.SwitchMachine,
            False,
            default_switch.id, machine.id,
            port=switch_machine.port
        )
    return utils.del_db_object(session, switch_machine)


@utils.supported_filters()
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_DEL_SWITCH_MACHINE
)
@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
def del_switch_machine(
    switch_id, machine_id, user=None,
    session=None, **kwargs
):
    """Delete switch machine by switch id and machine id."""
    switch_machine = _get_switch_machine(
        switch_id, machine_id, session=session
    )
    return _del_switch_machine(switch_machine, session=session)


@utils.supported_filters()
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_DEL_SWITCH_MACHINE
)
@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
def del_switchmachine(switch_machine_id, user=None, session=None, **kwargs):
    """Delete switch machine by switch_machine_id."""
    switch_machine = _get_switchmachine(
        switch_machine_id, session=session
    )
    return _del_switch_machine(switch_machine, session=session)


@utils.supported_filters(
    ['machine_id'],
    optional_support_keys=UPDATED_SWITCH_MACHINES_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
def _add_machine_to_switch(
    switch_id, machine_id, session=None, **kwargs
):
    """Add machine to switch."""
    switch = _get_switch(switch_id, session=session)
    from compass.db.api import machine as machine_api
    machine = machine_api.get_machine_internal(
        machine_id, session=session
    )
    _add_switch_machine_only(
        switch, machine, False,
        owner_id=machine.owner_id, **kwargs
    )


def _add_machines(switch, machines, session=None):
    """Add machines to switch.

    Args:
       machines: list of dict which contains attributes to
                 add machine to switch.

    machines example:
       {{'machine_id': 1, 'port': 'ae20'}]
    """
    for machine in machines:
        _add_machine_to_switch(
            switch.id, session=session, **machine
        )


def _remove_machines(switch, machines, session=None):
    """Remove machines from switch.

    Args:
        machines: list of machine id.

    machines example:
        [1,2]
    """
    utils.del_db_objects(
        session, models.SwitchMachine,
        switch_id=switch.id, machine_id=machines
    )


def _set_machines(switch, machines, session=None):
    """Reset machines to a switch.

    Args:
       machines: list of dict which contains attributes to
                 add machine to switch.

    machines example:
       {{'machine_id': 1, 'port': 'ae20'}]
    """
    utils.del_db_objects(
        session, models.SwitchMachine,
        switch_id=switch.id
    )
    for switch_machine in machines:
        _add_machine_to_switch(
            switch.id, session=session, **switch_machine
        )


@utils.supported_filters(
    optional_support_keys=[
        'add_machines', 'remove_machines', 'set_machines'
    ]
)
@database.run_in_session()
@user_api.check_user_permission(
    permission.PERMISSION_UPDATE_SWITCH_MACHINES
)
@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
def update_switch_machines(
    switch_id, add_machines=[], remove_machines=[],
    set_machines=None, user=None, session=None, **kwargs
):
    """update switch's machines"""
    switch = _get_switch(switch_id, session=session)
    if remove_machines:
        _remove_machines(
            switch, remove_machines, session=session
        )
    if add_machines:
        _add_machines(
            switch, add_machines, session=session
        )
    if set_machines is not None:
        _set_machines(
            switch, set_machines, session=session
        )
    return switch.switch_machines
