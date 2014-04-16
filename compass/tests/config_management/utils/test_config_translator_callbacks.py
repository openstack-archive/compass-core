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


from compass.config_management.utils import config_reference
from compass.config_management.utils import config_translator_callbacks
from compass.utils import flags
from compass.utils import logsetting


class TestGetKeyFromPattern(unittest2.TestCase):
    """test get key from pattern."""

    def setUp(self):
        super(TestGetKeyFromPattern, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestGetKeyFromPattern, self).tearDown()

    def test_get_key_from_pattern(self):
        key = config_translator_callbacks.get_key_from_pattern(
            None, '/networking/interfaces/management/ip',
            to_pattern='macaddress-%(nic)s',
            nic='eth0')
        self.assertEqual(key, 'macaddress-eth0')

    def test_get_key_from_pattern_extra_keys_in_to_pattern(self):
        self.assertRaises(
            KeyError, config_translator_callbacks.get_key_from_pattern,
            None, '/networking/interfaces/management/ip',
            to_pattern='macaddress-%(nic)s')


class TestAddValue(unittest2.TestCase):
    """test add value."""

    def setUp(self):
        super(TestAddValue, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestAddValue, self).tearDown()

    def test_add_value_if_not_exist(self):
        config = 'hello'
        ref = config_reference.ConfigReference(config)
        translated_config = None
        translated_ref = config_reference.ConfigReference(translated_config)
        new_value = config_translator_callbacks.add_value(
            ref, None, translated_ref, None)
        self.assertEqual(new_value, ['hello'])

    def test_add_value(self):
        config = 'hello'
        ref = config_reference.ConfigReference(config)
        translated_config = ['hi']
        translated_ref = config_reference.ConfigReference(translated_config)
        new_value = config_translator_callbacks.add_value(
            ref, None, translated_ref, None)
        self.assertEqual(new_value, ['hi', 'hello'])

    def test_ignore_add_value(self):
        config = 'hello'
        ref = config_reference.ConfigReference(config)
        translated_config = ['hi']
        translated_ref = config_reference.ConfigReference(translated_config)
        new_value = config_translator_callbacks.add_value(
            ref, None, translated_ref, None, condition=False)
        self.assertEqual(new_value, ['hi'])


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
