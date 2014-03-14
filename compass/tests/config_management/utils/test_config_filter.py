#!/usr/bin/python
#
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

"""test config_filter module.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import os
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from compass.config_management.utils import config_filter
from compass.utils import flags
from compass.utils import logsetting


class TestConfigFilter(unittest2.TestCase):
    """test config filter class."""

    def setUp(self):
        super(TestConfigFilter, self).setUp()
        logsetting.init()
        self.config_ = {
            '1': '1',
            '2': {
                '22': '22',
                '33': {
                    '333': '333',
                    '44': '444'
                }
            },
            '3': {'33': '44'}
        }

    def tearDown(self):
        super(TestConfigFilter, self).tearDown()

    def test_init(self):
        config_filter.ConfigFilter(
            allows=['abc', 'def'], denies=['def', 'ghi'])
        config_filter.ConfigFilter(
            allows=[u'abc', u'def'], denies=[u'def', u'ghi'])

    def test_init_allows(self):
        # allows type should be a list of string.
        self.assertRaises(
            TypeError, config_filter.ConfigFilter,
            allows={'abd': 'abc'})
        self.assertRaises(
            TypeError, config_filter.ConfigFilter,
            allows='abc')
        self.assertRaises(
            TypeError, config_filter.ConfigFilter,
            allows=[{'abc': 'bdc'}])

    def test_init_denies(self):
        # denies type should be a list of string.
        self.assertRaises(
            TypeError, config_filter.ConfigFilter,
            denies={'abd': 'abc'})
        self.assertRaises(
            TypeError, config_filter.ConfigFilter,
            denies='abc')
        self.assertRaises(
            TypeError, config_filter.ConfigFilter,
            denies=[{'abc': 'bdc'}])

    def test_allows_asterisks(self):
        """test allows rules."""
        # keys in allows will be copied to dest.
        # if '*' in allows, all keys will be copied to dest.
        allows = ['*', '3', '5']
        configfilter = config_filter.ConfigFilter(allows)
        filtered_config = configfilter.filter(self.config_)
        self.assertEqual(filtered_config, self.config_)

    def test_allows_path(self):
        allows = ['/1', '2/22', '5']
        expected_config = {'1': '1', '2': {'22': '22'}}
        configfilter = config_filter.ConfigFilter(allows)
        filtered_config = configfilter.filter(self.config_)
        self.assertEqual(filtered_config, expected_config)

    def test_allows_asterrisks_in_path(self):
        allows = ['*/33']
        expected_config = {'2': {'33': {'333': '333',
                                        '44': '444'}},
                           '3': {'33': '44'}}
        configfilter = config_filter.ConfigFilter(allows)
        filtered_config = configfilter.filter(self.config_)
        self.assertEqual(filtered_config, expected_config)

    def test_denies(self):
        """test denies rules."""
        # keys in denies list will be removed from filtered config.
        denies = ['/1', '2/22', '2/33/333', '5']
        expected_config = {'2': {'33': {'44': '444'}}, '3': {'33': '44'}}
        configfilter = config_filter.ConfigFilter(denies=denies)
        filtered_config = configfilter.filter(self.config_)
        self.assertEqual(filtered_config, expected_config)

    def test_denies_asterisks(self):
        denies = ['*']
        configfilter = config_filter.ConfigFilter(denies=denies)
        filtered_config = configfilter.filter(self.config_)
        self.assertIsNone(filtered_config)

    def tet_deneis_asterisks_in_path(self):
        denies = ['*/33']
        expected_config = {'1': '1', '2': {'22': '22'}}
        configfilter = config_filter.ConfigFilter(denies=denies)
        filtered_config = configfilter.filter(self.config_)
        self.assertEqual(filtered_config, expected_config)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
