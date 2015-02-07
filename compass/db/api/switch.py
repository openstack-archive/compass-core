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


SUPPORTED_FIELDS = ['ip_int', 'vendor', 'state']
SUPPORTED_FILTER_FIELDS = ['ip_int', 'vendor', 'state']
SUPPORTED_SWITCH_MACHINES_FIELDS = [
    'switch_ip_int', 'port', 'vlans', 'mac', 'tag', 'location'
]
SUPPORTED_MACHINES_FIELDS = [
    'port', 'vlans', 'mac', 'tag', 'location'
]
SUPPORTED_SWITCH_MACHINES_HOSTS_FIELDS = [
    'switch_ip_int', 'port', 'vlans', 'mac',
    'tag', 'location', 'os_name', 'os_id'
]
SUPPORTED_MACHINES_HOSTS_FIELDS = [
    'port', 'vlans', 'mac', 'tag', 'location',
    'os_name', 'os_id'
]
IGNORE_FIELDS = ['id', 'created_at', 'updated_at']
ADDED_FIELDS = ['ip']
OPTIONAL_ADDED_FIELDS = [
    'credentials', 'vendor', 'state', 'err_msg', 'filters'
]
UPDATED_FIELDS = [
    'ip', 'credentials', 'vendor', 'state',
    'err_msg', 'put_filters'
]
PATCHED_FIELDS = ['patched_credentials', 'patched_filters']
UPDATED_FILTERS_FIELDS = ['put_filters']
PATCHED_FILTERS_FIELDS = ['patched_filters']
ADDED_MACHINES_FIELDS = ['mac', 'port']
OPTIONAL_ADDED_MACHINES_FIELDS = [
    'vlans', 'ipmi_credentials', 'tag', 'location'
]
ADDED_SWITCH_MACHINES_FIELDS = ['port', 'vlans']
UPDATED_MACHINES_FIELDS = [
    'port', 'vlans', 'ipmi_credentials',
    'tag', 'location'
]
UPDATED_SWITCH_MACHINES_FIELDS = ['port', 'vlans']
PATCHED_MACHINES_FIELDS = [
    'patched_vlans', 'patched_ipmi_credentials',
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
    'port', 'vlans', 'mac',
    'ipmi_credentials', 'tag', 'location',
    'created_at', 'updated_at'
]
RESP_MACHINES_HOSTS_FIELDS = [
    'id', 'switch_id', 'switch_ip', 'machine_id', 'switch_machine_id',
    'port', 'vlans', 'mac',
    'ipmi_credentials', 'tag', 'location', 'ip',
    'name', 'hostname', 'os_name', 'os_id', 'owner',
    'os_installer', 'reinstall_os', 'os_installed',
    'clusters', 'created_at', 'updated_at'
]
RESP_CLUSTER_FIELDS = [
    'name', 'id'
]


def _check_filters(switch_filters):
    logging.debug('check filters: %s', switch_filters)
    models.Switch.parse_filters(switch_filters)


def _check_vlans(vlans):
    for vlan in vlans:
        if not isinstance(vlan, int):
            raise exception.InvalidParameter(
                'vlan %s is not int' % vlan
            )


def add_switch_internal(
    session, ip_int, exception_when_existing=True,
    filters=setting.SWITCHES_DEFAULT_FILTERS, **kwargs
):
    with session.begin(subtransactions=True):
        return utils.add_db_object(
            session, models.Switch, exception_when_existing, ip_int,
            filters=filters, **kwargs
        )


def get_switch_internal(
    session, exception_when_missing=True, **kwargs
):
    """Get switch."""
    with session.begin(subtransactions=True):
        return utils.get_db_object(
            session, models.Switch, exception_when_missing,
            **kwargs
        )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_SWITCHES
)
@utils.wrap_to_dict(RESP_FIELDS)
def get_switch(
    switch_id, exception_when_missing=True,
    user=None, session=None, **kwargs
):
    """get field dict of a switch."""
    return utils.get_db_object(
        session, models.Switch,
        exception_when_missing, id=switch_id
    )


@utils.supported_filters(optional_support_keys=SUPPORTED_FIELDS)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_SWITCHES
)
@utils.wrap_to_dict(RESP_FIELDS)
def list_switches(user=None, session=None, **filters):
    """List switches."""
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
@user_api.check_user_permission_in_session(
    permission.PERMISSION_DEL_SWITCH
)
@utils.wrap_to_dict(RESP_FIELDS)
def del_switch(switch_id, user=None, session=None, **kwargs):
    """Delete a switch."""
    switch = utils.get_db_object(session, models.Switch, id=switch_id)
    default_switch_ip_int = long(netaddr.IPAddress(setting.DEFAULT_SWITCH_IP))
    default_switch = utils.get_db_object(
        session, models.Switch,
        ip_int=default_switch_ip_int
    )
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


@utils.supported_filters(
    ADDED_FIELDS,
    optional_support_keys=OPTIONAL_ADDED_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(
    ip=utils.check_ip,
    credentials=utils.check_switch_credentials,
    filters=_check_filters
)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_SWITCH
)
@utils.wrap_to_dict(RESP_FIELDS)
def add_switch(
    exception_when_existing=True, ip=None,
    user=None, session=None, **kwargs
):
    """Create a switch."""
    ip_int = long(netaddr.IPAddress(ip))
    return add_switch_internal(
        session, ip_int, exception_when_existing, **kwargs
    )


def update_switch_internal(session, switch, **kwargs):
    """update switch."""
    return utils.update_db_object(
        session, switch,
        **kwargs
    )


@utils.wrap_to_dict(RESP_FIELDS)
def _update_switch(session, switch_id, **kwargs):
    """Update a switch."""
    switch = utils.get_db_object(
        session, models.Switch, id=switch_id
    )
    return utils.update_db_object(session, switch, **kwargs)


@utils.replace_filters(
    filters='put_filters'
)
@utils.supported_filters(
    optional_support_keys=UPDATED_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(
    credentials=utils.check_switch_credentials,
    put_filters=_check_filters
)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_SWITCH
)
def update_switch(switch_id, user=None, session=None, **kwargs):
    """Update fields of a switch."""
    return _update_switch(session, switch_id, **kwargs)


@utils.replace_filters(
    credentials='patched_credentials',
    filters='patched_filters'
)
@utils.supported_filters(
    optional_support_keys=PATCHED_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(
    patched_filters=_check_filters
)
@database.run_in_session()
@utils.output_validates(
    credentials=utils.check_switch_credentials
)
@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_SWITCH
)
def patch_switch(switch_id, user=None, session=None, **kwargs):
    """Patch fields of a switch."""
    return _update_switch(session, switch_id, **kwargs)


@utils.supported_filters(optional_support_keys=SUPPORTED_FILTER_FIELDS)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_SWITCH_FILTERS
)
@utils.wrap_to_dict(RESP_FILTERS_FIELDS)
def list_switch_filters(user=None, session=None, **filters):
    """List switch filters."""
    return utils.list_db_objects(
        session, models.Switch, **filters
    )


@utils.supported_filters()
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_SWITCH_FILTERS
)
@utils.wrap_to_dict(RESP_FILTERS_FIELDS)
def get_switch_filters(
    switch_id, user=None, session=None, **kwargs
):
    """get switch filter."""
    return utils.get_db_object(
        session, models.Switch, id=switch_id
    )


@utils.replace_filters(
    filters='put_filters'
)
@utils.supported_filters(
    optional_support_keys=UPDATED_FILTERS_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(put_filters=_check_filters)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_UPDATE_SWITCH_FILTERS
)
@utils.wrap_to_dict(RESP_FILTERS_FIELDS)
def update_switch_filters(switch_id, user=None, session=None, **kwargs):
    """Update a switch filter."""
    switch = utils.get_db_object(session, models.Switch, id=switch_id)
    return utils.update_db_object(session, switch, **kwargs)


@utils.replace_filters(
    filters='patched_filters'
)
@utils.supported_filters(
    optional_support_keys=PATCHED_FILTERS_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(patched_filters=_check_filters)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_UPDATE_SWITCH_FILTERS
)
@utils.wrap_to_dict(RESP_FILTERS_FIELDS)
def patch_switch_filter(switch_id, user=None, session=None, **kwargs):
    """Patch a switch filter."""
    switch = utils.get_db_object(session, models.Switch, id=switch_id)
    return utils.update_db_object(session, switch, **kwargs)


def get_switch_machines_internal(session, **filters):
    return utils.list_db_objects(
        session, models.SwitchMachine, **filters
    )


def _filter_port(port_filter, obj):
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
        in_range = False
        for port_start, port_end in port_filter['resp_range']:
            if port_start <= port_number <= port_end:
                in_range = True
                break
        if not in_range:
            return False
    return True


def _filter_vlans(vlan_filter, obj):
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
def _filter_switch_machines(session, switch_machines):
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
    os_id=utils.general_filter_callback
)
@utils.wrap_to_dict(
    RESP_MACHINES_HOSTS_FIELDS,
    clusters=RESP_CLUSTER_FIELDS
)
def _filter_switch_machines_hosts(session, switch_machines):
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
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_SWITCH_MACHINES
)
def list_switch_machines(switch_id, user=None, session=None, **filters):
    """Get switch machines."""
    switch_machines = get_switch_machines_internal(
        session, switch_id=switch_id, **filters
    )
    return _filter_switch_machines(session, switch_machines)


@utils.replace_filters(
    ip_int='switch_ip_int'
)
@utils.supported_filters(
    optional_support_keys=SUPPORTED_SWITCH_MACHINES_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_SWITCH_MACHINES
)
def list_switchmachines(user=None, session=None, **filters):
    """List switch machines."""
    switch_machines = get_switch_machines_internal(
        session, **filters
    )
    return _filter_switch_machines(
        session, switch_machines
    )


@utils.supported_filters(
    optional_support_keys=SUPPORTED_MACHINES_HOSTS_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_SWITCH_MACHINES
)
def list_switch_machines_hosts(switch_id, user=None, session=None, **filters):
    """Get switch machines hosts."""
    switch_machines = get_switch_machines_internal(
        session, switch_id=switch_id, **filters
    )
    return _filter_switch_machines_hosts(
        session, switch_machines
    )


@utils.replace_filters(
    ip_int='switch_ip_int'
)
@utils.supported_filters(
    optional_support_keys=SUPPORTED_SWITCH_MACHINES_HOSTS_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_SWITCH_MACHINES
)
def list_switchmachines_hosts(user=None, session=None, **filters):
    """List switch machines hosts."""
    switch_machines = get_switch_machines_internal(
        session, **filters
    )
    if 'ip_int' in filters:
        filtered_switch_machines = switch_machines
    else:
        filtered_switch_machines = [
            switch_machine for switch_machine in switch_machines
        ]
    return _filter_switch_machines_hosts(
        session, filtered_switch_machines
    )


@utils.supported_filters(
    ADDED_MACHINES_FIELDS,
    optional_support_keys=OPTIONAL_ADDED_MACHINES_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(mac=utils.check_mac, vlans=_check_vlans)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_SWITCH_MACHINE
)
@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
def add_switch_machine(
    switch_id, exception_when_existing=True,
    mac=None, user=None, session=None, **kwargs
):
    """Add switch machine."""
    switch = utils.get_db_object(
        session, models.Switch, id=switch_id)
    switch_machine_dict = {}
    machine_dict = {}
    for key, value in kwargs.items():
        if key in ADDED_SWITCH_MACHINES_FIELDS:
            switch_machine_dict[key] = value
        else:
            machine_dict[key] = value
    machine = utils.add_db_object(
        session, models.Machine, False,
        mac, **machine_dict)

    return utils.add_db_object(
        session, models.SwitchMachine,
        exception_when_existing,
        switch.id, machine.id,
        **switch_machine_dict
    )


@utils.supported_filters(optional_support_keys=['find_machines'])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_UPDATE_SWITCH_MACHINES
)
@utils.wrap_to_dict(RESP_ACTION_FIELDS)
def poll_switch_machines(switch_id, user=None, session=None, **kwargs):
    """poll switch machines."""
    from compass.tasks import client as celery_client
    switch = utils.get_db_object(session, models.Switch, id=switch_id)
    celery_client.celery.send_task(
        'compass.tasks.pollswitch',
        (user.email, switch.ip, switch.credentials)
    )
    return {
        'status': 'action %s sent' % kwargs,
        'details': {
        }
    }


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_SWITCH_MACHINES
)
@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
def get_switch_machine(
    switch_id, machine_id, exception_when_missing=True,
    user=None, session=None, **kwargs
):
    """get field dict of a switch machine."""
    return utils.get_db_object(
        session, models.SwitchMachine,
        exception_when_missing,
        switch_id=switch_id, machine_id=machine_id
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_SWITCH_MACHINES
)
@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
def get_switchmachine(
    switch_machine_id, exception_when_missing=True,
    user=None, session=None, **kwargs
):
    """get field dict of a switch machine."""
    return utils.get_db_object(
        session, models.SwitchMachine,
        exception_when_missing, switch_machine_id=switch_machine_id
    )


def update_switch_machine_internal(
    session, switch_machine, switch_machines_fields, **kwargs
):
    """Update switch machine internal."""
    switch_machine_dict = {}
    machine_dict = {}
    for key, value in kwargs.items():
        if key in switch_machines_fields:
            switch_machine_dict[key] = value
        else:
            machine_dict[key] = value
    if machine_dict:
        utils.update_db_object(
            session, switch_machine.machine, **machine_dict
        )
    return utils.update_db_object(
        session, switch_machine, **switch_machine_dict
    )


@utils.supported_filters(
    optional_support_keys=UPDATED_MACHINES_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(vlans=_check_vlans)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_SWITCH_MACHINE
)
@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
def update_switch_machine(
    switch_id, machine_id, user=None,
    session=None, **kwargs
):
    """Update switch machine."""
    switch_machine = utils.get_db_object(
        session, models.SwitchMachine,
        switch_id=switch_id, machine_id=machine_id
    )
    return update_switch_machine_internal(
        session, switch_machine,
        UPDATED_SWITCH_MACHINES_FIELDS, **kwargs
    )


@utils.supported_filters(
    optional_support_keys=UPDATED_MACHINES_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(vlans=_check_vlans)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_SWITCH_MACHINE
)
@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
def update_switchmachine(switch_machine_id, user=None, session=None, **kwargs):
    """Update switch machine."""
    switch_machine = utils.get_db_object(
        session, models.SwitchMachine,
        switch_machine_id=switch_machine_id
    )
    return update_switch_machine_internal(
        session, switch_machine,
        UPDATED_SWITCH_MACHINES_FIELDS, **kwargs
    )


@utils.replace_filters(
    vlans='patched_vlans',
    ipmi_credentials='patched_ipmi_credentials',
    tag='patched_tag',
    location='patched_location'
)
@utils.supported_filters(
    optional_support_keys=PATCHED_MACHINES_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(patched_vlans=_check_vlans)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_SWITCH_MACHINE
)
@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
def patch_switch_machine(
    switch_id, machine_id, user=None,
    session=None, **kwargs
):
    """Patch switch machine."""
    switch_machine = utils.get_db_object(
        session, models.SwitchMachine,
        switch_id=switch_id, machine_id=machine_id
    )
    return update_switch_machine_internal(
        session, switch_machine,
        PATCHED_SWITCH_MACHINES_FIELDS, **kwargs
    )


@utils.replace_filters(
    vlans='patched_vlans',
    ipmi_credentials='patched_ipmi_credentials',
    tag='patched_tag',
    location='patched_location'
)
@utils.supported_filters(
    optional_support_keys=PATCHED_MACHINES_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
@utils.input_validates(patched_vlans=_check_vlans)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_SWITCH_MACHINE
)
@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
def patch_switchmachine(switch_machine_id, user=None, session=None, **kwargs):
    """Patch switch machine."""
    switch_machine = utils.get_db_object(
        session, models.SwitchMachine,
        switch_machine_id=switch_machine_id
    )
    return update_switch_machine_internal(
        session, switch_machine,
        PATCHED_SWITCH_MACHINES_FIELDS, **kwargs
    )


@utils.supported_filters()
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_DEL_SWITCH_MACHINE
)
@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
def del_switch_machine(
    switch_id, machine_id, user=None,
    session=None, **kwargs
):
    """Delete switch machine by switch id and machine id."""
    switch_machine = utils.get_db_object(
        session, models.SwitchMachine,
        switch_id=switch_id, machine_id=machine_id
    )
    default_switch_ip_int = long(netaddr.IPAddress(setting.DEFAULT_SWITCH_IP))
    default_switch = utils.get_db_object(
        session, models.Switch,
        ip_int=default_switch_ip_int
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
@user_api.check_user_permission_in_session(
    permission.PERMISSION_DEL_SWITCH_MACHINE
)
@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
def del_switchmachine(switch_machine_id, user=None, session=None, **kwargs):
    """Delete switch machine by switch_machine_id."""
    switch_machine = utils.get_db_object(
        session, models.SwitchMachine,
        switch_machine_id=switch_machine_id
    )
    default_switch_ip_int = long(netaddr.IPAddress(setting.DEFAULT_SWITCH_IP))
    default_switch = utils.get_db_object(
        session, models.Switch,
        ip_int=default_switch_ip_int
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


@utils.supported_filters(
    ['machine_id'],
    optional_support_keys=UPDATED_SWITCH_MACHINES_FIELDS,
    ignore_support_keys=IGNORE_FIELDS
)
def _update_machine_internal(session, switch_id, machine_id, **kwargs):
    utils.add_db_object(
        session, models.SwitchMachine, False,
        switch_id, machine_id, **kwargs
    )


def _add_machines(session, switch, machines):
    for machine in machines:
        _update_machine_internal(
            session, switch.id, **machine
        )


def _remove_machines(session, switch, machines):
    utils.del_db_objects(
        session, models.SwitchMachine,
        switch_id=switch.id, machine_id=machines
    )


def _set_machines(session, switch, machines):
    utils.del_db_objects(
        session, models.SwitchMachine,
        switch_id=switch.id
    )
    for switch_machine in machines:
        _update_machine_internal(
            session, switch.id, **switch_machine
        )


@utils.supported_filters(
    optional_support_keys=[
        'add_machines', 'remove_machines', 'set_machines'
    ]
)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_UPDATE_SWITCH_MACHINES
)
@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
def update_switch_machines(
    switch_id, add_machines=[], remove_machines=[],
    set_machines=None, user=None, session=None, **kwargs
):
    """update switch machines."""
    switch = utils.get_db_object(
        session, models.Switch, id=switch_id
    )
    if remove_machines:
        _remove_machines(
            session, switch, remove_machines
        )
    if add_machines:
        _add_machines(
            session, switch, add_machines
        )
    if set_machines is not None:
        _set_machines(
            session, switch,
            set_machines
        )
    return switch.switch_machines
