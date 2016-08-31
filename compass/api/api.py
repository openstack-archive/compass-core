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
import logging
import netaddr
import requests
import simplejson as json

from flask.ext.login import current_user
from flask.ext.login import login_required
from flask.ext.login import login_user
from flask.ext.login import logout_user
from flask import request

from compass.api import app
from compass.api import auth_handler
from compass.api import exception_handler
from compass.api import utils
from compass.db.api import adapter_holder as adapter_api
from compass.db.api import cluster as cluster_api
from compass.db.api import database
from compass.db.api import health_check_report as health_report_api
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
from compass.utils import setting_wrapper as setting
from compass.utils import util


def log_user_action(func):
    """decorator used to log api request url."""
    @functools.wraps(func)
    def decorated_api(*args, **kwargs):
        # TODO(xicheng): save request args for GET
        # and request data for POST/PUT.
        user_log_api.log_user_action(current_user.id, request.path)
        return func(*args, **kwargs)
    return decorated_api


def update_user_token(func):
    """decorator used to update user token expire time after api request."""
    @functools.wraps(func)
    def decorated_api(*args, **kwargs):
        response = func(*args, **kwargs)
        expire_timestamp = (
            datetime.datetime.now() + app.config['REMEMBER_COOKIE_DURATION']
        )
        user_api.record_user_token(
            current_user.token, expire_timestamp, user=current_user
        )
        return response
    return decorated_api


def _clean_data(data, keys):
    """remove keys from dict."""
    for key in keys:
        if key in data:
            del data[key]


def _replace_data(data, key_mapping):
    """replace key names in dict."""
    for key, replaced_key in key_mapping.items():
        if key in data:
            data[replaced_key] = data[key]
            del data[key]


def _get_data(data, key):
    """get key's value from request arg dict.

    When the value is list, return the element in the list
    if the list size is one. If the list size is greater than one,
    raise exception_handler.BadRequest.

    Example: data = {'a': ['b'], 'b': 5, 'c': ['d', 'e'], 'd': []}
             _get_data(data, 'a') == 'b'
             _get_data(data, 'b') == 5
             _get_data(data, 'c') raises exception_handler.BadRequest
             _get_data(data, 'd') == None
             _get_data(data, 'e') == None

    Usage: Used to parse the key-value pair in request.args to expected types.
           Depends on the different flask plugins and what kind of parameters
           passed in, the request.args format may be as below:
           {'a': 'b'} or {'a': ['b']}. _get_data forces translate the
           request.args to the format {'a': 'b'}. It raises exception when some
           parameter declares multiple times.
    """
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
    """get key's value as list from request arg dict.

    If the value type is list, return it, otherwise return the list
    whos only element is the value got from the dict.

    Example: data = {'a': ['b'], 'b': 5, 'c': ['d', 'e'], 'd': []}
             _get_data_list(data, 'a') == ['b']
             _get_data_list(data, 'b') == [5]
             _get_data_list(data, 'd') == []
             _get_data_list(data, 'e') == []

    Usage: Used to parse the key-value pair in request.args to expected types.
           Depends on the different flask plugins and what kind of parameters
           passed in, the request.args format may be as below:
           {'a': 'b'} or {'a': ['b']}. _get_data_list forces translate the
           request.args to the format {'a': ['b']}. It accepts the case that
           some parameter declares multiple times.
    """
    if key in data:
        if isinstance(data[key], list):
            return data[key]
        else:
            return [data[key]]
    else:
        return []


def _get_request_data():
    """Convert reqeust data from string to python dict.

    If the request data is not json formatted, raises
    exception_handler.BadRequest.
    If the request data is not json formatted dict, raises
    exception_handler.BadRequest
    If the request data is empty, return default as empty dict.

    Usage: It is used to add or update a single resource.
    """
    if request.data:
        try:
            data = json.loads(request.data)
        except Exception:
            raise exception_handler.BadRequest(
                'request data is not json formatted: %s' % request.data
            )
        if not isinstance(data, dict):
            raise exception_handler.BadRequest(
                'request data is not json formatted dict: %s' % request.data
            )
        return data
    else:
        return {}


def _get_request_data_as_list():
    """Convert reqeust data from string to python list.

    If the request data is not json formatted, raises
    exception_handler.BadRequest.
    If the request data is not json formatted list, raises
    exception_handler.BadRequest.
    If the request data is empty, return default as empty list.

    Usage: It is used to batch add or update a list of resources.
    """
    if request.data:
        try:
            data = json.loads(request.data)
        except Exception:
            raise exception_handler.BadRequest(
                'request data is not json formatted: %s' % request.data
            )
        if not isinstance(data, list):
            raise exception_handler.BadRequest(
                'request data is not json formatted list: %s' % request.data
            )
        return data
    else:
        return []


def _bool_converter(value):
    """Convert string value to bool.

    This function is used to convert value in requeset args to expected type.
    If the key exists in request args but the value is not set, it means the
    value should be true.

    Examples:
       /<request_path>?is_admin parsed to {'is_admin', None} and it should
       be converted to {'is_admin': True}.
       /<request_path>?is_admin=0 parsed and converted to {'is_admin': False}.
       /<request_path>?is_admin=1 parsed and converted to {'is_admin': True}.
    """
    if not value:
        return True
    if value in ['False', 'false', '0']:
        return False
    if value in ['True', 'true', '1']:
        return True
    raise exception_handler.BadRequest(
        '%r type is not bool' % value
    )


def _int_converter(value):
    """Convert string value to int.

    We do not use the int converter default exception since we want to make
    sure the exact http response code.

    Raises: exception_handler.BadRequest if value can not be parsed to int.

    Examples:
       /<request_path>?count=10 parsed to {'count': '10'} and it should be
       converted to {'count': 10}.
    """
    try:
        return int(value)
    except Exception:
        raise exception_handler.BadRequest(
            '%r type is not int' % value
        )


def _get_request_args(**kwargs):
    """Get request args as dict.

    The value in the dict is converted to expected type.

    Args:
       kwargs: for each key, the value is the type converter.
    """
    args = dict(request.args)
    logging.log(
        logsetting.getLevelByName('fine'),
        'origin request args: %s', args
    )
    for key, value in args.items():
        if key in kwargs:
            converter = kwargs[key]
            if isinstance(value, list):
                args[key] = [converter(item) for item in value]
            else:
                args[key] = converter(value)
    logging.log(
        logsetting.getLevelByName('fine'),
        'request args: %s', args
    )
    return args


def _group_data_action(data, **data_callbacks):
    """Group api actions and pass data to grouped action callback.

    Example:
       data = {
          'add_hosts': [{'name': 'a'}, {'name': 'b'}],
          'update_hosts': {'c': {'mac': '123'}},
          'remove_hosts': ['d', 'e']
       }
       data_callbacks = {
           'add_hosts': update_cluster_action,
           'update_hosts': update_cluster_action,
           'remove_hosts': update_cluster_action
       }
       it converts to update_cluster_action(
           add_hosts=[{'name': 'a'}, {'name': 'b'}],
           update_hosts={'c': {'mac': '123'}},
           remove_hosts=['d', 'e']
       )

    Raises:
       exception_handler.BadRequest if data is empty.
       exception_handler.BadMethod if there are some keys in data but
       not in data_callbacks.
       exception_handler.BadRequest if it groups to multiple
       callbacks.
    """
    if not data:
        raise exception_handler.BadRequest(
            'no action to take'
        )
    unsupported_keys = list(set(data) - set(data_callbacks))
    if unsupported_keys:
        raise exception_handler.BadMethod(
            'unsupported actions: %s' % unsupported_keys
        )
    callback_datas = {}
    for data_key, data_value in data.items():
        callback = data_callbacks[data_key]
        callback_datas.setdefault(id(callback), {})[data_key] = data_value
    if len(callback_datas) > 1:
        raise exception_handler.BadRequest(
            'multi actions are not supported'
        )
    callback_ids = {}
    for data_key, data_callback in data_callbacks.items():
        callback_ids[id(data_callback)] = data_callback
    for callback_id, callback_data in callback_datas.items():
        return callback_ids[callback_id](**callback_data)


def _wrap_response(func, response_code):
    """wrap function response to json formatted http response."""
    def wrapped_func(*args, **kwargs):
        return utils.make_json_response(
            response_code,
            func(*args, **kwargs)
        )
    return wrapped_func


def _reformat_host_networks(networks):
    """Reformat networks from list to dict.

    The key in the dict is the value of the key 'interface'
    in each network.

    Example: networks = [{'interface': 'eth0', 'ip': '10.1.1.1'}]
             is reformatted to {
                 'eth0': {'interface': 'eth0', 'ip': '10.1.1.1'}
             }

    Usage: The networks got from db api is a list of network,
           For better parsing in json frontend, we converted the
           format into dict to easy reference.
    """
    network_mapping = {}
    for network in networks:
        if 'interface' in network:
            network_mapping[network['interface']] = network
    return network_mapping


def _reformat_host(host):
    """Reformat host's networks."""
    if isinstance(host, list):
        return [_reformat_host(item) for item in host]
    if 'networks' in host:
        host['networks'] = _reformat_host_networks(host['networks'])
    return host


def _login(use_cookie):
    """User login helper function.

    The request data should contain at least 'email' and 'password'.
    The cookie expiration duration is defined in flask app config.
    If user is not authenticated, it raises Unauthorized exception.
    """
    data = _get_request_data()
    if 'email' not in data or 'password' not in data:
        raise exception_handler.BadRequest(
            'missing email or password in data'
        )
    expire_timestamp = (
        datetime.datetime.now() + app.config['REMEMBER_COOKIE_DURATION']
    )
    data['expire_timestamp'] = expire_timestamp
    user = auth_handler.authenticate_user(**data)
    if not user.active:
        raise exception_handler.UserDisabled(
            '%s is not activated' % user.email
        )
    if not login_user(user, remember=data.get('remember', False)):
        raise exception_handler.UserDisabled('failed to login: %s' % user)

    user_log_api.log_user_action(user.id, request.path)
    response_data = user_api.record_user_token(
        user.token, user.expire_timestamp, user=user
    )
    return utils.make_json_response(200, response_data)


@app.route('/users/token', methods=['POST'])
def get_token():
    """user login and return token."""
    return _login(False)


@app.route("/users/login", methods=['POST'])
def login():
    """User login."""
    return _login(True)


@app.route("/users/register", methods=['POST'])
def register():
    """register new user."""
    data = _get_request_data()
    data['is_admin'] = False
    data['active'] = False
    return utils.make_json_response(
        200, user_api.add_user(**data)
    )


@app.route('/users/logout', methods=['POST'])
@login_required
def logout():
    """User logout."""
    user_log_api.log_user_action(current_user.id, request.path)
    response_data = user_api.clean_user_token(
        current_user.token, user=current_user
    )
    logout_user()
    return utils.make_json_response(200, response_data)


@app.route("/users", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def list_users():
    """list users.

    Supported paramters: ['email', 'is_admin', 'active']
    """
    data = _get_request_args(
        is_admin=_bool_converter,
        active=_bool_converter
    )
    return utils.make_json_response(
        200, user_api.list_users(user=current_user, **data)
    )


@app.route("/users", methods=['POST'])
@log_user_action
@login_required
@update_user_token
def add_user():
    """add user.

    Must parameters: ['email', 'password'],
    Optional paramters: ['is_admin', 'active']
    """
    data = _get_request_data()
    user_dict = user_api.add_user(user=current_user, **data)
    return utils.make_json_response(
        200, user_dict
    )


@app.route("/users/<int:user_id>", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def show_user(user_id):
    """Get user by id."""
    data = _get_request_args()
    return utils.make_json_response(
        200, user_api.get_user(user_id, user=current_user, **data)
    )


@app.route("/current-user", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def show_current_user():
    """Get current  user."""
    data = _get_request_args()
    return utils.make_json_response(
        200, user_api.get_current_user(user=current_user, **data)
    )


@app.route("/users/<int:user_id>", methods=['PUT'])
@log_user_action
@login_required
@update_user_token
def update_user(user_id):
    """Update user.

    Supported parameters by self: [
        'email', 'firstname', 'lastname', 'password'
    ]
    Supported parameters by admin ['is_admin', 'active']
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        user_api.update_user(
            user_id,
            user=current_user,
            **data
        )
    )


@app.route("/users/<int:user_id>", methods=['DELETE'])
@log_user_action
@login_required
@update_user_token
def delete_user(user_id):
    """Delete user.

    Delete is only permitted by admin user.
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        user_api.del_user(
            user_id, user=current_user, **data
        )
    )


@app.route("/users/<int:user_id>/permissions", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def list_user_permissions(user_id):
    """Get user permissions."""
    data = _get_request_args()
    return utils.make_json_response(
        200, user_api.get_permissions(user_id, user=current_user, **data)
    )


@app.route("/users/<int:user_id>/action", methods=['POST'])
@log_user_action
@login_required
@update_user_token
def take_user_action(user_id):
    """Take user action.

    Support actions: [
        'add_permissions', 'remove_permissions',
        'set_permissions', 'enable_user',
        'disable_user'
    ]
    """
    data = _get_request_data()
    update_permissions_func = _wrap_response(
        functools.partial(
            user_api.update_permissions, user_id, user=current_user,
        ),
        200
    )

    def disable_user(disable_user=None):
        return user_api.update_user(
            user_id, user=current_user, active=False
        )

    disable_user_func = _wrap_response(
        disable_user,
        200
    )

    def enable_user(enable_user=None):
        return user_api.update_user(
            user_id, user=current_user, active=True
        )

    enable_user_func = _wrap_response(
        enable_user,
        200
    )
    return _group_data_action(
        data,
        add_permissions=update_permissions_func,
        remove_permissions=update_permissions_func,
        set_permissions=update_permissions_func,
        enable_user=enable_user_func,
        disable_user=disable_user_func
    )


@app.route(
    '/users/<int:user_id>/permissions/<int:permission_id>',
    methods=['GET']
)
@log_user_action
@login_required
@update_user_token
def show_user_permission(user_id, permission_id):
    """Get a specific user permission."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        user_api.get_permission(
            user_id, permission_id, user=current_user,
            **data
        )
    )


@app.route("/users/<int:user_id>/permissions", methods=['POST'])
@log_user_action
@login_required
@update_user_token
def add_user_permission(user_id):
    """Add permission to a specific user.

    add_user_permission is only permitted by admin user.
    Must parameters: ['permission_id']
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        user_api.add_permission(
            user_id, user=current_user,
            **data
        )
    )


@app.route(
    '/users/<int:user_id>/permissions/<permission_id>',
    methods=['DELETE']
)
@log_user_action
@login_required
@update_user_token
def delete_user_permission(user_id, permission_id):
    """Delete a specific user permission."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        user_api.del_permission(
            user_id, permission_id, user=current_user,
            **data
        )
    )


@app.route("/permissions", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def list_permissions():
    """List permissions.

    Supported filters: ['id', 'name', 'alias', 'description']
    """
    data = _get_request_args()
    return utils.make_json_response(
        200,
        permission_api.list_permissions(user=current_user, **data)
    )


@app.route("/permissions/<int:permission_id>", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def show_permission(permission_id):
    """Get permission."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        permission_api.get_permission(permission_id, user=current_user, **data)
    )


def _filter_timestamp(data):
    """parse timestamp related params to db api understandable params.

    Example:
        {'timestamp_start': '2005-12-23 12:00:00'} to
        {'timestamp': {'ge': timestamp('2005-12-23 12:00:00')}},
        {'timestamp_end': '2005-12-23 12:00:00'} to
        {'timestamp': {'le': timestamp('2005-12-23 12:00:00')}},
        {'timestamp_range': '2005-12-23 12:00:00,2005-12-24 12:00:00'} to
        {'timestamp': {'between': [
                timestamp('2005-12-23 12:00:00'),
                timestamp('2005-12-24 12:00:00')
            ]
        }}

    The timestamp related params can be declared multi times.
    """
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
@update_user_token
def list_all_user_actions():
    """List all users actions.

    Supported filters: [
        'timestamp_start', 'timestamp_end', 'timestamp_range',
        'user_email'
    ]
    """
    data = _get_request_args()
    _filter_timestamp(data)
    return utils.make_json_response(
        200,
        user_log_api.list_actions(
            user=current_user, **data
        )
    )


@app.route("/users/<int:user_id>/logs", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def list_user_actions(user_id):
    """List user actions for specific user.

    Supported filters: [
        'timestamp_start', 'timestamp_end', 'timestamp_range',
    ]
    """
    data = _get_request_args()
    _filter_timestamp(data)
    return utils.make_json_response(
        200,
        user_log_api.list_user_actions(
            user_id, user=current_user, **data
        )
    )


@app.route("/users/logs", methods=['DELETE'])
@log_user_action
@login_required
@update_user_token
def delete_all_user_actions():
    """Delete all user actions."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        user_log_api.del_actions(
            user=current_user, **data
        )
    )


@app.route("/users/<int:user_id>/logs", methods=['DELETE'])
@log_user_action
@login_required
@update_user_token
def delete_user_actions(user_id):
    """Delete user actions for specific user."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        user_log_api.del_user_actions(
            user_id, user=current_user, **data
        )
    )


def _filter_switch_ip(data):
    """filter switch ip related params to db/api understandable format.

    Examples:
        {'switchIp': '10.0.0.1'} to {'ip_int': {'eq': int of '10.0.0.1'}}
        {'switchIpStart': '10.0.0.1'} to
        {'ip_int': {'ge': int of '10.0.0.1'}}
        {'switchIpEnd': '10.0.0.1'} to
        {'ip_int': {'le': int of '10.0.0.1'}}
        {'switchIpRange': '10.0.0.1,10.0.0.254'} to
        {'ip_int': {'between': [int of '10.0.0.1', int of '10.0.0.254']}}

    the switch ip related params can be declared multi times.
    """
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
@update_user_token
def list_switches():
    """List switches.

    Supported filters: [
        'switchIp', 'switchIpStart', 'switchIpEnd',
        'switchIpEnd', 'vendor', 'state'
    ]
    """
    data = _get_request_args()
    _filter_switch_ip(data)
    return utils.make_json_response(
        200,
        switch_api.list_switches(
            user=current_user, **data
        )
    )


@app.route("/switches/<int:switch_id>", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def show_switch(switch_id):
    """Get switch."""
    data = _get_request_args()
    return utils.make_json_response(
        200, switch_api.get_switch(switch_id, user=current_user, **data)
    )


@app.route("/switches", methods=['POST'])
@log_user_action
@login_required
@update_user_token
def add_switch():
    """add switch.

    Must fields: ['ip']
    Optional fields: [
        'credentials', 'vendor', 'state',
        'err_msg', 'filters'
    ]
    """
    data = _get_request_data()
    _replace_data(data, {'filters': 'machine_filters'})
    return utils.make_json_response(
        200,
        switch_api.add_switch(user=current_user, **data)
    )


@app.route("/switchesbatch", methods=['POST'])
@log_user_action
@login_required
@update_user_token
def add_switches():
    """batch add switches.

    request data is a list of dict. Each dict must contain ['ip'],
    may contain [
        'credentials', 'vendor', 'state', 'err_msg', 'filters'
    ]
    """
    data = _get_request_data_as_list()
    for item_data in data:
        _replace_data(item_data, {'filters': 'machine_filters'})
    return utils.make_json_response(
        200,
        switch_api.add_switches(
            data=data, user=current_user
        )
    )


@app.route("/switches/<int:switch_id>", methods=['PUT'])
@log_user_action
@login_required
@update_user_token
def update_switch(switch_id):
    """update switch.

    Supported fields: [
        'ip', 'credentials', 'vendor', 'state',
        'err_msg', 'filters'
    ]
    """
    data = _get_request_data()
    _replace_data(data, {'filters': 'machine_filters'})
    return utils.make_json_response(
        200,
        switch_api.update_switch(switch_id, user=current_user, **data)
    )


@app.route("/switches/<int:switch_id>", methods=['PATCH'])
@log_user_action
@login_required
@update_user_token
def patch_switch(switch_id):
    """patch switch.

    Supported fields: [
        'credentials', 'filters'
    ]
    """
    data = _get_request_data()
    _replace_data(data, {'filters': 'machine_filters'})
    return utils.make_json_response(
        200,
        switch_api.patch_switch(switch_id, user=current_user, **data)
    )


@app.route("/switches/<int:switch_id>", methods=['DELETE'])
@log_user_action
@login_required
@update_user_token
def delete_switch(switch_id):
    """delete switch."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        switch_api.del_switch(switch_id, user=current_user, **data)
    )


@util.deprecated
@app.route("/switch-filters", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def list_switch_filters():
    """List switch filters."""
    data = _get_request_args()
    _filter_switch_ip(data)
    return utils.make_json_response(
        200,
        switch_api.list_switch_filters(
            user=current_user, **data
        )
    )


@util.deprecated
@app.route("/switch-filters/<int:switch_id>", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def show_switch_filters(switch_id):
    """Get switch filters."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        switch_api.get_switch_filters(switch_id, user=current_user, **data)
    )


@util.deprecated
@app.route("/switch-filters/<int:switch_id>", methods=['PUT'])
@log_user_action
@login_required
@update_user_token
def update_switch_filters(switch_id):
    """update switch filters."""
    data = _get_request_data()
    _replace_data(data, {'filters': 'machine_filters'})
    return utils.make_json_response(
        200,
        switch_api.update_switch_filters(switch_id, user=current_user, **data)
    )


@util.deprecated
@app.route("/switch-filters/<int:switch_id>", methods=['PATCH'])
@log_user_action
@login_required
@update_user_token
def patch_switch_filters(switch_id):
    """patch switch filters."""
    data = _get_request_data()
    _replace_data(data, {'filters': 'machine_filters'})
    return utils.make_json_response(
        200,
        switch_api.patch_switch_filter(switch_id, user=current_user, **data)
    )


def _filter_switch_port(data):
    """Generate switch machine filters by switch port related fields.

    Examples:
       {'port': 'ae20'} to {'port': {'eq': 'ae20'}}
       {'portStart': 20, 'portPrefix': 'ae', 'portSuffix': ''} to
       {'port': {'startswith': 'ae', 'endswith': '', 'resp_ge': 20}}
       {'portEnd': 20, 'portPrefix': 'ae', 'portSuffix': ''} to
       {'port': {'startswith': 'ae', 'endswith': '', 'resp_le': 20}}
       {'portRange': '20,40', 'portPrefix': 'ae', 'portSuffix': ''} to
       {'port': {
           'startswith': 'ae', 'endswith': '', 'resp_range': [(20. 40)]
       }}

    For each switch machines port, it extracts portNumber from
    '<portPrefix><portNumber><portSuffix>' and filter the returned switch
    machines by the filters.
    """
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


def _filter_general(data, key):
    """Generate general filter for db/api returned list.

    Supported filter type: [
        'resp_eq', 'resp_in', 'resp_le', 'resp_ge',
        'resp_gt', 'resp_lt', 'resp_match'
    ]
    """
    general_filter = {}
    general = _get_data_list(data, key)
    if general:
        general_filter['resp_in'] = general
        data[key] = general_filter


def _filter_machine_tag(data):
    """Generate filter for machine tag.

    Examples:
       original returns:
          [{'tag': {
              'city': 'beijing',
              'building': 'tsinghua main building',
              'room': '205', 'rack': 'a2b3',
              'stack': '20'
          }},{'location': {
              'city': 'beijing',
              'building': 'tsinghua main building',
              'room': '205', 'rack': 'a2b2',
              'stack': '20'
          }}]
       filter: {'tag': 'room=205;rack=a2b3'}
       filtered: [{'tag': {
          'city': 'beijing',
          'building': 'tsinghua main building',
          'room': '205', 'rack': 'a2b3',
          'stack': '20'
       }}]
    """
    tag_filter = {}
    tags = _get_data_list(data, 'tag')
    if tags:
        tag_filter['resp_in'] = []
        for tag in tags:
            tag_filter['resp_in'].append(
                util.parse_request_arg_dict(tag)
            )
        data['tag'] = tag_filter


def _filter_machine_location(data):
    """Generate filter for machine location.

    Examples:
       original returns:
          [{'location': {
              'city': 'beijing',
              'building': 'tsinghua main building',
              'room': '205', 'rack': 'a2b3',
              'stack': '20'
          }},{'location': {
              'city': 'beijing',
              'building': 'tsinghua main building',
              'room': '205', 'rack': 'a2b2',
              'stack': '20'
          }}]
       filter: {'location': 'room=205;rack=a2b3'}
       filtered: [{'location': {
          'city': 'beijing',
          'building': 'tsinghua main building',
          'room': '205', 'rack': 'a2b3',
          'stack': '20'
       }}]
    """
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
@update_user_token
def list_switch_machines(switch_id):
    """Get switch machines.

    Supported filters: [
        'port', 'portStart', 'portEnd', 'portRange',
        'portPrefix', 'portSuffix', 'vlans', 'tag', 'location'
    ]
    """
    data = _get_request_args(vlans=_int_converter)
    _filter_switch_port(data)
    _filter_general(data, 'vlans')
    _filter_machine_tag(data)
    _filter_machine_location(data)
    return utils.make_json_response(
        200,
        switch_api.list_switch_machines(
            switch_id, user=current_user, **data
        )
    )


@app.route("/switches/<int:switch_id>/machines-hosts", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def list_switch_machines_hosts(switch_id):
    """Get switch machines or hosts.

    Supported filters: [
        'port', 'portStart', 'portEnd', 'portRange',
        'portPrefix', 'portSuffix', 'vlans', 'tag', 'location',
        'os_name', 'os_id'
    ]

    """
    data = _get_request_args(vlans=_int_converter, os_id=_int_converter)
    _filter_switch_port(data)
    _filter_general(data, 'vlans')
    _filter_machine_tag(data)
    _filter_machine_location(data)
    _filter_general(data, 'os_name')
    # TODO(xicheng): os_id filter should be removed later
    _filter_general(data, 'os_id')
    return utils.make_json_response(
        200,
        switch_api.list_switch_machines_hosts(
            switch_id, user=current_user, **data
        )
    )


@app.route("/switches/<int:switch_id>/machines", methods=['POST'])
@log_user_action
@login_required
@update_user_token
def add_switch_machine(switch_id):
    """add switch machine.

    Must fields: ['mac', 'port']
    Optional fields: ['vlans', 'ipmi_credentials', 'tag', 'location']
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        switch_api.add_switch_machine(switch_id, user=current_user, **data)
    )


@app.route("/switches/machines", methods=['POST'])
@log_user_action
@login_required
@update_user_token
def add_switch_machines():
    """batch add switch machines.

    request data is list of dict which contains switch machine fields.
    Each dict must contain ['switch_ip', 'mac', 'port'],
    may contain ['vlans', 'ipmi_credentials', 'tag', 'location'].
    """
    data = _get_request_data_as_list()
    return utils.make_json_response(
        200, switch_api.add_switch_machines(
            data=data, user=current_user
        )
    )


@app.route(
    '/switches/<int:switch_id>/machines/<int:machine_id>',
    methods=['GET']
)
@log_user_action
@login_required
@update_user_token
def show_switch_machine(switch_id, machine_id):
    """get switch machine."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        switch_api.get_switch_machine(
            switch_id, machine_id, user=current_user, **data
        )
    )


@app.route(
    '/switches/<int:switch_id>/machines/<int:machine_id>',
    methods=['PUT']
)
@log_user_action
@login_required
@update_user_token
def update_switch_machine(switch_id, machine_id):
    """update switch machine.

    Supported fields: [
        'port', 'vlans', 'ipmi_credentials', 'tag', 'location'
    ]
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        switch_api.update_switch_machine(
            switch_id, machine_id, user=current_user, **data
        )
    )


@app.route(
    '/switches/<int:switch_id>/machines/<int:machine_id>',
    methods=['PATCH']
)
@log_user_action
@login_required
@update_user_token
def patch_switch_machine(switch_id, machine_id):
    """patch switch machine.

    Supported fields: [
        'vlans', 'ipmi_credentials', 'tag', 'location'
    ]
    """
    data = _get_request_data()
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
@update_user_token
def delete_switch_machine(switch_id, machine_id):
    """Delete switch machine."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        switch_api.del_switch_machine(
            switch_id, machine_id, user=current_user, **data
        )
    )


@app.route("/switches/<int:switch_id>/action", methods=['POST'])
@log_user_action
@login_required
@update_user_token
def take_switch_action(switch_id):
    """take switch action.

    Supported actions: [
        'find_machines', 'add_machines', 'remove_machines',
        'set_machines'
    ]
    """
    data = _get_request_data()
    poll_switch_func = _wrap_response(
        functools.partial(
            switch_api.poll_switch, switch_id, user=current_user,
        ),
        202
    )
    update_switch_machines_func = _wrap_response(
        functools.partial(
            switch_api.update_switch_machines, switch_id, user=current_user,
        ),
        200
    )
    return _group_data_action(
        data,
        find_machines=poll_switch_func,
        add_machines=update_switch_machines_func,
        remove_machines=update_switch_machines_func,
        set_machines=update_switch_machines_func
    )


@app.route("/machines/<int:machine_id>/action", methods=['POST'])
@log_user_action
@login_required
@update_user_token
def take_machine_action(machine_id):
    """take machine action.

    Supported actions: ['tag', 'poweron', 'poweroff', 'reset']
    """
    data = _get_request_data()
    tag_func = _wrap_response(
        functools.partial(
            machine_api.update_machine, machine_id, user=current_user,
        ),
        200
    )
    poweron_func = _wrap_response(
        functools.partial(
            machine_api.poweron_machine, machine_id, user=current_user,
        ),
        202
    )
    poweroff_func = _wrap_response(
        functools.partial(
            machine_api.poweroff_machine, machine_id, user=current_user,
        ),
        202
    )
    reset_func = _wrap_response(
        functools.partial(
            machine_api.reset_machine, machine_id, user=current_user,
        ),
        202
    )
    return _group_data_action(
        data,
        tag=tag_func,
        poweron=poweron_func,
        poweroff=poweroff_func,
        reset=reset_func
    )


@app.route("/switch-machines", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def list_switchmachines():
    """List switch machines.

    Supported filters: [
        'vlans', 'switchIp', 'SwitchIpStart',
        'SwitchIpEnd', 'SwitchIpRange', 'port',
        'portStart', 'portEnd', 'portRange',
        'location', 'tag', 'mac'
    ]
    """
    data = _get_request_args(vlans=_int_converter)
    _filter_switch_ip(data)
    _filter_switch_port(data)
    _filter_general(data, 'vlans')
    _filter_machine_tag(data)
    _filter_machine_location(data)
    return utils.make_json_response(
        200,
        switch_api.list_switchmachines(
            user=current_user, **data
        )
    )


@app.route("/switches-machines-hosts", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def list_switchmachines_hosts():
    """List switch machines or hosts.

    Supported filters: [
        'vlans', 'switchIp', 'SwitchIpStart',
        'SwitchIpEnd', 'SwitchIpRange', 'port',
        'portStart', 'portEnd', 'portRange',
        'location', 'tag', 'mac', 'os_name'
    ]

    """
    data = _get_request_args(vlans=_int_converter, os_id=_int_converter)
    _filter_switch_ip(data)
    _filter_switch_port(data)
    _filter_general(data, 'vlans')
    _filter_machine_tag(data)
    _filter_machine_location(data)
    _filter_general(data, 'os_name')
    return utils.make_json_response(
        200,
        switch_api.list_switchmachines_hosts(
            user=current_user, **data
        )
    )


@app.route(
    '/switch-machines/<int:switch_machine_id>',
    methods=['GET']
)
@log_user_action
@login_required
@update_user_token
def show_switchmachine(switch_machine_id):
    """get switch machine."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        switch_api.get_switchmachine(
            switch_machine_id, user=current_user, **data
        )
    )


@app.route(
    '/switch-machines/<int:switch_machine_id>',
    methods=['PUT']
)
@log_user_action
@login_required
@update_user_token
def update_switchmachine(switch_machine_id):
    """update switch machine.

    Support fields: [
        ''port', 'vlans', 'ipmi_credentials', 'tag', 'location'
    ]
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        switch_api.update_switchmachine(
            switch_machine_id, user=current_user, **data
        )
    )


@app.route('/switch-machines/<int:switch_machine_id>', methods=['PATCH'])
@log_user_action
@login_required
@update_user_token
def patch_switchmachine(switch_machine_id):
    """patch switch machine.

    Support fields: [
        'vlans', 'ipmi_credentials', 'tag', 'location'
    ]
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        switch_api.patch_switchmachine(
            switch_machine_id, user=current_user, **data
        )
    )


@app.route("/switch-machines/<int:switch_machine_id>", methods=['DELETE'])
@log_user_action
@login_required
@update_user_token
def delete_switchmachine(switch_machine_id):
    """Delete switch machine."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        switch_api.del_switchmachine(
            switch_machine_id, user=current_user, **data
        )
    )


@app.route("/machines", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def list_machines():
    """List machines.

    Supported filters: [
        'tag', 'location', 'mac'
    ]
    """
    data = _get_request_args()
    _filter_machine_tag(data)
    _filter_machine_location(data)
    return utils.make_json_response(
        200,
        machine_api.list_machines(
            user=current_user, **data
        )
    )


@app.route("/machines", methods=['POST'])
def add_machine():
    """add machine by tinycore.

    supported fileds: [
        'tag', 'location', 'ipmi_credentials',
        'machine_attributes'
    ]
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        machine_api.add_machine(**data)
    )


@app.route("/machines/<int:machine_id>", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def show_machine(machine_id):
    """Get machine."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        machine_api.get_machine(
            machine_id, user=current_user, **data
        )
    )


@app.route("/machines/<int:machine_id>", methods=['PUT'])
@log_user_action
@login_required
@update_user_token
def update_machine(machine_id):
    """update machine.

    Supported fields: [
        'tag', 'location', 'ipmi_credentials',
        'machine_attributes'
    ]
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        machine_api.update_machine(
            machine_id, user=current_user, **data
        )
    )


@app.route("/machines/<int:machine_id>", methods=['PATCH'])
@log_user_action
@login_required
@update_user_token
def patch_machine(machine_id):
    """patch machine.

    Supported fields: [
        'tag', 'location', 'ipmi_credentials',
        'machine_attributes'
    ]
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        machine_api.patch_machine(
            machine_id, user=current_user, **data
        )
    )


@app.route("/machines/<int:machine_id>", methods=['DELETE'])
@log_user_action
@login_required
@update_user_token
def delete_machine(machine_id):
    """Delete machine."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        machine_api.del_machine(
            machine_id, user=current_user, **data
        )
    )


@app.route("/subnets", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def list_subnets():
    """List subnets.

    Supported filters: [
        'subnet', 'name'
    ]
    """
    data = _get_request_args()
    return utils.make_json_response(
        200,
        network_api.list_subnets(
            user=current_user, **data
        )
    )


@app.route("/subnets/<int:subnet_id>", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def show_subnet(subnet_id):
    """Get subnet."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        network_api.get_subnet(
            subnet_id, user=current_user, **data
        )
    )


@app.route("/subnets", methods=['POST'])
@log_user_action
@login_required
@update_user_token
def add_subnet():
    """add subnet.

    Must fields: ['subnet']
    Optional fields: ['name']
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        network_api.add_subnet(user=current_user, **data)
    )


@app.route("/subnets/<int:subnet_id>", methods=['PUT'])
@log_user_action
@login_required
@update_user_token
def update_subnet(subnet_id):
    """update subnet.

    Support fields: ['subnet', 'name']
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        network_api.update_subnet(
            subnet_id, user=current_user, **data
        )
    )


@app.route("/subnets/<int:subnet_id>", methods=['DELETE'])
@log_user_action
@login_required
@update_user_token
def delete_subnet(subnet_id):
    """Delete subnet."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        network_api.del_subnet(
            subnet_id, user=current_user, **data
        )
    )


@app.route("/adapters", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def list_adapters():
    """List adapters.

    Supported filters: [
        'name'
    ]
    """
    data = _get_request_args()
    _filter_general(data, 'name')
    return utils.make_json_response(
        200,
        adapter_api.list_adapters(
            user=current_user, **data
        )
    )


@app.route("/adapters/<adapter_id>", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def show_adapter(adapter_id):
    """Get adapter."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        adapter_api.get_adapter(
            adapter_id, user=current_user, **data
        )
    )


@app.route("/adapters/<adapter_id>/metadata", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def show_adapter_metadata(adapter_id):
    """Get adapter metadata."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        metadata_api.get_package_metadata(
            adapter_id, user=current_user, **data
        )
    )


@app.route("/oses/<os_id>/metadata", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def show_os_metadata(os_id):
    """Get os metadata."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        metadata_api.get_os_metadata(
            os_id, user=current_user, **data
        )
    )


@app.route("/oses/<os_id>/ui_metadata", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def convert_os_metadata(os_id):
    """Convert os metadata to ui os metadata."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        metadata_api.get_os_ui_metadata(
            os_id, user=current_user, **data
        )
    )


@app.route("/flavors/<flavor_id>/metadata", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def show_flavor_metadata(flavor_id):
    """Get flavor metadata."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        metadata_api.get_flavor_metadata(
            flavor_id, user=current_user, **data
        )
    )


@app.route("/flavors/<flavor_id>/ui_metadata", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def convert_flavor_metadata(flavor_id):
    """Convert flavor metadata to ui flavor metadata."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        metadata_api.get_flavor_ui_metadata(
            flavor_id, user=current_user, **data
        )
    )


@app.route(
    "/adapters/<adapter_id>/oses/<os_id>/metadata",
    methods=['GET']
)
@log_user_action
@login_required
@update_user_token
def show_adapter_os_metadata(adapter_id, os_id):
    """Get adapter metadata."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        metadata_api.get_package_os_metadata(
            adapter_id, os_id, user=current_user, **data
        )
    )


@app.route("/clusters", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def list_clusters():
    """List clusters.

    Supported filters: [
        'name', 'os_name', 'owner', 'adapter_name', 'flavor_name'
    ]
    """
    data = _get_request_args()
    return utils.make_json_response(
        200,
        cluster_api.list_clusters(
            user=current_user, **data
        )
    )


@app.route("/clusters/<int:cluster_id>", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def show_cluster(cluster_id):
    """Get cluster."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        cluster_api.get_cluster(
            cluster_id, user=current_user, **data
        )
    )


@app.route("/clusters", methods=['POST'])
@log_user_action
@login_required
@update_user_token
def add_cluster():
    """add cluster.

    Must fields: ['name', 'adapter_id', 'os_id']
    Optional fields: ['flavor_id']
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.add_cluster(user=current_user, **data)
    )


@app.route("/clusters/<int:cluster_id>", methods=['PUT'])
@log_user_action
@login_required
@update_user_token
def update_cluster(cluster_id):
    """update cluster.

    Supported fields: ['name', 'reinstall_distributed_system']
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.update_cluster(
            cluster_id, user=current_user, **data
        )
    )


@app.route("/clusters/<int:cluster_id>", methods=['DELETE'])
@log_user_action
@login_required
@update_user_token
def delete_cluster(cluster_id):
    """Delete cluster."""
    data = _get_request_data()
    response = cluster_api.del_cluster(
        cluster_id, user=current_user, **data
    )
    if 'status' in response:
        return utils.make_json_response(
            202, response
        )
    else:
        return utils.make_json_response(
            200, response
        )


@app.route("/clusters/<int:cluster_id>/config", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def show_cluster_config(cluster_id):
    """Get cluster config."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        cluster_api.get_cluster_config(
            cluster_id, user=current_user, **data
        )
    )


@app.route("/clusters/<int:cluster_id>/metadata", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def show_cluster_metadata(cluster_id):
    """Get cluster metadata."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        cluster_api.get_cluster_metadata(
            cluster_id, user=current_user, **data
        )
    )


@app.route("/clusters/<int:cluster_id>/config", methods=['PUT'])
@log_user_action
@login_required
@update_user_token
def update_cluster_config(cluster_id):
    """update cluster config.

    Supported fields: ['os_config', 'package_config', 'config_step']
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.update_cluster_config(
            cluster_id, user=current_user, **data
        )
    )


@app.route("/clusters/<int:cluster_id>/config", methods=['PATCH'])
@log_user_action
@login_required
@update_user_token
def patch_cluster_config(cluster_id):
    """patch cluster config.

    Supported fields: ['os_config', 'package_config', 'config_step']
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.patch_cluster_config(cluster_id, user=current_user, **data)
    )


@app.route("/clusters/<int:cluster_id>/config", methods=['DELETE'])
@log_user_action
@login_required
@update_user_token
def delete_cluster_config(cluster_id):
    """Delete cluster config."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.del_cluster_config(
            cluster_id, user=current_user, **data
        )
    )


@app.route("/clusters/<int:cluster_id>/action", methods=['POST'])
@log_user_action
@login_required
@update_user_token
def take_cluster_action(cluster_id):
    """take cluster action.

    Supported actions: [
        'add_hosts', 'remove_hosts', 'set_hosts',
        'review', 'deploy', 'check_health', 'apply_patch'
    ]
    """
    data = _get_request_data()
    url_root = request.url_root

    update_cluster_hosts_func = _wrap_response(
        functools.partial(
            cluster_api.update_cluster_hosts, cluster_id, user=current_user,
        ),
        200
    )
    review_cluster_func = _wrap_response(
        functools.partial(
            cluster_api.review_cluster, cluster_id, user=current_user,
        ),
        200
    )
    deploy_cluster_func = _wrap_response(
        functools.partial(
            cluster_api.deploy_cluster, cluster_id, user=current_user,
        ),
        202
    )
    redeploy_cluster_func = _wrap_response(
        functools.partial(
            cluster_api.redeploy_cluster, cluster_id, user=current_user,
        ),
        202
    )
    patch_cluster_func = _wrap_response(
        functools.partial(
            cluster_api.patch_cluster, cluster_id, user=current_user,
        ),
        202
    )
    check_cluster_health_func = _wrap_response(
        functools.partial(
            health_report_api.start_check_cluster_health,
            cluster_id,
            '%s/clusters/%s/healthreports' % (url_root, cluster_id),
            user=current_user
        ),
        202
    )
    return _group_data_action(
        data,
        add_hosts=update_cluster_hosts_func,
        set_hosts=update_cluster_hosts_func,
        remove_hosts=update_cluster_hosts_func,
        review=review_cluster_func,
        deploy=deploy_cluster_func,
        redeploy=redeploy_cluster_func,
        apply_patch=patch_cluster_func,
        check_health=check_cluster_health_func
    )


@app.route("/clusters/<int:cluster_id>/state", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def get_cluster_state(cluster_id):
    """Get cluster state."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        cluster_api.get_cluster_state(
            cluster_id, user=current_user, **data
        )
    )


@app.route("/clusters/<int:cluster_id>/healthreports", methods=['POST'])
def create_health_reports(cluster_id):
    """Create a health check report.

    Must fields: ['name']
    Optional fields: [
        'display_name', 'report', 'category', 'state', 'error_message'
    ]
    """
    data = _get_request_data()
    output = []
    logging.info('create_health_reports for cluster %s: %s',
                 cluster_id, data)
    if 'report_list' in data:
        for report in data['report_list']:
            try:
                output.append(
                    health_report_api.add_report_record(
                        cluster_id, **report
                    )
                )
            except Exception as error:
                logging.exception(error)
                continue

    else:
        output = health_report_api.add_report_record(
            cluster_id, **data
        )

    return utils.make_json_response(
        200,
        output
    )


@app.route("/clusters/<int:cluster_id>/healthreports", methods=['PUT'])
def bulk_update_reports(cluster_id):
    """Bulk update reports.

    request data is a list of health report.
    Each health report must contain ['name'],
    may contain [
        'display_name', 'report', 'category', 'state', 'error_message'
    ]
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        health_report_api.update_multi_reports(
            cluster_id, **data
        )
    )


@app.route("/clusters/<int:cluster_id>/healthreports", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def list_health_reports(cluster_id):
    """list health report for a cluster."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        health_report_api.list_health_reports(
            cluster_id, user=current_user, **data
        )
    )


@app.route("/clusters/<int:cluster_id>/healthreports/<name>", methods=['PUT'])
def update_health_report(cluster_id, name):
    """Update cluster health report.

    Supported fields: ['report', 'state', 'error_message']
    """
    data = _get_request_data()
    if 'error_message' not in data:
        data['error_message'] = ""

    return utils.make_json_response(
        200,
        health_report_api.update_report(
            cluster_id, name, **data
        )
    )


@app.route("/clusters/<int:cluster_id>/healthreports/<name>", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def get_health_report(cluster_id, name):
    """Get health report by cluster id and name."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        health_report_api.get_health_report(
            cluster_id, name, user=current_user, **data
        )
    )


@app.route("/clusters/<int:cluster_id>/hosts", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def list_cluster_hosts(cluster_id):
    """Get cluster hosts."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        _reformat_host(cluster_api.list_cluster_hosts(
            cluster_id, user=current_user, **data
        ))
    )


@app.route("/clusterhosts", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def list_clusterhosts():
    """Get cluster hosts."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        _reformat_host(cluster_api.list_clusterhosts(
            user=current_user, **data
        ))
    )


@app.route("/clusters/<int:cluster_id>/hosts/<int:host_id>", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def show_cluster_host(cluster_id, host_id):
    """Get clusterhost."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        _reformat_host(cluster_api.get_cluster_host(
            cluster_id, host_id, user=current_user, **data
        ))
    )


@app.route("/clusterhosts/<int:clusterhost_id>", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def show_clusterhost(clusterhost_id):
    """Get clusterhost."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        _reformat_host(cluster_api.get_clusterhost(
            clusterhost_id, user=current_user, **data
        ))
    )


@app.route("/clusters/<int:cluster_id>/hosts", methods=['POST'])
@log_user_action
@login_required
@update_user_token
def add_cluster_host(cluster_id):
    """update cluster hosts.

    Must fields: ['machine_id']
    Optional fields: ['name', 'reinstall_os', 'roles']
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.add_cluster_host(cluster_id, user=current_user, **data)
    )


@app.route(
    '/clusters/<int:cluster_id>/hosts/<int:host_id>',
    methods=['PUT']
)
@log_user_action
@login_required
@update_user_token
def update_cluster_host(cluster_id, host_id):
    """Update cluster host.

    Supported fields: ['name', 'reinstall_os', 'roles']
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.update_cluster_host(
            cluster_id, host_id, user=current_user, **data
        )
    )


@app.route(
    '/clusterhosts/<int:clusterhost_id>',
    methods=['PUT']
)
@log_user_action
@login_required
@update_user_token
def update_clusterhost(clusterhost_id):
    """Update cluster host.

    Supported fields: ['name', 'reinstall_os', 'roles']
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.update_clusterhost(
            clusterhost_id, user=current_user, **data
        )
    )


@app.route(
    '/clusters/<int:cluster_id>/hosts/<int:host_id>',
    methods=['PATCH']
)
@log_user_action
@login_required
@update_user_token
def patch_cluster_host(cluster_id, host_id):
    """Update cluster host.

    Supported fields: ['roles']
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.patch_cluster_host(
            cluster_id, host_id, user=current_user, **data
        )
    )


@app.route(
    '/clusterhosts/<int:clusterhost_id>',
    methods=['PATCH']
)
@log_user_action
@login_required
@update_user_token
def patch_clusterhost(clusterhost_id):
    """Update cluster host.

    Supported fields: ['roles']
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.patch_clusterhost(
            clusterhost_id, user=current_user, **data
        )
    )


@app.route(
    '/clusters/<int:cluster_id>/hosts/<int:host_id>',
    methods=['DELETE']
)
@log_user_action
@login_required
@update_user_token
def delete_cluster_host(cluster_id, host_id):
    """Delete cluster host."""
    data = _get_request_data()
    response = cluster_api.del_cluster_host(
        cluster_id, host_id, user=current_user, **data
    )
    if 'status' in response:
        return utils.make_json_response(
            202, response
        )
    else:
        return utils.make_json_response(
            200, response
        )


@app.route(
    '/clusterhosts/<int:clusterhost_id>',
    methods=['DELETE']
)
@log_user_action
@login_required
@update_user_token
def delete_clusterhost(clusterhost_id):
    """Delete cluster host."""
    data = _get_request_data()
    response = cluster_api.del_clusterhost(
        clusterhost_id, user=current_user, **data
    )
    if 'status' in response:
        return utils.make_json_response(
            202, response
        )
    else:
        return utils.make_json_response(
            200, response
        )


@app.route(
    "/clusters/<int:cluster_id>/hosts/<int:host_id>/config",
    methods=['GET']
)
@log_user_action
@login_required
@update_user_token
def show_cluster_host_config(cluster_id, host_id):
    """Get clusterhost config."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        cluster_api.get_cluster_host_config(
            cluster_id, host_id, user=current_user, **data
        )
    )


@app.route("/clusterhosts/<int:clusterhost_id>/config", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def show_clusterhost_config(clusterhost_id):
    """Get clusterhost config."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        cluster_api.get_clusterhost_config(
            clusterhost_id, user=current_user, **data
        )
    )


@app.route(
    "/clusters/<int:cluster_id>/hosts/<int:host_id>/config",
    methods=['PUT']
)
@log_user_action
@login_required
@update_user_token
def update_cluster_host_config(cluster_id, host_id):
    """update clusterhost config.

    Supported fields: ['os_config', package_config']
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.update_cluster_host_config(
            cluster_id, host_id, user=current_user, **data
        )
    )


@app.route("/clusterhosts/<int:clusterhost_id>/config", methods=['PUT'])
@log_user_action
@login_required
@update_user_token
def update_clusterhost_config(clusterhost_id):
    """update clusterhost config.

    Supported fields: ['os_config', 'package_config']
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.update_clusterhost_config(
            clusterhost_id, user=current_user, **data
        )
    )


@app.route(
    "/clusters/<int:cluster_id>/hosts/<int:host_id>/config",
    methods=['PATCH']
)
@log_user_action
@login_required
@update_user_token
def patch_cluster_host_config(cluster_id, host_id):
    """patch clusterhost config."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.patch_cluster_host_config(
            cluster_id, host_id, user=current_user, **data
        )
    )


@app.route("/clusterhosts/<int:clusterhost_id>", methods=['PATCH'])
@log_user_action
@login_required
@update_user_token
def patch_clusterhost_config(clusterhost_id):
    """patch clusterhost config."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.patch_clusterhost_config(
            clusterhost_id, user=current_user, **data
        )
    )


@app.route(
    "/clusters/<int:cluster_id>/hosts/<int:host_id>/config",
    methods=['DELETE']
)
@log_user_action
@login_required
@update_user_token
def delete_cluster_host_config(cluster_id, host_id):
    """Delete clusterhost config."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.del_clusterhost_config(
            cluster_id, host_id, user=current_user, **data
        )
    )


@app.route("/clusterhosts/<int:clusterhost_id>/config", methods=['DELETE'])
@log_user_action
@login_required
@update_user_token
def delete_clusterhost_config(clusterhost_id):
    """Delete clusterhost config."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.del_clusterhost_config(
            clusterhost_id, user=current_user, **data
        )
    )


@app.route(
    "/clusters/<int:cluster_id>/hosts/<int:host_id>/state",
    methods=['GET']
)
@log_user_action
@login_required
@update_user_token
def show_cluster_host_state(cluster_id, host_id):
    """Get clusterhost state."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        cluster_api.get_cluster_host_state(
            cluster_id, host_id, user=current_user, **data
        )
    )


@app.route("/clusterhosts/<int:clusterhost_id>/state", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def show_clusterhost_state(clusterhost_id):
    """Get clusterhost state."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        cluster_api.get_clusterhost_state(
            clusterhost_id, user=current_user, **data
        )
    )


@app.route(
    "/clusters/<int:cluster_id>/hosts/<int:host_id>/state",
    methods=['PUT', 'POST']
)
@log_user_action
@login_required
@update_user_token
def update_cluster_host_state(cluster_id, host_id):
    """update clusterhost state.

    Supported fields: ['state', 'percentage', 'message', 'severity']
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.update_clusterhost_state(
            cluster_id, host_id, user=current_user, **data
        )
    )


@util.deprecated
@app.route(
    "/clusters/<clustername>/hosts/<hostname>/state_internal",
    methods=['PUT', 'POST']
)
def update_cluster_host_state_internal(clustername, hostname):
    """update clusterhost state.

    Supported fields: ['ready']
    """
    # TODO(xicheng): it should be merged into update_cluster_host_state.
    # TODO(xicheng): the api is not login required and no user checking.
    data = _get_request_data()
    clusters = cluster_api.list_clusters(name=clustername)
    if not clusters:
        raise exception_handler.ItemNotFound(
            'no clusters found for clustername %s' % clustername
        )
    cluster_id = clusters[0]['id']
    hosts = host_api.list_hosts(name=hostname)
    if not hosts:
        raise exception_handler.ItemNotFound(
            'no hosts found for hostname %s' % hostname
        )
    host_id = hosts[0]['id']
    return utils.make_json_response(
        200,
        cluster_api.update_clusterhost_state_internal(
            cluster_id, host_id, **data
        )
    )


@app.route(
    "/clusterhosts/<int:clusterhost_id>/state",
    methods=['PUT', 'POST']
)
@log_user_action
@login_required
@update_user_token
def update_clusterhost_state(clusterhost_id):
    """update clusterhost state.

    Supported fields: ['state', 'percentage', 'message', 'severity']
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        cluster_api.update_clusterhost_state(
            clusterhost_id, user=current_user, **data
        )
    )


@util.deprecated
@app.route(
    "/clusterhosts/<clusterhost_name>/state_internal",
    methods=['PUT', 'POST']
)
def update_clusterhost_state_internal(clusterhost_name):
    """update clusterhost state.

    Supported fields: ['ready']
    """
    data = _get_request_data()
    clusterhosts = cluster_api.list_clusterhosts()
    clusterhost_id = None
    for clusterhost in clusterhosts:
        if clusterhost['name'] == clusterhost_name:
            clusterhost_id = clusterhost['clusterhost_id']
            break
    if not clusterhost_id:
        raise exception_handler.ItemNotFound(
            'no clusterhost found for clusterhost_name %s' % (
                clusterhost_name
            )
        )
    return utils.make_json_response(
        200,
        cluster_api.update_clusterhost_state_internal(
            clusterhost_id, **data
        )
    )


@app.route("/hosts", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def list_hosts():
    """List hosts.

    Supported fields: ['name', 'os_name', 'owner', 'mac']
    """
    data = _get_request_args()
    return utils.make_json_response(
        200,
        _reformat_host(host_api.list_hosts(
            user=current_user, **data
        ))
    )


@app.route("/hosts/<int:host_id>", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def show_host(host_id):
    """Get host."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        _reformat_host(host_api.get_host(
            host_id, user=current_user, **data
        ))
    )


@app.route("/machines-hosts", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def list_machines_or_hosts():
    """Get list of machine of host if the host exists.

    Supported filters: [
        'mac', 'tag', 'location', 'os_name', 'os_id'
    ]
    """
    data = _get_request_args(os_id=_int_converter)
    _filter_machine_tag(data)
    _filter_machine_location(data)
    _filter_general(data, 'os_name')
    _filter_general(data, 'os_id')
    return utils.make_json_response(
        200,
        _reformat_host(host_api.list_machines_or_hosts(
            user=current_user, **data
        ))
    )


@app.route("/machines-hosts/<int:host_id>", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def show_machine_or_host(host_id):
    """Get host."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        _reformat_host(host_api.get_machine_or_host(
            host_id, user=current_user, **data
        ))
    )


@app.route("/hosts/<int:host_id>", methods=['PUT'])
@log_user_action
@login_required
@update_user_token
def update_host(host_id):
    """update host.

    Supported fields: ['name', 'reinstall_os']
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        host_api.update_host(
            host_id, user=current_user, **data
        )
    )


@app.route("/hosts", methods=['PUT'])
@log_user_action
@login_required
@update_user_token
def update_hosts():
    """update hosts.

    update a list of host as dict each may contains following keys: [
        'name', 'reinstall_os'
    ]
    """
    data = _get_request_data_as_list()
    return utils.make_json_response(
        200,
        host_api.update_hosts(
            data, user=current_user,
        )
    )


@app.route("/hosts/<int:host_id>", methods=['DELETE'])
@log_user_action
@login_required
@update_user_token
def delete_host(host_id):
    """Delete host."""
    data = _get_request_data()
    response = host_api.del_host(
        host_id, user=current_user, **data
    )
    if 'status' in response:
        return utils.make_json_response(
            202, response
        )
    else:
        return utils.make_json_response(
            200, response
        )


@app.route("/hosts/<int:host_id>/clusters", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def get_host_clusters(host_id):
    """Get host clusters."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        host_api.get_host_clusters(
            host_id, user=current_user, **data
        )
    )


@app.route("/hosts/<int:host_id>/config", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def show_host_config(host_id):
    """Get host config."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        host_api.get_host_config(
            host_id, user=current_user, **data
        )
    )


@app.route("/hosts/<int:host_id>/config", methods=['PUT'])
@log_user_action
@login_required
@update_user_token
def update_host_config(host_id):
    """update host config."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        host_api.update_host_config(host_id, user=current_user, **data)
    )


@app.route("/hosts/<int:host_id>", methods=['PATCH'])
@log_user_action
@login_required
@update_user_token
def patch_host_config(host_id):
    """patch host config."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        host_api.patch_host_config(host_id, user=current_user, **data)
    )


@app.route("/hosts/<int:host_id>/config", methods=['DELETE'])
@log_user_action
@login_required
@update_user_token
def delete_host_config(host_id):
    """Delete host config."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        host_api.del_host_config(
            host_id, user=current_user, **data
        )
    )


@app.route("/hosts/<int:host_id>/networks", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def list_host_networks(host_id):
    """list host networks.

    Supported filters: [
        'interface', 'ip', 'is_mgmt', 'is_promiscuous'
    ]
    """
    data = _get_request_args()
    return utils.make_json_response(
        200,
        _reformat_host_networks(
            host_api.list_host_networks(
                host_id, user=current_user, **data
            )
        )
    )


@app.route("/host/networks", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def list_hostnetworks():
    """list host networks.

    Supported filters: [
        'interface', 'ip', 'is_mgmt', 'is_promiscuous'
    ]
    """
    data = _get_request_args(
        is_mgmt=_bool_converter,
        is_promiscuous=_bool_converter
    )
    return utils.make_json_response(
        200,
        _reformat_host_networks(
            host_api.list_hostnetworks(user=current_user, **data)
        )
    )


@app.route(
    "/hosts/<int:host_id>/networks/<int:host_network_id>",
    methods=['GET']
)
@log_user_action
@login_required
@update_user_token
def show_host_network(host_id, host_network_id):
    """Get host network."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        host_api.get_host_network(
            host_id, host_network_id, user=current_user, **data
        )
    )


@app.route("/host/networks/<int:host_network_id>", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def show_hostnetwork(host_network_id):
    """Get host network."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        host_api.get_hostnetwork(
            host_network_id, user=current_user, **data
        )
    )


@app.route("/hosts/<int:host_id>/networks", methods=['POST'])
@log_user_action
@login_required
@update_user_token
def add_host_network(host_id):
    """add host network.

    Must fields: ['interface', 'ip', 'subnet_id']
    Optional fields: ['is_mgmt', 'is_promiscuous']
    """
    data = _get_request_data()
    return utils.make_json_response(
        200, host_api.add_host_network(host_id, user=current_user, **data)
    )


@app.route("/hosts/networks", methods=['PUT'])
@log_user_action
@login_required
@update_user_token
def update_host_networks():
    """add host networks.

    update a list of host network each may contain [
        'interface', 'ip', 'subnet_id', 'is_mgmt', 'is_promiscuous'
    ]
    """
    data = _get_request_data_as_list()
    return utils.make_json_response(
        200, host_api.add_host_networks(
            data=data, user=current_user,)
    )


@app.route(
    "/hosts/<int:host_id>/networks/<int:host_network_id>",
    methods=['PUT']
)
@log_user_action
@login_required
@update_user_token
def update_host_network(host_id, host_network_id):
    """update host network.

    supported fields: [
        'interface', 'ip', 'subnet_id', 'subnet', 'is_mgmt',
        'is_promiscuous'
    ]
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        host_api.update_host_network(
            host_id, host_network_id, user=current_user, **data
        )
    )


@app.route("/host-networks/<int:host_network_id>", methods=['PUT'])
@log_user_action
@login_required
@update_user_token
def update_hostnetwork(host_network_id):
    """update host network.

    supported fields: [
        'interface', 'ip', 'subnet_id', 'subnet', 'is_mgmt',
        'is_promiscuous'
    ]
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        host_api.update_hostnetwork(
            host_network_id, user=current_user, **data
        )
    )


@app.route(
    "/hosts/<int:host_id>/networks/<int:host_network_id>",
    methods=['DELETE']
)
@log_user_action
@login_required
@update_user_token
def delete_host_network(host_id, host_network_id):
    """Delete host network."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        host_api.del_host_network(
            host_id, host_network_id, user=current_user, **data
        )
    )


@app.route("/host-networks/<int:host_network_id>", methods=['DELETE'])
@log_user_action
@login_required
@update_user_token
def delete_hostnetwork(host_network_id):
    """Delete host network."""
    data = _get_request_data()
    return utils.make_json_response(
        200,
        host_api.del_hostnetwork(
            host_network_id, user=current_user, **data
        )
    )


@app.route("/hosts/<int:host_id>/state", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def show_host_state(host_id):
    """Get host state."""
    data = _get_request_args()
    return utils.make_json_response(
        200,
        host_api.get_host_state(
            host_id, user=current_user, **data
        )
    )


@app.route("/hosts/<int:host_id>/state", methods=['PUT', 'POST'])
@log_user_action
@login_required
@update_user_token
def update_host_state(host_id):
    """update host state.

    Supported fields: [
        'state', 'percentage', 'message', 'severity'
    ]
    """
    data = _get_request_data()
    return utils.make_json_response(
        200,
        host_api.update_host_state(
            host_id, user=current_user, **data
        )
    )


@util.deprecated
@app.route("/hosts/<host_id>/state_internal", methods=['PUT', 'POST'])
def update_host_state_internal(host_id):
    """update host state.

    Supported fields: ['ready']
    """
    data = _get_request_data()
    host_id = int(host_id)
    hosts = host_api.list_hosts(id=host_id)
    if not hosts:
        raise exception_handler.ItemNotFound(
            'no hosts found for host_id %s' % host_id
        )
    return utils.make_json_response(
        200,
        host_api.update_host_state_internal(
            host_id, **data
        )
    )


@app.route("/hosts/<int:host_id>/action", methods=['POST'])
@log_user_action
@login_required
@update_user_token
def take_host_action(host_id):
    """take host action.

    Supported actions: [
        'poweron', 'poweroff', 'reset'
    ]
    """
    data = _get_request_data()
    poweron_func = _wrap_response(
        functools.partial(
            host_api.poweron_host, host_id, user=current_user,
        ),
        202
    )
    poweroff_func = _wrap_response(
        functools.partial(
            host_api.poweroff_host, host_id, user=current_user,
        ),
        202
    )
    reset_func = _wrap_response(
        functools.partial(
            host_api.reset_host, host_id, user=current_user,
        )
    )
    return _group_data_action(
        data,
        poweron=poweron_func,
        poweroff=poweroff_func,
        reset=reset_func,
    )


def _get_headers(*keys):
    """Get proxied request headers."""
    headers = {}
    for key in keys:
        if key in request.headers:
            headers[key] = request.headers[key]
    return headers


def _get_response_json(response):
    """Get proxies request json formatted response."""
    try:
        return response.json()
    except ValueError:
        return response.text


@app.route("/proxy/<path:url>", methods=['GET'])
@log_user_action
@login_required
@update_user_token
def proxy_get(url):
    """proxy url."""
    headers = _get_headers(
        'Content-Type', 'Accept-Encoding',
        'Content-Encoding', 'Accept', 'User-Agent',
        'Content-MD5', 'Transfer-Encoding', app.config['AUTH_HEADER_NAME'],
        'Cookie'
    )
    response = requests.get(
        '%s/%s' % (setting.PROXY_URL_PREFIX, url),
        params=_get_request_args(),
        headers=headers,
        stream=True
    )
    logging.debug(
        'proxy %s response: %s',
        url, response.text
    )
    return utils.make_json_response(
        response.status_code, _get_response_json(response)
    )


@app.route("/proxy/<path:url>", methods=['POST'])
@log_user_action
@login_required
@update_user_token
def proxy_post(url):
    """proxy url."""
    headers = _get_headers(
        'Content-Type', 'Accept-Encoding',
        'Content-Encoding', 'Accept', 'User-Agent',
        'Content-MD5', 'Transfer-Encoding',
        'Cookie'
    )
    response = requests.post(
        '%s/%s' % (setting.PROXY_URL_PREFIX, url),
        data=request.data,
        headers=headers
    )
    logging.debug(
        'proxy %s response: %s',
        url, response.text
    )
    return utils.make_json_response(
        response.status_code, _get_response_json(response)
    )


@app.route("/proxy/<path:url>", methods=['PUT'])
@log_user_action
@login_required
@update_user_token
def proxy_put(url):
    """proxy url."""
    headers = _get_headers(
        'Content-Type', 'Accept-Encoding',
        'Content-Encoding', 'Accept', 'User-Agent',
        'Content-MD5', 'Transfer-Encoding',
        'Cookie'
    )
    response = requests.put(
        '%s/%s' % (setting.PROXY_URL_PREFIX, url),
        data=request.data,
        headers=headers
    )
    logging.debug(
        'proxy %s response: %s',
        url, response.text
    )
    return utils.make_json_response(
        response.status_code, _get_response_json(response)
    )


@app.route("/proxy/<path:url>", methods=['PATCH'])
@log_user_action
@login_required
@update_user_token
def proxy_patch(url):
    """proxy url."""
    headers = _get_headers(
        'Content-Type', 'Accept-Encoding',
        'Content-Encoding', 'Accept', 'User-Agent',
        'Content-MD5', 'Transfer-Encoding',
        'Cookie'
    )
    response = requests.patch(
        '%s/%s' % (setting.PROXY_URL_PREFIX, url),
        data=request.data,
        headers=headers
    )
    logging.debug(
        'proxy %s response: %s',
        url, response.text
    )
    return utils.make_json_response(
        response.status_code, _get_response_json(response)
    )


@app.route("/proxy/<path:url>", methods=['DELETE'])
@log_user_action
@login_required
@update_user_token
def proxy_delete(url):
    """proxy url."""
    headers = _get_headers(
        'Content-Type', 'Accept-Encoding',
        'Content-Encoding', 'Accept', 'User-Agent',
        'Content-MD5', 'Transfer-Encoding',
        'Cookie'
    )
    response = requests.delete(
        '%s/%s' % (setting.PROXY_URL_PREFIX, url),
        headers=headers
    )
    logging.debug(
        'proxy %s response: %s',
        url, response.text
    )
    return utils.make_json_response(
        response.status_code, _get_response_json(response)
    )


def init():
    logging.info('init flask')
    database.init()
    adapter_api.load_adapters()
    metadata_api.load_metadatas()
    adapter_api.load_flavors()


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    init()
    app.run(host='0.0.0.0')
