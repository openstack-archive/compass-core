# Copyright 2014 Huawei Technologies Co. Ltd
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
    except KeyError as error:
        logging.error('failed to get translated key from %s %% %s',
                      to_pattern, group)
        raise error

    logging.debug('got translated key %s for %s', translated_key, path)
    return translated_key


def get_keys_from_config_mapping(ref, _path, **kwargs):
    """get translated keys from config."""
    config = ref.config
    translated_keys = config.keys()
    logging.debug('got translated_keys %s from config mapping %s',
                  translated_keys, config)
    return translated_keys


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


def get_value_from_config_mapping(
    ref, _path, _translated_ref, translated_path, **kwargs
):
    """get translated_value from config and translated_path."""
    config = ref.config
    if translated_path not in config:
        return None

    value = config[translated_path]
    if isinstance(value, basestring):
        translated_value = ref.get(value)
        logging.debug('got translated_value %s from %s',
                      translated_value, value)
    elif isinstance(value, list):
        for value_in_list in value:
            translated_value = ref.get(value_in_list)
            logging.debug('got translated_value %s from %s',
                          translated_value, value_in_list)
            if translated_value is not None:
                break

    else:
        logging.error('unexpected type %s: %s',
                      type(value), value)
        translated_value = None

    logging.debug('got translated_value %s from translated_path %s',
                  translated_value, translated_path)
    return translated_value


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
        if isinstance(value, basestring):
            translated_value = ref.get(value)
            logging.debug('got translated_value %s from %s',
                          translated_value, value)
        elif isinstance(value, list):
            for value_in_list in value:
                translated_value = ref.get(value_in_list)
                logging.debug('got translated_value %s from %s',
                              translated_value, value_in_list)
                if translated_value is not None:
                    break
        else:
            logging.error('unexpected type %s: %s',
                          type(value), value)
            translated_value = None

        logging.debug('got translated_value %s from roles %s '
                      'and translated_path %s',
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


def set_value(ref, _path, _translated_ref,
              _translated_path,
              return_value_callback=None, **kwargs):
    """Set value into translated config."""
    condition = True
    for _, arg in kwargs.items():
        if not arg:
            condition = False

    if condition:
        translated_value = ref.config
    else:
        translated_value = None

    if not return_value_callback:
        return translated_value
    else:
        return return_value_callback(translated_value)


def add_value(ref, _path, translated_ref,
              translated_path,
              get_value_callback=None,
              check_value_callback=None,
              add_value_callback=None,
              return_value_callback=None, **kwargs):
    """Append value into translated config."""
    if not translated_ref.config:
        value_list = []
    else:
        if not get_value_callback:
            value_list = translated_ref.config
        else:
            value_list = get_value_callback(translated_ref.config)

    logging.debug('%s value list is %s', translated_path, value_list)
    if not isinstance(value_list, list):
        raise TypeError(
            '%s value %s type %s but expected type is list' % (
                translated_path, value_list, type(value_list)))

    condition = True
    for _, arg in kwargs.items():
        if not arg:
            condition = False

    logging.debug('%s add_value condition is %s', translated_path, condition)
    if condition:
        if not check_value_callback:
            value_in_list = ref.config in value_list
        else:
            value_in_list = check_value_callback(ref.config, value_list)

        if value_in_list:
            logging.debug('%s found value %s in %s',
                          translated_path, value_list, value_in_list)

        if not value_in_list:
            if not add_value_callback:
                value_list.append(ref.config)
            else:
                add_value_callback(ref.config, value_list)

    logging.debug('%s value %s after added', translated_path, value_list)
    if not return_value_callback:
        return value_list
    else:
        return return_value_callback(value_list)


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
