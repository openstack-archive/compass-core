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

"""Exceptions for RESTful API."""
import logging
import simplejson as json
import traceback

from compass.api import app
from compass.api import utils


class HTTPException(Exception):
    def __init__(self, message, status_code):
        super(HTTPException, self).__init__(message)
        self.traceback = traceback.format_exc()
        self.status_code = status_code


class ItemNotFound(HTTPException):
    """Define the exception for referring non-existing object."""
    def __init__(self, message):
        super(ItemNotFound, self).__init__(message, 410)


class BadRequest(HTTPException):
    """Define the exception for invalid/missing parameters or a user makes
       a request in invalid state and cannot be processed at this moment.
    """
    def __init__(self, message):
        super(BadRequest, self).__init__(message, 400)


class Unauthorized(HTTPException):
    """Define the exception for invalid user login."""
    def __init__(self, message):
        super(Unauthorized, self).__init__(message, 401)


class UserDisabled(HTTPException):
    """Define the exception that a disabled user tries to do some operations.
    """
    def __init__(self, message):
        super(UserDisabled, self).__init__(message, 403)


class Forbidden(HTTPException):
    """Define the exception that a user tries to do some operations without
       valid permissions.
    """
    def __init__(self, message):
        super(Forbidden, self).__init__(message, 403)


class BadMethod(HTTPException):
    """Define the exception for invoking unsupprted or unimplemented methods.
    """
    def __init__(self, message):
        super(BadMethod, self).__init__(message, 405)


class ConflictObject(HTTPException):
    """Define the exception for creating an existing object."""
    def __init__(self, message):
        super(ConflictObject, self).__init__(message, 409)


@app.errorhandler(Exception)
def handle_exception(error):
    response = {'message': str(error)}
    if hasattr(error, 'traceback'):
        response['traceback'] = error.traceback

    status_code = 400
    if hasattr(error, 'status_code'):
        status_code = error.status_code

        return utils.make_json_response(status_code, response)
