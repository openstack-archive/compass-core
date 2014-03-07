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

"""Module to filter configuration when upddating.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import logging

from compass.config_management.utils import config_reference


class ConfigFilter(object):
    """config filter based on allows and denies rules."""

    def __init__(self, allows=['*'], denies=[]):
        """Constructor

        :param allows: glob path to copy to the filtered configuration.
        :type allows: list of str
        :param denies: glob path to remove from the filtered configuration.
        :type denies: list of str
        """
        self.allows_ = allows
        self.denies_ = denies
        self._is_valid()

    def __repr__(self):
        return '%s[allows=%s,denies=%s]' % (
            self.__class__.__name__, self.allows_, self.denies_)

    def _is_allows_valid(self):
        """Check if allows are valid."""
        if not isinstance(self.allows_, list):
            raise TypeError(
                'allows type is %s but expected type is list: %s' % (
                    type(self.allows_), self.allows_))

        for i, allow in enumerate(self.allows_):
            if not isinstance(allow, str):
                raise TypeError(
                    'allows[%s] type is %s but expected type is str: %s' % (
                        i, type(allow), allow))

    def _is_denies_valid(self):
        """Check if denies are valid."""
        if not isinstance(self.denies_, list):
            raise TypeError(
                'denies type is %s but expected type is list: %s' % (
                    type(self.denies_), self.denies_))

        for i, deny in enumerate(self.denies_):
            if not isinstance(deny, str):
                raise TypeError(
                    'denies[%s] type is %s but expected type is str: %s' % (
                        i, type(deny), deny))

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
        for allow in self.allows_:
            if not allow:
                continue

            logging.debug('filter by allow rule %s', allow)
            for sub_key, sub_ref in ref.ref_items(allow):
                logging.debug('%s is added to filtered config', sub_key)
                filtered_ref.setdefault(sub_key).update(sub_ref.config)

    def _filter_denies(self, filtered_ref):
        """remove config from filter_ref by denies."""
        for deny in self.denies_:
            if not deny:
                continue

            logging.debug('filter by deny rule %s', deny)
            for ref_key in filtered_ref.ref_keys(deny):
                logging.debug('%s is removed from filtered config', ref_key)
                del filtered_ref[ref_key]
