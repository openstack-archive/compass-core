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


class ItemNotFound(Exception):
    """Define the exception for referring non-existing object."""
    def __init__(self, message):
        super(ItemNotFound, self).__init__(message)
        self.message = message

    def __str__(self):
        return repr(self.message)


class BadRequest(Exception):
    """Define the exception for invalid/missing parameters or a user makes
       a request in invalid state and cannot be processed at this moment.
    """
    def __init__(self, message):
        super(BadRequest, self).__init__(message)
        self.message = message

    def __str__(self):
        return repr(self.message)


class Unauthorized(Exception):
    """Define the exception for invalid user login."""
    def __init__(self, message):
        super(Unauthorized, self).__init__(message)
        self.message = message

    def __str__(self):
        return repr(self.message)


class UserDisabled(Exception):
    """Define the exception that a disabled user tries to do some operations.
    """
    def __init__(self, message):
        super(UserDisabled, self).__init__(message)
        self.message = message

    def __str__(self):
        return repr(self.message)


class Forbidden(Exception):
    """Define the exception that a user tries to do some operations without
       valid permissions.
    """
    def __init__(self, message):
        super(Forbidden, self).__init__(message)
        self.message = message

    def __str__(self):
        return repr(self.message)


class BadMethod(Exception):
    """Define the exception for invoking unsupprted or unimplemented methods.
    """
    def __init__(self, message):
        super(BadMethod, self).__init__(message)
        self.message = message

    def __str__(self):
        return repr(self.message)


class ConflictObject(Exception):
    """Define the exception for creating an existing object."""
    def __init__(self, message):
        super(ConflictObject, self).__init__(message)
        self.message = message

    def __str__(self):
        return repr(self.message)
