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

"""Custom exception"""


class RecordNotExists(Exception):
    """Define the exception for referring non-existing object in DB."""
    def __init__(self, message):
        super(RecordNotExists, self).__init__(message)
        self.message = message


class DuplicatedRecord(Exception):
    """Define the exception for trying to insert an existing object in DB."""
    def __init__(self, message):
        super(DuplicatedRecord, self).__init__(message)
        self.message = message


class Forbidden(Exception):
    """Define the exception that a user is trying to make some action
       without the right permission.
    """
    def __init__(self, message):
        super(Forbidden, self).__init__(message)
        self.message = message


class InvalidParameter(Exception):
    """Define the exception that the request has invalid or missing parameters.
    """
    def __init__(self, message):
        super(InvalidParameter, self).__init__(message)
        self.message = message
