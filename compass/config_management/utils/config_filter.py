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

"""Module to filter configuration when upddating.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import logging

from compass.config_management.utils import config_reference


class AllowRule(object):
    """class to define allow rule."""

    def __init__(self, check=None):
        self.check_ = check

    def allow(self, key, ref):
        """Check if the ref is OK to add to filtered config."""
        if not self.check_:
            return True
        else:
            return self.check_(key, ref)


class DenyRule(object):
    def __init__(self, check=None):
        self.check_ = check

    def deny(self, key, ref):
        """Check if the ref is OK to del from filtered config."""
        if not self.check_:
            return True
        else:
            return self.check_(key, ref)


class ConfigFilter(object):
    """config filter based on allows and denies rules."""

    def __init__(self, allows={'*': AllowRule()}, denies={}):
        """Constructor

        :param allows: dict of glob path and allow rule to copy to the
                       filtered configuration.
        :type allows: dict of str to AllowRule
        :param denies: dict of glob path and deny rule to remove from
                       the filtered configuration.
        :type denies: dict of str to DenyRule
        """
        self.allows_ = allows
        self.denies_ = denies
        self._is_valid()

    def __repr__(self):
        return '%s[allows=%s,denies=%s]' % (
            self.__class__.__name__, self.allows_, self.denies_)

    def _is_allows_valid(self):
        """Check if allows are valid."""
        if not isinstance(self.allows_, dict):
            raise TypeError(
                'allows type is %s but expected type is dict: %s' % (
                    type(self.allows_), self.allows_))

        for allow_key, allow_rule in self.allows_.items():
            if not isinstance(allow_key, basestring):
                raise TypeError(
                    'allow_key %s type is %s but expected type '
                    'is str or unicode' % (allow_key, type(allow_rule)))

            if not isinstance(allow_rule, AllowRule):
                raise TypeError(
                    'allows[%s] %s type is %s but expected type '
                    'is AllowRule' % (
                        allow_key, allow_rule, type(allow_rule)))

    def _is_denies_valid(self):
        """Check if denies are valid."""
        if not isinstance(self.denies_, dict):
            raise TypeError(
                'denies type is %s but expected type is dict: %s' % (
                    type(self.denies_), self.denies_))

        for deny_key, deny_rule in self.denies_.items():
            if not isinstance(deny_key, basestring):
                raise TypeError(
                    'deny_key %s type is %s but expected type '
                    'is str or unicode: %s' % (
                        deny_key, deny_rule, type(deny_rule)))

            if not isinstance(deny_rule, DenyRule):
                raise TypeError(
                    'denies[%s] %s type is %s but expected type '
                    'is DenyRule' % (deny_key, deny_rule, type(deny_rule)))

    def _is_valid(self):
        """Check if config filter is valid."""
        self._is_allows_valid()
        self._is_denies_valid()

    def filter(self, config):
        """Filter config

        :param config: configuration to filter.
        :type config: dict

        :returns: filtered configuration as dict
        """
        ref = config_reference.ConfigReference(config)
        filtered_ref = config_reference.ConfigReference({})
        self._filter_allows(ref, filtered_ref)
        self._filter_denies(filtered_ref)
        filtered_config = config_reference.get_clean_config(
            filtered_ref.config)
        logging.debug('filter config %s to %s', config, filtered_config)
        return filtered_config

    def _filter_allows(self, ref, filtered_ref):
        """copy ref config with the allows to filtered ref."""
        for allow_key, allow_rule in self.allows_.items():
            logging.debug('filter by allow rule %s', allow_key)
            for sub_key, sub_ref in ref.ref_items(allow_key):
                if allow_rule.allow(sub_key, sub_ref):
                    logging.debug('%s is added to filtered config', sub_key)
                    filtered_ref.setdefault(sub_key).update(sub_ref.config)
                else:
                    logging.debug('%s is ignored to add to filtered config',
                                  sub_key)

    def _filter_denies(self, filtered_ref):
        """remove config from filter_ref by denies."""
        for deny_key, deny_rule in self.denies_.items():
            logging.debug('filter by deny rule %s', deny_key)
            for ref_key, ref in filtered_ref.ref_items(deny_key):
                if deny_rule.deny(ref_key, ref):
                    logging.debug('%s is removed from filtered config',
                                  ref_key)
                    del filtered_ref[ref_key]
                else:
                    logging.debug('%s is ignored to del from filtered config',
                                  ref_key)
