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

"""Utils for database usage."""
import copy
from functools import wraps


def wrap_to_dict(support_keys=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            obj = func(*args, **kwargs)
            obj_info = None
            if isinstance(obj, list):
                obj_info = [_wrapper_dict(o, support_keys) for o in obj]
            else:
                obj_info = _wrapper_dict(obj, support_keys)

            return obj_info
        return wrapper
    return decorator


def _wrapper_dict(data, support_keys=None):
    """Helper for warpping db object into dictionaryi."""
    if support_keys is None:
        return data

    info = {}
    for key in support_keys:
        if key in data:
            info[key] = data[key]

    return info


def merge_dict(lhs, rhs, override=True):
    """Merge nested right dict into left nested dict recursively.

:param lhs: dict to be merged into.
:type lhs: dict
:param rhs: dict to merge from.
:type rhs: dict
:param override: the value in rhs overide the value in left if True.
:type override: str

:raises: TypeError if lhs or rhs is not a dict.
"""
    if not rhs:
        return

    if not isinstance(lhs, dict):
        raise TypeError('lhs type is %s while expected is dict' % type(lhs),
                        lhs)

    if not isinstance(rhs, dict):
        raise TypeError('rhs type is %s while expected is dict' % type(rhs),
                        rhs)

    for key, value in rhs.items():
        if (
            isinstance(value, dict) and key in lhs and
            isinstance(lhs[key], dict)
        ):
            merge_dict(lhs[key], value, override)
        else:
            if override or key not in lhs:
                lhs[key] = copy.deepcopy(value)
