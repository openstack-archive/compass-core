#!/usr/bin/python
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

"""Define all the RestfulAPI entry points."""
import datetime
import functools
import netaddr
import simplejson as json

from flask import flash
from flask import redirect
from flask import request
from flask import session as app_session
from flask import url_for

from flask.ext.login import current_user
from flask.ext.login import login_required
from flask.ext.login import login_user
from flask.ext.login import logout_user

from compass.api import app
from compass.api import auth_handler
from compass.api import exception_handler
from compass.api import utils
from compass.db.api import adapter_holder as adapter_api
from compass.db.api import cluster as cluster_api
from compass.db.api import host as host_api
from compass.db.api import machine as machine_api
from compass.db.api import metadata_holder as metadata_api
from compass.db.api import network as network_api
from compass.db.api import permission as permission_api
from compass.db.api import switch as switch_api
from compass.db.api import user as user_api
from compass.db.api import user_log as user_log_api
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import util


def log_user_action(func):
    @functools.wraps(func)
    def decorated_api(*args, **kwargs):
        user_log_api.log_user_action(current_user.id, request.path)
        return func(*args, **kwargs)
    return decorated_api


def _clean_data(data, keys):
    for key in keys:
        if key in data:
            del data[key]


def _replace_data(data, key_mapping):
    for key, replaced_key in key_mapping.items():
        if key in data:
            data[replaced_key] = data[key]
            del data[key]


def _get_data(data, key):
    if key in data:
        if isinstance(data[key], list):
            if data[key]:
                if len(data[key]) == 1:
                    return data[key][0]
                else:
                    raise exception_handler.BadRequest(
                        '%s declared multi times %s in request' % (
                            key, data[key]
                        )
                    )
            else:
                return None
        else:
            return data[key]
    else:
        return None


def _get_data_list(data, key):
    if key in data:
        if isinstance(data[key], list):
            return data[key]
        else:
            return [data[key]]
    else:
        return []


def _get_request_data():
    if request.data:
        try:
            return json.loads(request.data)
        except Exception:
            raise exception_handler.BadRequest(
                'request data is not json formatted: %s' % request.data
            )
    else:
        return {}


def _get_request_args():
    return dict(request.args)


def _login(use_cookie):
    """User login helper function."""
    data = _get_request_data()
    if 'email' not in data or 'password' not in data:
        raise exception_handler.BadRequest(
            'missing email or password in data'
        )
    if 'expires' not in data:
        expire_timestamp = (
            datetime.datetime.now() + app.config['REMEMBER_COOKIE_DURATION']
        )
    else:
        expire_timestamp = util.parse_datetime(
            data['expires'], exception_handler.BadRequest
        )

    data['expire_timestamp'] = expire_timestamp
    user = auth_handler.authenticate_user(**data)
    if not login_user(user, remember=data.get('remember', False)):
        raise exception_handler.UserDisabled('failed to login: %s' % user)

    user_log_api.log_user_action(user.id, request.path)
    response_data = {'id': user.id}
    response_data = user_api.record_user_token(
        user, user.token, user.expire_timestamp
    )
    return utils.make_json_response(200, response_data)


@app.route('/users/token', methods=['POST'])
def get_token():
    """Get token from email and password after user authentication."""
    return _login(False)


@app.route("/users/login", methods=['POST'])
def login():
    """User login."""
    return _login(True)


@app.route('/users/logout', methods=['POST'])
@login_required
def logout():
    """User logout."""
    user_log_api.log_user_action(current_user.id, request.path)
    response_data = user_api.clean_user_token(
        current_user, current_user.token
    )
    logout_user()
    return utils.make_json_response(200, response_data)


@app.route("/users", methods=['GET'])
@log_user_action
@login_required
def list_users():
    """list users."""
    data = _get_request_args()
    return utils.make_json_response(
        200, user_api.list_users(current_user, **data)
    )


@app.route("/users", methods=['POST'])
@log_user_action
@login_required
def add_user():
    """add user."""
    data = _get_request_data()
    user_dict = user_api.add_user(current_user, **data)
    return utils.make_json_response(
        200, user_dict
    )


@app.route("/users/<int:user_id>", methods=['GET'])
@log_user_action
@login_required
def show_user(user_id):
    """Get user."""
    data = _get_request_args()
    return utils.make_json_response(
        200, user_api.get_user(current_user, user_id, **data)
    )


@app.route("/users/<int:user_id>", methods=['PUT'])
@log_user_action
@login_required
def update_user(user_id):
    """Update user."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        user_api.update_user(
            current_user,
            user_id,
            **data
        )
    )


@app.route("/users/<int:user_id>", methods=['DELETE'])
@log_user_action
@login_required
def delete_user(user_id):
    """Delete user."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        user_api.del_user(
            current_user, user_id, **data
        )
    )


@app.route("/users/<int:user_id>/permissions", methods=['GET'])
@log_user_action
@login_required
def list_user_permissions(user_id):
    """Get user permissions."""
    data = _get_request_args()
    return utils.make_json_response(
        200, user_api.get_permissions(current_user, user_id, **data)
    )


@app.route("/users/<int:user_id>/permissions/actions", methods=['POST'])
@log_user_action
@login_required
def update_user_permissions(user_id):
    """Update user permissions."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        user_api.update_permissions(
            current_user, user_id,
            **data
        )
    )


@app.route(
    '/users/<int:user_id>/permissions/<int:permission_id>',
    methods=['GET']
)
@log_user_action
@login_required
def show_user_permission(user_id, permission_id):
    """Get a specific user permission."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        user_api.get_permission(
            current_user, user_id, permission_id,
            **data
        )
    )


@app.route("/users/<int:user_id>/permissions", methods=['POST'])
@log_user_action
@login_required
def add_user_permission(user_id):
    """Delete a specific user permission."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        user_api.add_permission(
            current_user, user_id,
            **data
        )
    )


@app.route(
    '/users/<int:user_id>/permissions/<int:permission_id>',
    methods=['DELETE']
)
@log_user_action
@login_required
def delete_user_permission(user_id, permission_id):
    """Delete a specific user permission."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        user_api.del_permission(
            current_user, user_id, permission_id,
            **data
        )
    )


@app.route("/permissions", methods=['GET'])
@log_user_action
@login_required
def list_permissions():
    """List permissions."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        permission_api.list_permissions(current_user, **data)
    )


@app.route("/permissions/<int:permission_id>", methods=['GET'])
@log_user_action
@login_required
def show_permission(permission_id):
    """Get permission."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        permission_api.get_permission(current_user, permission_id, **data)
    )


def _filter_timestamp(data):
    timestamp_filter = {}
    start = _get_data(data, 'timestamp_start')
    if start is not None:
        timestamp_filter['ge'] = util.parse_datetime(
            start, exception_handler.BadRequest
        )
    end = _get_data(data, 'timestamp_end')
    if end is not None:
        timestamp_filter['le'] = util.parse_datetime(
            end, exception_handler.BadRequest)
    range = _get_data_list(data, 'timestamp_range')
    if range:
        timestamp_filter['between'] = []
        for value in range:
            timestamp_filter['between'].append(
                util.parse_datetime_range(
                    value, exception_handler.BadRequest
                )
            )
    data['timestamp'] = timestamp_filter
    _clean_data(
        data,
        [
            'timestamp_start', 'timestamp_end',
            'timestamp_range'
        ]
    )


@app.route("/users/logs", methods=['GET'])
@log_user_action
@login_required
def list_all_user_actions():
    """List all users actions."""
    data = _get_request_args()
    _filter_timestamp(data)
    return utils.make_json_response(
        200,
        user_log_api.list_actions(
            current_user, **data
        )
    )


@app.route("/users/<int:user_id>/logs", methods=['GET'])
@log_user_action
@login_required
def list_user_actions(user_id):
    """List user actions."""
    data = _get_request_args()
    _filter_timestamp(data)
    return utils.make_json_response(
        200,
        user_log_api.list_user_actions(
            current_user, user_id, **data
        )
    )


@app.route("/users/logs", methods=['DELETE'])
@log_user_action
@login_required
def delete_all_user_actions():
    """Delete all user actions."""
    data = _get_request_data()
    _filter_timestamp(data)
    return utils.make_json_response(
        200,
        user_log_api.del_actions(
            current_user, **data
        )
    )


@app.route("/users/<int:user_id>/logs", methods=['DELETE'])
@log_user_action
@login_required
def delete_user_actions(user_id):
    """Delete user actions."""
    data = _get_request_data()
    _filter_timestamp(data)
    return utils.make_json_response(
        200,
        user_log_api.del_user_actions(
            current_user, user_id, **data
        )
    )


def _filter_ip(data):
    ip_filter = {}
    switch_ips = _get_data_list(data, 'switchIp')
    if switch_ips:
        ip_filter['eq'] = []
        for switch_ip in switch_ips:
            ip_filter['eq'].append(long(netaddr.IPAddress(switch_ip)))
    switch_start = _get_data(data, 'switchIpStart')
    if switch_start is not None:
        ip_filter['ge'] = long(netaddr.IPAddress(switch_start))
    switch_end = _get_data(data, 'switchIpEnd')
    if switch_end is not None:
        ip_filter['lt'] = long(netaddr.IPAddress(switch_end))
    switch_nets = _get_data_list(data, 'switchIpNetwork')
    if switch_nets:
        ip_filter['between'] = []
        for switch_net in switch_nets:
            network = netaddr.IPNetwork(switch_net)
            ip_filter['between'].append((network.first, network.last))
    switch_ranges = _get_data_list(data, 'switchIpRange')
    if switch_ranges:
        ip_filter.setdefault('between', [])
        for switch_range in switch_ranges:
            ip_start, ip_end = switch_range.split(',')
            ip_filter['between'].append(
                long(netaddr.IPAddress(ip_start)),
                long(netaddr.IPAddress(ip_end))
            )
    if ip_filter:
        data['ip_int'] = ip_filter
    _clean_data(
        data,
        [
            'switchIp', 'switchIpStart', 'switchIpEnd',
            'switchIpNetwork', 'switchIpRange'
        ]
    )


@app.route("/switches", methods=['GET'])
@log_user_action
@login_required
def list_switches():
    """List switches."""
    data = _get_request_args()
    _filter_ip(data)
    return utils.make_json_response(
        200,
        switch_api.list_switches(
            current_user, **data
        )
    )


@app.route("/switches/<int:switch_id>", methods=['GET'])
@log_user_action
@login_required
def show_switch(switch_id):
    """Get switch."""
    data = _get_request_args()
    return utils.make_json_response(
        200, switch_api.get_switch(current_user, switch_id, **data)
    )


@app.route("/switches", methods=['POST'])
@log_user_action
@login_required
def add_switch():
    """add switch."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        switch_api.add_switch(current_user, **data)
    )


@app.route("/switches/<int:switch_id>", methods=['PUT'])
@log_user_action
@login_required
def update_switch(switch_id):
    """update switch."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        switch_api.update_switch(current_user, switch_id, **data)
    )


@app.route("/switches/<int:switch_id>", methods=['PATCH'])
@log_user_action
@login_required
def patch_switch(switch_id):
    """patch switch."""
    data = _get_request_data()
    _replace_data(data, {'credentials': 'patched_credentials'})
    return utils.make_json_response(
        200,
        switch_api.patch_switch(current_user, switch_id, **data)
    )


@app.route("/switches/<int:switch_id>", methods=['DELETE'])
@log_user_action
@login_required
def delete_switch(switch_id):
    """delete switch."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        switch_api.del_switch(current_user, switch_id, **data)
    )


@app.route("/switch-filters", methods=['GET'])
@log_user_action
@login_required
def list_switch_filters():
    """List switch filters."""
    data = _get_request_args()
    _filter_ip(data)
    return utils.make_json_response(
        200,
        switch_api.list_switch_filters(
            current_user, **data
        )
    )


@app.route("/switch-filters/<int:switch_id>", methods=['GET'])
@log_user_action
@login_required
def show_switch_filters(switch_id):
    """Get switch filters."""
    data = _get_request_args()
    return utils.make_json_response(
        200, switch_api.get_switch_filters(current_user, switch_id, **data)
    )


@app.route("/switch-filters/<int:switch_id>", methods=['PUT'])
@log_user_action
@login_required
def update_switch_filters(switch_id):
    """update switch filters."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        switch_api.update_switch_filters(current_user, switch_id, **data)
    )


@app.route("/switch-filters/<int:switch_id>", methods=['PATCH'])
@log_user_action
@login_required
def patch_switch_filters(switch_id):
    """patch switch filters."""
    data = _get_request_data()
    _replace_data(data, {'filters': 'patched_filters'})
    return utils.make_json_response(
        200,
        switch_api.patch_switch_filter(current_user, switch_id, **data)
    )


def _filter_port(data):
    port_filter = {}
    ports = _get_data_list(data, 'port')
    if ports:
        port_filter['eq'] = ports
    port_start = _get_data(data, 'portStart')
    if port_start is not None:
        port_filter['resp_ge'] = int(port_start)
    port_end = _get_data(data, 'portEnd')
    if port_end is not None:
        port_filter['resp_lt'] = int(port_end)
    port_ranges = _get_data_list(data, 'portRange')
    if port_ranges:
        port_filter['resp_range'] = []
        for port_range in port_ranges:
            port_start, port_end = port_range.split(',')
            port_filter['resp_range'].append(
                (int(port_start), int(port_end))
            )
    port_prefix = _get_data(data, 'portPrefix')
    if port_prefix:
        port_filter['startswith'] = port_prefix
    port_suffix = _get_data(data, 'portSuffix')
    if port_suffix:
        port_filter['endswith'] = port_suffix
    if port_filter:
        data['port'] = port_filter
    _clean_data(
        data,
        [
            'portStart', 'portEnd', 'portRange',
            'portPrefix', 'portSuffix'
        ]
    )


def _filter_vlans(data):
    vlan_filter = {}
    vlans = _get_data_list(data, 'vlans')
    if vlans:
        vlan_filter['resp_in'] = vlans
        data['vlans'] = vlan_filter


def _filter_tag(data):
    tag_filter = {}
    tags = _get_data_list(data, 'tag')
    if tags:
        tag_filter['resp_in'] = []
        for tag in tags:
            tag_filter['resp_in'].append(
                util.parse_request_arg_dict(tag)
            )
        data['tag'] = tag_filter


def _filter_location(data):
    location_filter = {}
    locations = _get_data_list(data, 'location')
    if locations:
        location_filter['resp_in'] = []
        for location in locations:
            location_filter['resp_in'].append(
                util.parse_request_arg_dict(location)
            )
        data['location'] = location_filter


@app.route("/switches/<int:switch_id>/machines", methods=['GET'])
@log_user_action
@login_required
def list_switch_machines(switch_id):
    """Get switch machines."""
    data = _get_request_args()
    _filter_port(data)
    _filter_vlans(data)
    _filter_tag(data)
    _filter_location(data)
    return utils.make_json_response(
        200,
        switch_api.list_switch_machines(
            current_user, switch_id, **data
        )
    )


@app.route("/switches/<int:switch_id>/machines", methods=['POST'])
@log_user_action
@login_required
def add_switch_machine(switch_id):
    """add switch machine."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        switch_api.add_switch_machine(current_user, switch_id, **data)
    )


@app.route(
    '/switches/<int:switch_id>/machines/<int:machine_id>',
    methods=['GET']
)
@log_user_action
@login_required
def show_switch_machine(switch_id, machine_id):
    """get switch machine."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        switch_api.get_switch_machine(
            current_user, switch_id, machine_id, **data
        )
    )


@app.route(
    '/switches/<int:switch_id>/machines/actions',
    methods=['POST']
)
@log_user_action
@login_required
def update_switch_machines(switch_id):
    """update switch machine."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        switch_api.update_switch_machines(
            current_user, switch_id, **data
        )
    )


@app.route(
    '/switches/<int:switch_id>/machines/<int:machine_id>',
    methods=['PUT']
)
@log_user_action
@login_required
def update_switch_machine(switch_id, machine_id):
    """update switch machine."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        switch_api.update_switch_machine(
            current_user, switch_id, machine_id, **data
        )
    )


@app.route(
    '/switches/<int:switch_id>/machines/<int:machine_id>',
    methods=['PATCH']
)
@log_user_action
@login_required
def patch_switch_machine(switch_id, machine_id):
    """patch switch machine."""
    data = _get_request_data()
    _replace_data(
        data,
        {
            'vlans': 'patched_vlans',
            'ipmi_credentials': 'patched_ipmi_credentials',
            'tag': 'patched_tag',
            'location': 'patched_location'
        }
    )
    return utils.make_json_response(
        200,
        switch_api.patch_switch_machine(
            current_user, switch_id, machine_id, **data
        )
    )


@app.route(
    '/switches/<int:switch_id>/machines/<int:machine_id>',
    methods=['DELETE']
)
@log_user_action
@login_required
def delete_switch_machine(switch_id, machine_id):
    """Delete switch machine."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        switch_api.del_switch_machine(
            current_user, switch_id, machine_id, **data
        )
    )


@app.route("/switches/<int:switch_id>/actions", methods=['POST'])
@log_user_action
@login_required
def take_switch_action(switch_id):
    """update switch."""
    data = _get_request_data()
    if 'find_machines' in data:
        return utils.make_json_response(
            202,
            switch_api.poll_switch_machines(
                current_user, switch_id, **data['find_machines']
            )
        )
    else:
        return utils.make_json_response(
            200,
            {
                'status': 'unknown action',
                'details': 'supported actions: %s' % str(['find_machines'])
            }
        )


@app.route("/switch-machines", methods=['GET'])
@log_user_action
@login_required
def list_switchmachines():
    """List switch machines."""
    data = _get_request_args()
    _filter_ip(data)
    _filter_port(data)
    _filter_vlans(data)
    _filter_tag(data)
    _filter_location(data)
    return utils.make_json_response(
        200,
        switch_api.list_switchmachines(
            current_user, **data
        )
    )


@app.route(
    '/switch-machines/<int:switch_machine_id>',
    methods=['GET']
)
@log_user_action
@login_required
def show_switchmachine(switch_machine_id):
    """get switch machine."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        switch_api.get_switchmachine(
            current_user, switch_machine_id, **data
        )
    )


@app.route(
    '/switch-machines/<int:switch_machine_id>',
    methods=['PUT']
)
@log_user_action
@login_required
def update_switchmachine(switch_machine_id):
    """update switch machine."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        switch_api.update_switchmachine(
            current_user, switch_machine_id, **data
        )
    )


@app.route('/switch-machines/<int:switch_machine_id>', methods=['PATCH'])
@log_user_action
@login_required
def patch_switchmachine(switch_machine_id):
    """patch switch machine."""
    data = _get_request_data()
    _replace_data(
        data,
        {
            'vlans': 'patched_vlans',
            'ipmi_credentials': 'patched_ipmi_credentials',
            'tag': 'patched_tag',
            'location': 'patched_location'
        }
    )
    return utils.make_json_response(
        200,
        switch_api.patch_switchmachine(
            current_user, switch_machine_id, **data
        )
    )


@app.route("/switch-machines/<int:switch_machine_id>", methods=['DELETE'])
@log_user_action
@login_required
def delete_switchmachine(switch_machine_id):
    """Delete switch machine."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        switch_api.del_switchmachine(
            current_user, switch_machine_id, **data
        )
    )


@app.route("/machines", methods=['GET'])
@log_user_action
@login_required
def list_machines():
    """List machines."""
    data = _get_request_args()
    _filter_tag(data)
    _filter_location(data)
    return utils.make_json_response(
        200,
        machine_api.list_machines(
            current_user, **data
        )
    )


@app.route("/machines/<int:machine_id>", methods=['GET'])
@log_user_action
@login_required
def show_machine(machine_id):
    """Get machine."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        machine_api.get_machine(
            current_user, machine_id, **data
        )
    )


@app.route("/machines/<int:machine_id>", methods=['PUT'])
@log_user_action
@login_required
def update_machine(machine_id):
    """update machine."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        machine_api.update_machine(
            current_user, machine_id, **data
        )
    )


@app.route("/machines/<int:machine_id>", methods=['PATCH'])
@log_user_action
@login_required
def patch_machine(machine_id):
    """patch machine."""
    data = _get_request_data()
    _replace_data(
        data,
        {
            'ipmi_credentials': 'patched_ipmi_credentials',
            'tag': 'patched_tag',
            'location': 'patched_location'
        }
    )
    return utils.make_json_response(
        200,
        machine_api.patch_machine(
            current_user, machine_id, **data
        )
    )


@app.route("/machines/<int:machine_id>", methods=['DELETE'])
@log_user_action
@login_required
def delete_machine(machine_id):
    """Delete machine."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        machine_api.del_machine(
            current_user, machine_id, **data
        )
    )


@app.route("/networks", methods=['GET'])
@log_user_action
@login_required
def list_subnets():
    """List subnets."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        network_api.list_subnets(
            current_user, **data
        )
    )


@app.route("/networks/<int:subnet_id>", methods=['GET'])
@log_user_action
@login_required
def show_subnet(subnet_id):
    """Get subnet."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        network_api.get_subnet(
            current_user, subnet_id, **data
        )
    )


@app.route("/networks", methods=['POST'])
@log_user_action
@login_required
def add_subnet():
    """add subnet."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        network_api.add_subnet(current_user, **data)
    )


@app.route("/networks/<int:subnet_id>", methods=['PUT'])
@log_user_action
@login_required
def update_subnet(subnet_id):
    """update subnet."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        network_api.update_subnet(
            current_user, subnet_id, **data
        )
    )


@app.route("/networks/<int:subnet_id>", methods=['DELETE'])
@log_user_action
@login_required
def delete_subnet(subnet_id):
    """Delete subnet."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        network_api.del_subnet(
            current_user, subnet_id, **data
        )
    )


@app.route("/adapters", methods=['GET'])
@log_user_action
@login_required
def list_adapters():
    """List adapters."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        adapter_api.list_adapters(
            current_user, **data
        )
    )


@app.route("/adapters/<int:adapter_id>", methods=['GET'])
@log_user_action
@login_required
def show_adapter(adapter_id):
    """Get adapter."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        adapter_api.get_adapter(
            current_user, adapter_id, **data
        )
    )


@app.route("/adapters/<int:adapter_id>/roles", methods=['GET'])
@log_user_action
@login_required
def show_adapter_roles(adapter_id):
    """Get adapter roles."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        adapter_api.get_adapter_roles(
            current_user, adapter_id, **data
        )
    )


@app.route("/adapters/<int:adapter_id>/metadata", methods=['GET'])
@log_user_action
@login_required
def show_metadata(adapter_id):
    """Get adapter metadata."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        metadata_api.get_metadata(
            current_user, adapter_id, **data
        )
    )


@app.route("/clusters", methods=['GET'])
@log_user_action
@login_required
def list_clusters():
    """List clusters."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        cluster_api.list_clusters(
            current_user, **data
        )
    )


@app.route("/clusters/<int:cluster_id>", methods=['GET'])
@log_user_action
@login_required
def show_cluster(cluster_id):
    """Get cluster."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        cluster_api.get_cluster(
            current_user, cluster_id, **data
        )
    )


@app.route("/clusters", methods=['POST'])
@log_user_action
@login_required
def add_cluster():
    """add cluster."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.add_cluster(current_user, **data)
    )


@app.route("/clusters/<int:cluster_id>", methods=['PUT'])
@log_user_action
@login_required
def update_cluster(cluster_id):
    """update cluster."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.update_cluster(
            current_user, cluster_id, **data
        )
    )


@app.route("/clusters/<int:cluster_id>", methods=['DELETE'])
@log_user_action
@login_required
def delete_cluster(cluster_id):
    """Delete cluster."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.del_cluster(
            current_user, cluster_id, **data
        )
    )


@app.route("/clusters/<int:cluster_id>/config", methods=['GET'])
@log_user_action
@login_required
def show_cluster_config(cluster_id):
    """Get cluster config."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        cluster_api.get_cluster_config(
            current_user, cluster_id, **data
        )
    )


@app.route("/clusters/<int:cluster_id>/config", methods=['PUT'])
@log_user_action
@login_required
def update_cluster_config(cluster_id):
    """update cluster config."""
    data = _get_request_data()
    _replace_data(
        data,
        {
            'os_config': 'put_os_config',
            'package_config': 'put_os_config'
        }
    )
    return utils.make_json_response(
        200,
        cluster_api.update_cluster_config(current_user, cluster_id, **data)
    )


@app.route("/clusters/<int:cluster_id>", methods=['PATCH'])
@log_user_action
@login_required
def patch_cluster_config(cluster_id):
    """patch cluster config."""
    data = _get_request_data()
    _replace_data(
        data,
        {
            'os_config': 'patched_os_config',
            'package_config': 'patched_package_config'
        }
    )
    return utils.make_json_response(
        200,
        cluster_api.patch_cluster_config(current_user, cluster_id, **data)
    )


@app.route("/clusters/<int:cluster_id>/config", methods=['DELETE'])
@log_user_action
@login_required
def delete_cluster_config(cluster_id):
    """Delete cluster config."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.del_cluster_config(
            current_user, cluster_id, **data
        )
    )


@app.route("/clusters/<int:cluster_id>/config", methods=['POST'])
@log_user_action
@login_required
def update_cluster_hosts(cluster_id):
    """update cluster hosts."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.update_clusterhosts(current_user, cluster_id, **data)
    )


@app.route("/clusters/<int:cluster_id>/review", methods=['POST'])
@log_user_action
@login_required
def review_cluster(cluster_id):
    """review cluster"""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.review_cluster(current_user, cluster_id, **data)
    )


@app.route("/clusters/<int:cluster_id>/action", methods=['POST'])
@log_user_action
@login_required
def take_cluster_action(cluster_id):
    """take cluster action."""
    data = _get_request_data()
    if 'deploy' in data:
        return utils.make_json_response(
            202,
            cluster_api.deploy_cluster(
                current_user, cluster_id, **data['deploy']
            )
        )
    return utils.make_json_response(
        200,
        {
            'status': 'unknown action',
            'details': 'supported actions: %s' % str(['deploy'])
        }
    )


@app.route("/clusters/<int:cluster_id>/state", methods=['GET'])
@log_user_action
@login_required
def get_cluster_state(cluster_id):
    """Get cluster state."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        cluster_api.get_cluster_state(
            current_user, cluster_id, **data
        )
    )


@app.route("/clusters/<int:cluster_id>/hosts", methods=['GET'])
@log_user_action
@login_required
def list_cluster_hosts(cluster_id):
    """Get cluster hosts."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        cluster_api.list_cluster_hosts(
            current_user, cluster_id, **data
        )
    )


@app.route("/clusterhosts", methods=['GET'])
@log_user_action
@login_required
def list_clusterhosts():
    """Get cluster hosts."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        cluster_api.list_clusterhosts(
            current_user, **data
        )
    )


@app.route("/clusters/<int:cluster_id>/hosts/<int:host_id>", methods=['GET'])
@log_user_action
@login_required
def show_cluster_host(cluster_id, host_id):
    """Get clusterhost."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        cluster_api.get_cluster_host(
            current_user, cluster_id, host_id, **data
        )
    )


@app.route("/clusterhosts/<int:clusterhost_id>", methods=['GET'])
@log_user_action
@login_required
def show_clusterhost(clusterhost_id):
    """Get clusterhost."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        cluster_api.get_clusterhost(
            current_user, clusterhost_id, **data
        )
    )


@app.route(
    "/clusters/<int:cluster_id>/hosts/<int:host_id>/config",
    methods=['GET']
)
@log_user_action
@login_required
def show_cluster_host_config(cluster_id, host_id):
    """Get clusterhost config."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        cluster_api.get_cluster_host_config(
            current_user, cluster_id, host_id, **data
        )
    )


@app.route("/clusterhosts/<int:clusterhost_id>/config", methods=['GET'])
@log_user_action
@login_required
def show_clusterhost_config(clusterhost_id):
    """Get clusterhost config."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        cluster_api.get_clusterhost_config(
            current_user, clusterhost_id, **data
        )
    )


@app.route(
    "/clusters/<int:cluster_id>/hosts/<int:host_id>/config",
    methods=['PUT']
)
@log_user_action
@login_required
def update_cluster_host_config(cluster_id, host_id):
    """update clusterhost config."""
    data = _get_request_data()
    _replace_data(
        data,
        {
            'package_config': 'put_os_config'
        }
    )
    return utils.make_json_response(
        200,
        cluster_api.update_cluster_host_config(
            current_user, cluster_id, host_id, **data
        )
    )


@app.route("/clusterhosts/<int:clusterhost_id>/config", methods=['PUT'])
@log_user_action
@login_required
def update_clusterhost_config(clusterhost_id):
    """update clusterhost config."""
    data = _get_request_data()
    _replace_data(
        data,
        {
            'package_config': 'put_os_config'
        }
    )
    return utils.make_json_response(
        200,
        cluster_api.update_clusterhost_config(
            current_user, clusterhost_id, **data
        )
    )


@app.route(
    "/clusters/<int:cluster_id>/hosts/<int:host_id>/config",
    methods=['PATCH']
)
@log_user_action
@login_required
def patch_cluster_host_config(cluster_id, host_id):
    """patch clusterhost config."""
    data = _get_request_data()
    _replace_data(
        data,
        {
            'package_config': 'patched_package_config'
        }
    )
    return utils.make_json_response(
        200,
        cluster_api.patch_cluster_host_config(
            current_user, cluster_id, host_id, **data
        )
    )


@app.route("/clusterhosts/<int:clusterhost_id>", methods=['PATCH'])
@log_user_action
@login_required
def patch_clusterhost_config(clusterhost_id):
    """patch clusterhost config."""
    data = _get_request_data()
    _replace_data(
        data,
        {
            'package_config': 'patched_package_config'
        }
    )
    return utils.make_json_response(
        200,
        cluster_api.patch_clusterhost_config(
            current_user, clusterhost_id, **data
        )
    )


@app.route(
    "/clusters/<int:cluster_id>/hosts/<int:host_id>/config",
    methods=['DELETE']
)
@log_user_action
@login_required
def delete_cluster_host_config(cluster_id, host_id):
    """Delete clusterhost config."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.del_clusterhost_config(
            current_user, cluster_id, host_id, **data
        )
    )


@app.route("/clusterhosts/<int:clusterhost_id>/config", methods=['DELETE'])
@log_user_action
@login_required
def delete_clusterhost_config(clusterhost_id):
    """Delete clusterhost config."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.del_clusterhost_config(
            current_user, clusterhost_id, **data
        )
    )


@app.route(
    "/clusters/<int:cluster_id>/hosts/<int:host_id>/state",
    methods=['GET']
)
@log_user_action
@login_required
def show_cluster_host_state(cluster_id, host_id):
    """Get clusterhost state."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        cluster_api.get_cluster_host_state(
            current_user, cluster_id, host_id, **data
        )
    )


@app.route("/clusterhosts/<int:clusterhost_id>/state", methods=['GET'])
@log_user_action
@login_required
def show_clusterhost_state(clusterhost_id):
    """Get clusterhost state."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        cluster_api.get_clusterhost_state(
            current_user, clusterhost_id, **data
        )
    )


@app.route(
    "/clusters/<int:cluster_id>/hosts/<int:host_id>/state",
    methods=['PUT']
)
@log_user_action
@login_required
def update_cluster_host_state(cluster_id, host_id):
    """update clusterhost state."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.update_clusterhost_state(
            current_user, cluster_id, host_id, **data
        )
    )


@app.route("/clusterhosts/<int:clusterhost_id>/state", methods=['PUT'])
@log_user_action
@login_required
def update_clusterhost_state(clusterhost_id):
    """update clusterhost state."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.update_clusterhost_state(
            current_user, clusterhost_id, **data
        )
    )


@app.route("/hosts", methods=['GET'])
@log_user_action
@login_required
def list_hosts():
    """List hosts."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        host_api.list_hosts(
            current_user, **data
        )
    )


@app.route("/hosts/<int:host_id>", methods=['GET'])
@log_user_action
@login_required
def show_host(host_id):
    """Get host."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        host_api.get_host(
            current_user, host_id, **data
        )
    )


@app.route("/hosts/<int:host_id>", methods=['PUT'])
@log_user_action
@login_required
def update_host(host_id):
    """update host."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        host_api.update_host(
            current_user, host_id, **data
        )
    )


@app.route("/hosts/<int:host_id>", methods=['DELETE'])
@log_user_action
@login_required
def delete_host(host_id):
    """Delete host."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        host_api.del_host(
            current_user, host_id, **data
        )
    )


@app.route("/hosts/<int:host_id>/clusters", methods=['GET'])
@log_user_action
@login_required
def get_host_clusters(host_id):
    """Get host clusters."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        host_api.get_host_clusters(
            current_user, host_id, **data
        )
    )


@app.route("/hosts/<int:host_id>/config", methods=['GET'])
@log_user_action
@login_required
def show_host_config(host_id):
    """Get host config."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        host_api.get_host_config(
            current_user, host_id, **data
        )
    )


@app.route("/hosts/<int:host_id>/config", methods=['PUT'])
@log_user_action
@login_required
def update_host_config(host_id):
    """update host config."""
    data = _get_request_data()
    _replace_data(
        data,
        {
            'os_config': 'put_os_config',
        }
    )
    return utils.make_json_response(
        200,
        host_api.update_cluster_config(current_user, host_id, **data)
    )


@app.route("/hosts/<int:host_id>", methods=['PATCH'])
@log_user_action
@login_required
def patch_host_config(host_id):
    """patch host config."""
    data = _get_request_data()
    _replace_data(
        data,
        {
            'os_config': 'patched_os_config',
        }
    )
    return utils.make_json_response(
        200,
        host_api.patch_host_config(current_user, host_id, **data)
    )


@app.route("/hosts/<int:host_id>/config", methods=['DELETE'])
@log_user_action
@login_required
def delete_host_config(host_id):
    """Delete host config."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        host_api.del_host_config(
            current_user, host_id, **data
        )
    )


@app.route("/hosts/<int:host_id>/networks", methods=['GET'])
@log_user_action
@login_required
def list_host_networks(host_id):
    """list host networks."""
    data = _get_request_args()
    return utils.make_json_response(
        200, host_api.list_host_networks(current_user, host_id, **data)
    )


@app.route("/hosts/<int:host_id>/networks", methods=['POST'])
@log_user_action
@login_required
def add_host_network(host_id):
    """add host network."""
    data = _get_request_data()
    return utils.make_json_response(
        200, host_api.add_host_network(current_user, host_id, **data)
    )


@app.route("/host-networks/<int:host_network_id>", methods=['PUT'])
@log_user_action
@login_required
def update_host_network(host_network_id):
    """update host network."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        host_api.update_host_network(
            current_user, host_network_id, **data
        )
    )


@app.route("/host-networks/<int:host_network_id>", methods=['DELETE'])
@log_user_action
@login_required
def delete_host_network(host_network_id):
    """Delete host network."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        host_api.del_host_network(
            current_user, host_network_id, **data
        )
    )


@app.route("/hosts/<int:host_id>/state", methods=['GET'])
@log_user_action
@login_required
def show_host_state(host_id):
    """Get host state."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        host_api.get_host_state(
            current_user, host_id, **data
        )
    )


@app.route("/hosts/<int:host_id>/state", methods=['PUT'])
@log_user_action
@login_required
def update_host_state(host_id):
    """update host state."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        host_api.update_host_state(
            current_user, host_id, **data
        )
    )


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    app.run(host='0.0.0.0')
