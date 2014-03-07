# Copyright 2014 Openstack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""callback lib for config translator callbacks."""
import crypt
import logging
import re

from compass.utils import util


def get_key_from_pattern(
    _ref, path, from_pattern='.*',
    to_pattern='', **kwargs
):
    """Get translated key from pattern."""
    match = re.match(from_pattern, path)
    if not match:
        return None
    group = match.groupdict()
    util.merge_dict(group, kwargs)
    try:
        translated_key = to_pattern % group
    except Exception as error:
        logging.error('failed to get translated key from %s %% %s',
                      to_pattern, group)
        raise error
    return translated_key


def get_keys_from_role_mapping(ref, _path, mapping={}, **_kwargs):
    """get translated keys from roles."""
    roles = ref.config
    translated_keys = []
    for role in roles:
        if role not in mapping:
            continue

        translated_keys.extend(mapping[role].keys())

    logging.debug('got translated_keys %s from roles %s and mapping %s',
                  translated_keys, roles, mapping)
    return translated_keys


def get_value_from_role_mapping(
    ref, _path, _translated_ref, translated_path,
    mapping={}, **_kwargs
):
    """get translated value from roles and translated_path."""
    roles = ref.config
    for role in roles:
        if role not in mapping:
            continue

        if translated_path not in mapping[role]:
            continue

        value = mapping[role][translated_path]
        translated_value = ref.get(value)
        logging.debug('got translated_value %s from %s and roles %s',
                      translated_value, roles, translated_path)
        return translated_value

    return None


def get_encrypted_value(ref, _path, _translated_ref, _translated_path,
                        crypt_method=None, **_kwargs):
    """Get encrypted value."""
    if not crypt_method:
        if hasattr(crypt, 'METHOD_MD5'):
            crypt_method = crypt.METHOD_MD5
        else:
            # for python2.7, copy python2.6 METHOD_MD5 logic here.
            from random import choice
            import string

            _saltchars = string.ascii_letters + string.digits + './'

            def _mksalt():
                """generate salt."""
                salt = '$1$'
                salt += ''.join(choice(_saltchars) for _ in range(8))
                return salt

            crypt_method = _mksalt()

    return crypt.crypt(ref.config, crypt_method)


def get_value_if(ref, _path, _translated_ref, _translated_path,
                 condition=False, **_kwargs):
    """Get value if condition is true."""
    if not condition:
        return None
    return ref.config


def add_value(ref, _path, translated_ref,
              _translated_path, condition='', **_kwargs):
    """Append value into translated config if condition."""
    if not translated_ref.config:
        value_list = []
    else:
        value_list = [
            value for value in translated_ref.config.split(',') if value
        ]

    if condition and ref.config not in value_list:
        value_list.append(ref.config)

    return ','.join(value_list)


def override_if_any(_ref, _path, _translated_ref, _translated_path, **kwargs):
    """override if any kwargs is True."""
    return any(kwargs.values())


def override_if_all(_ref, _path, _translated_ref, _translated_path, **kwargs):
    """override if all kwargs are True."""
    return all(kwargs.values())


def override_path_has(_ref, path, _translated_ref, _translated_path,
                      should_exist='', **_kwargs):
    """override if expect part exists in path."""
    return should_exist in path.split('/')
