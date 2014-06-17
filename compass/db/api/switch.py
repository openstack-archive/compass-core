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
SUPPORTED_SWITCH_MACHINES_FIELDS = ['ip_int', 'port', 'vlans', 'mac', 'tag']
SUPPORTED_MACHINES_FIELDS = ['port', 'vlans', 'mac', 'tag']
ADDED_FIELDS = ['ip']
OPTIONAL_ADDED_FIELDS = ['credentials', 'vendor', 'state', 'err_msg']
UPDATED_FIELDS = ['credentials', 'vendor', 'state', 'err_msg']
PATCHED_FIELDS = ['patched_credentials']
UPDATED_FILTERS_FIELDS = ['filters']
PATCHED_FILTERS_FIELDS = ['patched_filters']
ADDED_MACHINES_FIELDS = ['mac', 'port']
OPTIONAL_ADDED_MACHINES_FIELDS = [
    'vlans', 'ipmi_credentials', 'tag', 'location'
]
ALL_ADDED_MACHINES_FIELDS = ['port', 'vlans']
UPDATED_MACHINES_FIELDS = [
    'port', 'vlans', 'ipmi_credentials',
    'tag', 'location'
]
ALL_UPDATED_MACHINES_FIELDS = ['port', 'vlans']
PATCHED_MACHINES_FIELDS = [
    'patched_vlans', 'patched_ipmi_credentials',
    'patched_tag', 'patched_location'
]
ALL_PATCHED_MACHINES_FIELDS = ['patched_vlans']

RESP_FIELDS = [
    'id', 'ip', 'credentials', 'vendor', 'state', 'err_msg',
    'created_at', 'updated_at'
]
RESP_FILTERS_FIELDS = [
    'id', 'ip', 'filters', 'created_at', 'updated_at'
]
RESP_ACTION_FIELDS = [
    'status', 'details'
]
RESP_MACHINES_FIELDS = [
    'id', 'switch_id', 'machine_id', 'port', 'vlans', 'mac',
    'ipmi_credentials', 'tag', 'location',
    'created_at', 'updated_at'
]


def _check_credentials_version(version):
    if version not in ['1', '2c', '3']:
        raise exception.InvalidParameter(
            'unknown snmp version %s' % version
        )


def _check_credentials(credentials):
    if not credentials:
        return
    if not isinstance(credentials, dict):
        raise exception.InvalidParameter(
            'credentials %s is not dict' % credentials
        )
    for key in credentials:
        if key not in ['version', 'community']:
            raise exception.InvalidParameter(
                'unrecognized key %s in credentials %s' % (key, credentials)
            )
    for key in ['version', 'community']:
        if key not in credentials:
            raise exception.InvalidParameter(
                'there is no %s field in credentials %s' % (key, credentials)
            )

        key_check_func_name = '_check_credentials_%s' % key
        this_module = globals()
        if key_check_func_name in this_module:
            this_module[key_check_func_name](
                credentials[key]
            )
        else:
            logging.debug(
                'function %s is not defined in %s',
                key_check_func_name, this_module
            )


def _check_filter(switch_filter):
    if not isinstance(switch_filter, dict):
        raise exception.InvalidParameter(
            'filter %s is not dict' % switch_filter
        )
    filter_format_ok = True
    messages = []
    if 'filter_name' not in switch_filter:
        filter_format_ok = False
        messages.append('`filter_name` does not exist')
    if 'filter_type' not in switch_filter:
        filter_format_ok = False
        messages.append('`filter_type` does not exist')
    else:
        if switch_filter['filter_type'] not in ['allow', 'deny']:
            filter_format_ok = False
            messages.append(
                '`filter_type` should be one of [`allow`, `deny`]'
            )
    if 'ports' in switch_filter:
        if not isinstance(switch_filter['ports'], list):
            filter_format_ok = False
            messages.append('value of `ports` is not list')
    for key in ['port_start', 'port_end']:
        if key in switch_filter:
            if not isinstance(switch_filter[key], int):
                filter_format_ok = False
                messages.append('value of `%s` is not int' % key)
    for key in switch_filter:
        if key not in [
            'filter_name', 'filter_type',
            'ports', 'port_prefix', 'port_suffix',
            'port_start', 'port_end'
        ]:
            filter_format_ok = False
            messages.append('unknown key `%s`' % key)
    if not filter_format_ok:
        raise exception.InvalidParameter(
            'filter %s format is not OK: %s' % (switch_filter, messages)
        )


def _check_vlan(vlan):
    if not isinstance(vlan, int):
        raise exception.InvalidParameter(
            'vlan %s format is not OK' % vlan
        )


def add_switch_internal(
    session, ip_int, exception_when_existing=True, **kwargs
):
    with session.begin(subtransactions=True):
        return utils.add_db_object(
            session, models.Switch, exception_when_existing, ip_int,
            filters=setting.SWITCHES_DEFAULT_FILTERS, **kwargs
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


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters([])
def get_switch(getter, switch_id, **kwargs):
    """get field dict of a switch."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_LIST_SWITCHES)
        return utils.get_db_object(
            session, models.Switch, id=switch_id
        ).to_dict()


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters(optional_support_keys=SUPPORTED_FIELDS)
def list_switches(lister, **filters):
    """List switches."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, lister, permission.PERMISSION_LIST_SWITCHES)
        return [
            switch.to_dict()
            for switch in utils.list_db_objects(
                session, models.Switch, **filters
            )
        ]


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters([])
def del_switch(deleter, switch_id, **kwargs):
    """Delete a switch."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, deleter, permission.PERMISSION_DEL_SWITCH)
        switch = utils.get_db_object(session, models.Switch, id=switch_id)
        utils.del_db_object(session, switch)
        return switch.to_dict()


@utils.wrap_to_dict(RESP_FIELDS)
@utils.input_validates(
    ip=utils.check_ip,
    credentials=_check_credentials
)
@utils.supported_filters(
    ADDED_FIELDS,
    optional_support_keys=OPTIONAL_ADDED_FIELDS
)
def add_switch(creator, ip, **kwargs):
    """Create a switch."""
    ip_int = long(netaddr.IPAddress(ip))
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, creator, permission.PERMISSION_ADD_SWITCH)
        return add_switch_internal(
            session, ip_int, **kwargs
        ).to_dict()


def update_switch_internal(session, switch, **kwargs):
    """update switch."""
    with session.begin(subtransactions=True):
        return utils.update_db_object(
            session, switch,
            **kwargs
        )


def _update_switch(updater, switch_id, **kwargs):
    """Update a switch."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_ADD_SWITCH)
        switch = utils.get_db_object(
            session, models.Switch, id=switch_id
        )
        utils.update_db_object(session, switch, **kwargs)
        switch_dict = switch.to_dict()
        utils.validate_outputs(
            {'credentials': _check_credentials},
            switch_dict
        )
        return switch_dict


@utils.wrap_to_dict(RESP_FIELDS)
@utils.input_validates(credentials=_check_credentials)
@utils.supported_filters(optional_support_keys=UPDATED_FIELDS)
def update_switch(updater, switch_id, **kwargs):
    _update_switch(updater, switch_id, **kwargs)


@utils.wrap_to_dict(RESP_FIELDS)
@utils.supported_filters(optional_support_keys=PATCHED_FIELDS)
def patch_switch(updater, switch_id, **kwargs):
    _update_switch(updater, switch_id, **kwargs)


@utils.wrap_to_dict(RESP_FILTERS_FIELDS)
@utils.supported_filters(optional_support_keys=SUPPORTED_FILTER_FIELDS)
def list_switch_filters(lister, **filters):
    """list switch filters."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, lister, permission.PERMISSION_LIST_SWITCHES
        )
        return [
            switch.to_dict()
            for switch in utils.list_db_objects(
                session, models.Switch, **filters
            )
        ]


@utils.wrap_to_dict(RESP_FILTERS_FIELDS)
@utils.supported_filters()
def get_switch_filters(getter, switch_id, **kwargs):
    """get switch filter."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_LIST_SWITCHES)
        return utils.get_db_object(
            session, models.Switch, id=switch_id
        ).to_dict()


@utils.wrap_to_dict(RESP_FILTERS_FIELDS)
@utils.input_validates(filters=_check_filter)
@utils.supported_filters(optional_support_keys=UPDATED_FILTERS_FIELDS)
def update_switch_filters(updater, switch_id, **kwargs):
    """Update a switch filter."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_ADD_SWITCH)
        switch = utils.get_db_object(session, models.Switch, id=switch_id)
        utils.update_db_object(session, switch, **kwargs)
        return switch.to_dict()


@utils.wrap_to_dict(RESP_FILTERS_FIELDS)
@utils.input_validates(patched_filters=_check_filter)
@utils.supported_filters(optional_support_keys=PATCHED_FILTERS_FIELDS)
def patch_switch_filter(updater, switch_id, **kwargs):
    """Update a switch."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_ADD_SWITCH)
        switch = utils.get_db_object(session, models.Switch, id=switch_id)
        utils.update_db_object(session, switch, **kwargs)
        return switch.to_dict()


def filter_machine_internal(filters, port):
    for port_filter in filters:
        logging.debug('apply filter %s on port %s', port_filter, port)
        filter_allowed = port_filter['filter_type'] == 'allow'
        if 'ports' in port_filter:
            if port in port_filter['ports']:
                logging.debug('port is allowed? %s', filter_allowed)
                return filter_allowed
            else:
                logging.debug('port is allowed? %s', not filter_allowed)
                return not filter_allowed
        port_prefix = port_filter.get('port_prefix', '')
        port_suffix = port_filter.get('port_suffix', '')
        pattern = re.compile(r'%s(\d+)%s' % (port_prefix, port_suffix))
        match = pattern.match(port)
        if match:
            logging.debug(
                'port %s matches pattern %s',
                port, pattern.pattern
            )
            port_number = match.group(1)
            if (
                'port_start' not in port_filter or
                port_number >= port_filter['port_start']
            ) and (
                'port_end' not in port_filter or
                port_number <= port_filter['port_end']
            ):
                logging.debug('port is allowed? %s', filter_allowed)
                return filter_allowed
        else:
            logging.debug(
                'port %s does not match pattern %s',
                port, pattern.pattern
            )
    return True


def get_switch_machines_internal(session, **filters):
    with session.begin(subtransactions=True):
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


@utils.output_filters(port=_filter_port, vlans=_filter_vlans)
@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
@utils.supported_filters(optional_support_keys=SUPPORTED_MACHINES_FIELDS)
def get_switch_machines(getter, switch_id, **filters):
    """Get switch machines."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_LIST_SWITCHES)
        switch = utils.get_db_object(session, models.Switch, id=switch_id)
        switch_machines = [
            switch_machine
            for switch_machine in get_switch_machines_internal(
                session, switch_id=switch_id, **filters
            )
            if filter_machine_internal(switch.filters, switch_machine.port)
        ]
        return [
            switch_machine.to_dict()
            for switch_machine in switch_machines
        ]


@utils.output_filters(port=_filter_port, vlans=_filter_vlans)
@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
@utils.supported_filters(
    optional_support_keys=SUPPORTED_SWITCH_MACHINES_FIELDS
)
def list_switch_machines(getter, **filters):
    """List switch machines."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_LIST_SWITCHES)
        switch_machines = [
            switch_machine
            for switch_machine in get_switch_machines_internal(
                session, **filters
            )
            if filter_machine_internal(
                switch_machine.switch.filters, switch_machine.port
            )
        ]
        return [
            switch_machine.to_dict()
            for switch_machine in switch_machines
        ]


def add_switch_machines_internal(
    session, switch, machine_dicts,
    exception_when_switch_machine_existing=True
):
    with session.begin(subtransactions=True):
        machine_id_switch_machine_dict = {}
        for mac, all_dict in machine_dicts.items():
            switch_machine_dict = {}
            machine_dict = {}
            for key, value in all_dict.items():
                if key in ALL_ADDED_MACHINES_FIELDS:
                    switch_machine_dict[key] = value
                else:
                    machine_dict[key] = value
            #TODO(xiaodong): add ipmi field checks'
            machine = utils.add_db_object(
                session, models.Machine, False,
                mac, **machine_dict)
            machine_id_switch_machine_dict[machine.id] = switch_machine_dict

        switches = [switch]
        if switch.ip != setting.DEFAULT_SWITCH_IP:
            switches.append(utils.get_db_object(
                session, models.Switch,
                ip_int=long(netaddr.IPAddress(setting.DEFAULT_SWITCH_IP))
            ))

        switch_machines = []
        for machine_switch in switches:
            for machine_id, switch_machine_dict in (
                machine_id_switch_machine_dict.items()
            ):
                utils.add_db_object(
                    session, models.SwitchMachine,
                    exception_when_switch_machine_existing,
                    machine_switch.id, machine_id, **switch_machine_dict
                )
            switch_machines.extend(machine_switch.switch_machines)

        return switch_machines


@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
@utils.input_validates(mac=utils.check_mac, vlans=_check_vlan)
@utils.supported_filters(
    ADDED_MACHINES_FIELDS,
    optional_support_keys=OPTIONAL_ADDED_MACHINES_FIELDS
)
def add_switch_machine(creator, switch_id, mac, port, **kwargs):
    """Add switch machine."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, creator, permission.PERMISSION_ADD_MACHINE)
        switch = utils.get_db_object(
            session, models.Switch, id=switch_id)
        kwargs['port'] = port
        switch_machines = add_switch_machines_internal(
            session, switch, {mac: kwargs})
        return switch_machines[0].to_dict()


@utils.wrap_to_dict(RESP_ACTION_FIELDS)
@utils.supported_filters()
def poll_switch_machines(poller, switch_id, **kwargs):
    """poll switch machines."""
    from compass.tasks import client as celery_client
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, poller, permission.PERMISSION_ADD_MACHINE)
        switch = utils.get_db_object(session, models.Switch, id=switch_id)
        print 'send poll switch to celery'
        celery_client.celery.send_task(
            'compass.tasks.pollswitch',
            (switch.ip, switch.credentials)
        )
        return {
            'status': 'find_machines action sent',
            'details': {
            }
        }


@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
@utils.supported_filters([])
def get_switch_machine(getter, switch_machine_id, **kwargs):
    """get field dict of a switch machine."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, getter, permission.PERMISSION_LIST_MACHINES)
        return utils.get_db_object(
            session, models.SwitchMachine, id=switch_machine_id
        ).to_dict()


def _update_switch_machine(
    updater, switch_machine_id, machines_fields, **kwargs
):
    """Update switch machine."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, updater, permission.PERMISSION_ADD_MACHINE)
        switch_machine = utils.get_db_object(
            session, models.SwitchMachine,
            id=switch_machine_id
        )
        switch_machine_dict = {}
        machine_dict = {}
        for key, value in kwargs.items():
            if key in machines_fields:
                switch_machine_dict[key] = value
            else:
                machine_dict[key] = value
        utils.update_db_object(
            session, switch_machine, **switch_machine_dict
        )
        if machine_dict:
            utils.update_db_object(
                session, switch_machine.machine, **machine_dict
            )
        return switch_machine.to_dict()


@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
@utils.input_validates(vlans=_check_vlan)
@utils.supported_filters(optional_support_keys=UPDATED_MACHINES_FIELDS)
def update_switch_machine(updater, switch_machine_id, **kwargs):
    return _update_switch_machine(
        updater, switch_machine_id, ALL_UPDATED_MACHINES_FIELDS, **kwargs
    )


@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
@utils.input_validates(patched_vlans=_check_vlan)
@utils.supported_filters(optional_support_keys=PATCHED_MACHINES_FIELDS)
def patch_switch_machine(updater, switch_machine_id, **kwargs):
    return _update_switch_machine(
        updater, switch_machine_id, ALL_PATCHED_MACHINES_FIELDS, **kwargs
    )


@utils.wrap_to_dict(RESP_MACHINES_FIELDS)
@utils.supported_filters()
def del_switch_machine(deleter, switch_machine_id, **kwargs):
    """Delete switch machines."""
    with database.session() as session:
        user_api.check_user_permission_internal(
            session, deleter, permission.PERMISSION_DEL_MACHINE
        )
        switch_machine = utils.get_db_object(
            session, models.SwitchMachine,
            id=switch_machine_id
        )
        utils.del_db_object(session, switch_machine)
        return switch_machine.to_dict()
