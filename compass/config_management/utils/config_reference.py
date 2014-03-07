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

"""Module to provide util class to access item in nested dict easily.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import copy
import fnmatch
import os.path
import re

from compass.utils import util


def get_clean_config(config):
    """Get cleaned config from original config.

    :param config: configuration to be cleaned.

    :returns: clean configuration without key referring to None or empty dict.
    """
    if config is None:
        return None

    if isinstance(config, dict):
        extracted_config = {}
        for key, value in config.items():
            sub_config = get_clean_config(value)
            if sub_config is not None:
                extracted_config[key] = sub_config

        if not extracted_config:
            return None

        return extracted_config
    else:
        return config


class ConfigReference(object):
    """Helper class to acess item in nested dict."""

    def __init__(self, config, parent=None, parent_key=None):
        """Construct ConfigReference from configuration.

        :param config: configuration to build the ConfigRerence instance.
        :type config: dict
        :param parent: parent ConfigReference instance.
        :param parent_key: the key refers to the config in parent.
        :type parent_key: str

        :raises: TypeError
        """
        if parent and not isinstance(parent, self.__class__):
            raise TypeError('parent %s type should be %s'
                            % (parent, self.__class__.__name__))\

        if parent_key and not util.is_instance(parent_key, [str, unicode]):
            raise TypeError('parent_key %s type should be [str, unicode]'
                            % parent_key)

        self.config = config
        self.refs_ = {'.': self}
        self.parent_ = parent
        self.parent_key_ = parent_key
        if parent is not None:
            self.refs_['..'] = parent
            self.refs_['/'] = parent.refs_['/']
            parent.refs_[parent_key] = self
            if parent.config is None or not isinstance(parent.config, dict):
                parent.__init__({}, parent=parent.parent_,
                                parent_key=parent.parent_key_)

            parent.config[parent_key] = self.config
        else:
            self.refs_['..'] = self
            self.refs_['/'] = self

        if config and isinstance(config, dict):
            for key, value in config.items():
                if not util.is_instance(key, [str, unicode]):
                    msg = 'key type is %s while expected is [str, unicode]: %s'
                    raise TypeError(msg % (type(key), key))
                ConfigReference(value, self, key)

    def items(self, prefix=''):
        """Return key value pair of all nested items.

        :param prefix: iterate key value pair under prefix.
        :type prefix: str

        :returns: list of (key, value)
        """
        to_list = []
        for key, ref in self.refs_.items():
            if not self._special_path(key):
                key_prefix = os.path.join(prefix, key)
                to_list.append((key_prefix, ref.config))
                to_list.extend(ref.items(key_prefix))
        return to_list

    def keys(self):
        """Return keys of :func:`ConfigReference.items`."""
        return [key for key, _ in self.items()]

    def values(self):
        """Return values of :func:`ConfigReference.items`."""
        return [ref for _, ref in self.items()]

    def __nonzero__(self):
        return bool(self.config)

    def __iter__(self):
        return iter(self.keys())

    def __len__(self):
        return len(self.keys())

    @classmethod
    def _special_path(cls, path):
        """Check if path is special."""
        return path in ['/', '.', '..']

    def ref_items(self, path):
        """Return the refs matching the path glob.

        :param path: glob pattern to match the path to the ref.
        :type path: str

        :returns: dict of key to :class:`ConfigReference` instance.
        :raises: KeyError
        """
        if not path:
            raise KeyError('key %s is empty' % path)

        parts = []

        if util.is_instance(path, [str, unicode]):
            parts = path.split('/')
        else:
            parts = path

        if not parts[0]:
            parts = parts[1:]
            refs = [('/', self.refs_['/'])]
        else:
            refs = [('', self)]

        for part in parts:
            if not part:
                continue

            next_refs = []
            for prefix, ref in refs:
                if self._special_path(part):
                    sub_prefix = os.path.join(prefix, part)
                    next_refs.append((sub_prefix, ref.refs_[part]))
                    continue

                for sub_key, sub_ref in ref.refs_.items():
                    if self._special_path(sub_key):
                        continue

                    matched = fnmatch.fnmatch(sub_key, part)
                    if not matched:
                        continue

                    sub_prefix = os.path.join(prefix, sub_key)
                    next_refs.append((sub_prefix, sub_ref))

            refs = next_refs

        return refs

    def ref_keys(self, path):
        """Return keys of :func:`ConfigReference.ref_items`."""
        return [key for key, _ in self.ref_items(path)]

    def ref_values(self, path):
        """Return values of :func:`ConfigReference.ref_items`."""
        return [ref for _, ref in self.ref_items(path)]

    def ref(self, path, create_if_not_exist=False):
        """Get ref of the path.

        :param path: str. The path to the ref.
        :type path: str
        :param create_if_not_exists: create ref if does not exist on path.
        :type create_if_not_exist: bool

        :returns: :class:`ConfigReference` instance to the path.

        :raises: KeyError, TypeError
        """
        if not path:
            raise KeyError('key %s is empty' % path)

        if '*' in path or '?' in path:
            raise TypeError('key %s should not contain *')

        parts = []
        if isinstance(path, list):
            parts = path
        else:
            parts = path.split('/')

        if not parts[0]:
            ref = self.refs_['/']
            parts = parts[1:]
        else:
            ref = self

        for part in parts:
            if not part:
                continue

            if part in ref.refs_:
                ref = ref.refs_[part]
            elif create_if_not_exist:
                ref = ConfigReference(None, ref, part)
            else:
                raise KeyError('key %s is not exist' % path)

        return ref

    def __repr__(self):
        return '<ConfigReference: config=%r, refs[%s], parent=%s>' % (
            self.config, self.refs_.keys(), self.parent_)

    def __getitem__(self, path):
        return self.ref(path).config

    def __contains__(self, path):
        try:
            self.ref(path)
            return True
        except KeyError:
            return False

    def __setitem__(self, path, value):
        ref = self.ref(path, True)
        ref.__init__(value, ref.parent_, ref.parent_key_)
        return ref.config

    def __delitem__(self, path):
        ref = self.ref(path)
        if ref.parent_:
            del ref.parent_.refs_[ref.parent_key_]
            del ref.parent_.config[ref.parent_key_]
        ref.__init__(None)

    def update(self, config, override=True):
        """Update with config.

        :param config: config to update.
        :param override: if the instance config should be overrided
        :type override: bool
        """
        if (self.config is not None and
                isinstance(self.config, dict) and
                isinstance(config, dict)):

            util.merge_dict(self.config, config, override)
        elif self.config is None or override:
            self.config = copy.deepcopy(config)
        else:
            return

        self.__init__(self.config, self.parent_, self.parent_key_)

    def get(self, path, default=None):
        """Get config of the path or default if does not exist.

        :param path: path to the item
        :type path: str
        :param default: default value to return

        :returns: item in path or default.
        """
        try:
            return self[path]
        except KeyError:
            return default

    def setdefault(self, path, value=None):
        """Set default value to path.

        :param path: path to the item.
        :type path: str
        :param value: the default value to set to the path.

        :returns: the :class:`ConfigReference` to path
        """
        ref = self.ref(path, True)
        if ref.config is None:
            ref.__init__(value, ref.parent_, ref.parent_key_)
        return ref

    def match(self, properties_match):
        """Check if config match the given properties."""
        for property_name, property_value in properties_match.items():
            config_value = self.get(property_name)
            if config_value is None:
                return False

            if isinstance(config_value, list):
                found = False
                for config_value_item in config_value:
                    if re.match(property_value, str(config_value_item)):
                        found = True

                if not found:
                    return False

            else:
                if not re.match(property_value, str(config_value)):
                    return False

        return True

    def filter(self, properties_name):
        """filter config by properties name."""
        filtered_properties = {}
        for property_name in properties_name:
            config_value = self.get(property_name)
            if config_value is None:
                continue

            filtered_properties[property_name] = config_value

        return filtered_properties
