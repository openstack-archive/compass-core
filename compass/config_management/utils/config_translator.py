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

"""Config Translator module to translate orign config to dest config.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import logging

from compass.config_management.utils import config_reference
from compass.utils import util


class KeyTranslator(object):
    """Class to translate origin ref to dest ref."""

    def __init__(self, translated_keys=[], from_keys={}, translated_value=None,
                 from_values={}, override=False, override_conditions={}):
        """Constructor

        :param translated_keys: keys in dest ref to be translated to.
        :type translated_keys: callable or list of (str or callable)
        :param from_keys: extra kwargs parsed to translated key callback.
        :type: from_keys: dict mapping name of kwargs to path in origin ref
        :param translated_value: value or callback to get translated value.
        :type translated_value: callback or any type
        :param from_values: extra kwargs parsed to translated value callback.
        :type from_vlaues: dictr mapping name of kwargs to path in origin ref.
        :param override: if the translated value can be overridden.
        :type override: callback or bool
        :param override_conditions: extra kwargs parsed to override callback.
        :type override_conditions: dict of kwargs name to origin ref path.
        """
        self.translated_keys_ = translated_keys
        self.from_keys_ = from_keys
        self.translated_value_ = translated_value
        self.from_values_ = from_values
        self.override_ = override
        self.override_conditions_ = override_conditions
        self._is_valid()

    def __repr__(self):
        return (
            '%s[translated_keys=%s,from_keys=%s,translated_value=%s,'
            'from_values=%s,override=%s,override_conditions=%s]'
        ) % (
            self.__class__.__name__, self.translated_keys_,
            self.from_keys_, self.translated_value_, self.from_values_,
            self.override_, self.override_conditions_
        )

    def _is_valid_translated_keys(self):
        """Check translated keys are valid."""
        if callable(self.translated_keys_):
            return

        for i, translated_key in enumerate(self.translated_keys_):
            if util.is_instance(translated_key, [str, unicode]):
                if '*' in translated_key:
                    raise KeyError(
                        'transalted_keys[%d] %s should not contain *' % (
                            i, translated_key))
            elif not callable(translated_key):
                raise TypeError(
                    'translated_keys[%d] type is %s while expected '
                    'types are str or callable: %s' % (
                        i, type(translated_key), translated_key))

    def _is_valid_from_keys(self):
        """Check from keys are valid."""
        for mapping_key, from_key in self.from_keys_.items():
            if not util.is_instance(from_key, [str, unicode]):
                raise TypeError(
                    'from_keys[%s] type is %s while '
                    'expected type is [str, unicode]: %s' % (
                        mapping_key, type(from_key), from_key))

            if '*' in from_key:
                raise KeyError(
                    'from_keys[%s] %s contains *' % (
                        mapping_key, from_key))

    def _is_valid_from_values(self):
        """Check from values are valid."""
        for mapping_key, from_value in self.from_values_.items():
            if not util.is_instance(from_value, [str, unicode]):
                raise TypeError(
                    'from_values[%s] type is %s while '
                    'expected type is [str, unicode]: %s' % (
                        mapping_key, type(from_value), from_value))

            if '*' in from_value:
                raise KeyError(
                    'from_values[%s] %s contains *' % (
                        mapping_key, from_value))

    def _is_valid_override_conditions(self):
        """Check override conditions are valid."""
        override_items = self.override_conditions_.items()
        for mapping_key, override_condition in override_items:
            if not util.is_instance(override_condition, [str, unicode]):
                raise TypeError(
                    'override_conditions[%s] type is %s '
                    'while expected type is [str, unicode]: %s' % (
                        mapping_key, type(override_condition),
                        override_condition))

            if '*' in override_condition:
                raise KeyError(
                    'override_conditions[%s] %s contains *' % (
                        mapping_key, override_condition))

    def _is_valid(self):
        """Check key translator is valid."""
        self._is_valid_translated_keys()
        self._is_valid_from_keys()
        self._is_valid_from_values()
        self._is_valid_override_conditions()

    def _get_translated_keys(self, ref_key, sub_ref):
        """Get translated keys."""
        key_configs = {}
        for mapping_key, from_key in self.from_keys_.items():
            if from_key in sub_ref:
                key_configs[mapping_key] = sub_ref[from_key]
            else:
                logging.error('%s from_key %s missing in %s',
                              self, from_key, sub_ref)

        if callable(self.translated_keys_):
            translated_keys = self.translated_keys_(
                sub_ref, ref_key, **key_configs)
            return translated_keys

        translated_keys = []
        for translated_key in self.translated_keys_:
            if callable(translated_key):
                translated_key = translated_key(
                    sub_ref, ref_key, **key_configs)

            if not translated_key:
                logging.debug('%s ignore empty translated key', self)
                continue

            if not util.is_instance(translated_key, [str, unicode]):
                logging.error(
                    '%s translated key %s should be [str, unicode]',
                    self, translated_key)
                continue

            translated_keys.append(translated_key)

        return translated_keys

    def _get_translated_value(self, ref_key, sub_ref,
                              translated_key, translated_sub_ref):
        """Get translated value."""
        if self.translated_value_ is None:
            return sub_ref.config
        elif not callable(self.translated_value_):
            return self.translated_value_

        value_configs = {}

        for mapping_key, from_value in self.from_values_.items():
            if from_value in sub_ref:
                value_configs[mapping_key] = sub_ref[from_value]
            else:
                logging.info('%s ignore from value %s for key %s',
                             self, from_value, ref_key)

        return self.translated_value_(
            sub_ref, ref_key, translated_sub_ref,
            translated_key, **value_configs)

    def _get_override(self, ref_key, sub_ref,
                      translated_key, translated_sub_ref):
        """Get override."""
        if not callable(self.override_):
            return self.override_

        override_condition_configs = {}
        override_items = self.override_conditions_.items()
        for mapping_key, override_condition in override_items:
            if override_condition in sub_ref:
                override_condition_configs[mapping_key] = (
                    sub_ref[override_condition])
            else:
                logging.error('%s no override condition %s in %s',
                              self, override_condition, ref_key)

        return self.override_(sub_ref, ref_key,
                              translated_sub_ref,
                              translated_key,
                              **override_condition_configs)

    def translate(self, ref, key, translated_ref):
        """Translate content in ref[key] to translated_ref."""
        for ref_key, sub_ref in ref.ref_items(key):
            translated_keys = self._get_translated_keys(ref_key, sub_ref)
            for translated_key in translated_keys:
                translated_sub_ref = translated_ref.setdefault(
                    translated_key)
                translated_value = self._get_translated_value(
                    ref_key, sub_ref, translated_key, translated_sub_ref)

                if translated_value is None:
                    continue

                override = self._get_override(
                    ref_key, sub_ref, translated_key, translated_sub_ref)
                logging.debug('%s translate to %s value %s', ref_key,
                              translated_key, translated_value)
                translated_sub_ref.update(translated_value, override)


class ConfigTranslator(object):
    """Class to translate origin config to expected dest config."""

    def __init__(self, mapping):
        """Constructor

        :param mapping: dict of config path to :class:`KeyTranslator` instance
        """
        self.mapping_ = mapping
        self._is_valid()

    def __repr__(self):
        return '%s[mapping=%s]' % (self.__class__.__name__, self.mapping_)

    def _is_valid(self):
        """Check if ConfigTranslator is valid."""
        if not isinstance(self.mapping_, dict):
            raise TypeError(
                'mapping type is %s while expected type is dict: %s' % (
                    type(self.mapping_), self.mapping_))

        for key, values in self.mapping_.items():
            if not isinstance(values, list):
                msg = 'mapping[%s] type is %s while expected type is list: %s'
                raise TypeError(msg % (key, type(values), values))

            for i, value in enumerate(values):
                if not isinstance(value, KeyTranslator):
                    msg = (
                        'mapping[%s][%d] type is %s '
                        'while expected type is KeyTranslator: %s')
                    raise TypeError(msg % (key, i, type(value), value))

    def translate(self, config):
        """Translate config.

        :param config: configuration to translate.

        :returns: the translated configuration.
        """
        ref = config_reference.ConfigReference(config)
        translated_ref = config_reference.ConfigReference({})
        for key, values in self.mapping_.items():
            for value in values:
                value.translate(ref, key, translated_ref)

        translated_config = config_reference.get_clean_config(
            translated_ref.config)
        logging.debug('translate config\n%s\nto\n%s',
                      config, translated_config)
        return translated_config
