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
import logging
import simplejson as json

from flask import Blueprint
from flask import request

from flask.ext.restful import Resource

from compass.api.exception import BadRequest
from compass.api.exception import Forbidden
from compass.api.exception import ItemNotFound
from compass.api.exception import Unauthorized
from compass.api.restfulAPI import CompassApi
from compass.api import utils

from compass.db import db_api
from compass.db.exception import InvalidParameter
from compass.db.exception import RecordNotExists


v1_app = Blueprint('v1_app', __name__)
api = CompassApi(v1_app)
PREFIX = '/v1.0'


@v1_app.route('/users', methods=['GET'])
def list_users():
    """List details of all users filtered by user email and admin role."""

    emails = request.args.getlist('email')
    is_admin = request.args.get('admin')
    filters = {}

    if emails:
        filters['email'] = emails

    if is_admin is not None:
        if is_admin == 'true':
            filters['is_admin'] = True
        elif is_admin == 'false':
            filters['is_admin'] = False

    users_list = db_api.user.list_users(filters)

    return utils.make_json_response(200, users_list)


class User(Resource):
    ENDPOINT = PREFIX + '/users'

    def get(self, user_id):
        """Get user's information for the specified ID."""
        try:
            user_data = db_api.user.get_user(user_id)
            logging.debug("user_data is===>%s", user_data)

        except RecordNotExists as ex:
            error_msg = ex.message
            raise ItemNotFound(error_msg)

        return utils.make_json_response(200, user_data)


class Adapter(Resource):
    ENDPOINT = PREFIX + "/adapters"

    def get(self, adapter_id):
        """Get information for a specified adapter."""

        try:
            adapter_info = db_api.adapter.get_adapter(adapter_id)
        except RecordNotExists as ex:
            error_msg = ex.message
            raise ItemNotFound(error_msg)

        return utils.make_json_response(200, adapter_info)


@v1_app.route('/adapters', methods=['GET'])
def list_adapters():
    """List details of all adapters filtered by the adapter name(s)."""

    names = request.args.getlist('name')
    filters = {}
    if names:
        filters['name'] = names

    adapters_list = db_api.adapter.list_adapters(filters)
    return utils.make_json_response(200, adapters_list)


@v1_app.route('/adapters/<int:adapter_id>/config-schema', methods=['GET'])
def get_adapter_config_schema(adapter_id):
    """Get the config schema for a specified adapter."""

    os_id = request.args.get("os-id", type=int)

    try:
        schema = db_api.adapter.get_adapter_config_schema(adapter_id, os_id)
    except RecordNotExists as ex:
        raise ItemNotFound(ex.message)

    return utils.make_json_response(200, schema)


@v1_app.route('/adapters/<int:adapter_id>/roles', methods=['GET'])
def get_adapter_roles(adapter_id):
    """Get roles for a specified adapter."""

    try:
        roles = db_api.adapter.get_adapter(adapter_id, True)
    except RecordNotExists as ex:
        raise ItemNotFound(ex.message)

    return utils.make_json_response(200, roles)


class Cluster(Resource):
    def get(self, cluster_id):
        """Get information for a specified cluster."""

        try:
            cluster_info = db_api.cluster.get_cluster(cluster_id)

        except RecordNotExists as ex:
            error_msg = ex.message
            raise ItemNotFound(error_msg)

        return utils.make_json_response(200, cluster_info)


@v1_app.route('/clusters/<int:cluster_id>/config', methods=['PUT', 'PATCH'])
def add_cluster_config(cluster_id):
    """Update the config information for a specified cluster."""
    config = json.loads(request.data)
    if not config:
        raise BadRequest("Config cannot be None!")

    root_elems = ['os_config', 'package_config']
    if len(config.keys()) != 1 or config.keys()[0] not in root_elems:
        error_msg = ("Config root elements must be either"
                     "'os_config' or 'package_config'")
        raise BadRequest(error_msg)

    result = None
    is_patch_method = request.method == 'PATCH'
    try:
        if "os_config" in config:
            result = db_api.cluster\
                           .update_cluster_config(cluster_id,
                                                  'os_config',
                                                  config,
                                                  patch=is_patch_method)
        elif "package_config" in config:
            result = db_api.cluster\
                           .update_cluster_config(cluster_id,
                                                  'package_config', config,
                                                  patch=is_patch_method)

    except InvalidParameter as ex:
        raise BadRequest(ex.message)

    except RecordNotExists as ex:
        raise ItemNotFound(ex.message)

    return utils.make_json_response(200, result)


api.add_resource(User,
                 '/users',
                 '/users/<int:user_id>')
api.add_resource(Adapter,
                 '/adapters',
                 '/adapters/<int:adapter_id>')
api.add_resource(Cluster,
                 '/clusters',
                 '/clusters/<int:cluster_id>')


@v1_app.errorhandler(ItemNotFound)
def handle_not_exist(error, failed_objs=None):
    """Handler of ItemNotFound Exception."""

    message = {'type': 'itemNotFound',
               'message': error.message}

    if failed_objs and isinstance(failed_objs, dict):
        message.update(failed_objs)

    return utils.make_json_response(404, message)


@v1_app.errorhandler(Unauthorized)
def handle_invalid_user(error, failed_objs=None):
    """Handler of Unauthorized Exception."""

    message = {'type': 'unathorized',
               'message': error.message}

    if failed_objs and isinstance(failed_objs, dict):
        message.update(failed_objs)

    return utils.make_json_response(401, message)


@v1_app.errorhandler(Forbidden)
def handle_no_permission(error, failed_objs=None):
    """Handler of Forbidden Exception."""

    message = {'type': 'Forbidden',
               'message': error.message}

    if failed_objs and isinstance(failed_objs, dict):
        message.update(failed_objs)

    return utils.make_json_response(403, message)


@v1_app.errorhandler(BadRequest)
def handle_bad_request(error, failed_objs=None):
    """Handler of badRequest Exception."""

    message = {'type': 'badRequest',
               'message': error.message}

    if failed_objs and isinstance(failed_objs, dict):
        message.update(failed_objs)

    return utils.make_json_response(400, message)


if __name__ == '__main__':
    v1_app.run(debug=True)
