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

"""test config reference module.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import copy
import os
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from compass.config_management.utils import config_reference
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import util


class TestCleanConfig(unittest2.TestCase):
    """test clean_config function."""

    def setUp(self):
        super(TestCleanConfig, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestCleanConfig, self).tearDown()

    def test_config_empty(self):
        """test config is empty."""
        self.assertIsNone(config_reference.get_clean_config(None))
        self.assertIsNone(config_reference.get_clean_config({}))
        self.assertEqual([], config_reference.get_clean_config([]))
        self.assertEqual('', config_reference.get_clean_config(''))

    def test_recursive_empty_dict(self):
        """test config is recursively empty."""
        self.assertIsNone(config_reference.get_clean_config({'test': {}}))
        self.assertIsNone(config_reference.get_clean_config({'test': None}))

    def test_nromal_dict(self):
        """test config is normal dict."""
        config_list = [
            {'abc': 'abc'},
            {'abc': [1, 2, 3]},
            {'abc': {'1': '123'}},
            [1, 2, 3],
            'abc',
        ]
        for config in config_list:
            self.assertEqual(config, config_reference.get_clean_config(config))

    def test_partial_clean(self):
        """test config is partial cleaned."""
        config_and_cleans = [
            ({'abc': 1, 'bcd': None}, {'abc': 1}),
            ({'abc': 1, 'bcd': {}}, {'abc': 1}),
            ({'abc': 1, 'bcd': {'m': {}}}, {'abc': 1}),
            ({'abc': 1, 'b': {'m': {}, 'n': 2}}, {'abc': 1, 'b': {'n': 2}}),
        ]
        for config, expected_config in config_and_cleans:
            self.assertEqual(
                expected_config,
                config_reference.get_clean_config(config))


class TestConfigReference(unittest2.TestCase):
    """test config reference class."""

    def test_init(self):
        """test init function."""
        config = {'1': {'2': 3, '10': {}}, '4': [5, 6, 7], '8': 8}
        ref = config_reference.ConfigReference(config)
        config2 = {'5': {'6': 6}}
        ref2 = config_reference.ConfigReference(config2['5'], ref, '5')
        expected_config = copy.deepcopy(config)
        util.merge_dict(expected_config, config2)
        self.assertEqual(ref.config, expected_config)
        self.assertEqual(id(ref.config['5']), id(ref2.config))
        config3 = {'5': {'7': 7}}
        ref3 = config_reference.ConfigReference(config3['5'], ref, '5')
        self.assertEqual(id(ref.config['5']), id(ref3.config))
        config4 = {1: 2}
        self.assertRaises(
            TypeError, config_reference.ConfigReference, config4)
        config5 = {'1': 2}
        self.assertRaises(
            TypeError, config_reference.ConfigReference,
            config5, parent=object())
        self.assertRaises(
            TypeError, config_reference.ConfigReference,
            config5, parent=ref3, parent_key=6)
        config6 = {'2': 4}
        config_reference.ConfigReference(config6, ref, '1')
        self.assertEqual(
            config,
            {'1': {'2': 4}, '4': [5, 6, 7], '5': {'7': 7}, '8': 8})

    def test_ref(self):
        """test ref function."""
        config = {'1': {'2': 3, '10': {}}, '4': [5, 6, 7], '8': 8}
        ref = config_reference.ConfigReference(config)
        self.assertRaises(KeyError, ref.ref, '')
        self.assertRaises(KeyError, ref.ref, '/1/2/4')
        self.assertEqual(ref.ref('.').config, config)
        self.assertEqual(ref.ref('..').config, config)
        self.assertEqual(ref.ref('/').config, config)
        self.assertEqual(ref.ref('1').config, config['1'])
        self.assertEqual(ref.ref('1/2').config, config['1']['2'])
        self.assertEqual(ref.ref('1/2/.').config, config['1']['2'])
        self.assertEqual(ref.ref('1/2/..').config, config['1'])
        self.assertEqual(ref.ref('1/2//').config, config['1']['2'])
        self.assertEqual(ref.ref('/1').config, config['1'])
        self.assertEqual(ref.ref('/1/2').config, config['1']['2'])
        subref = ref.ref('1')
        self.assertEqual(subref.ref('2').config, config['1']['2'])
        self.assertEqual(subref.ref('2/..').config, config['1'])
        self.assertEqual(subref.ref('..').config, config)
        self.assertEqual(subref.ref('../..').config, config)
        self.assertEqual(subref.ref('/').config, config)
        self.assertEqual(subref.ref('/4').config, config['4'])
        self.assertRaises(KeyError, subref.ref, '/4/5')
        self.assertRaises(KeyError, subref.ref, '/9')
        subref2 = ref.ref('9', True)
        self.assertEqual(ref.ref('9'), subref2)

    def test_refs(self):
        """test refs function."""
        config = {'1': {'2': 3, '10': {}}, '4': [5, 6, 7], '8': 8, '88': 88}
        ref = config_reference.ConfigReference(config)
        refkeys = ref.ref_keys('1')
        self.assertEqual(set(refkeys), set(['1']))
        refkeys = ref.ref_keys('/1/*')
        self.assertEqual(set(refkeys), set(['/1/2', '/1/10']))
        refkeys = ref.ref_keys('*')
        self.assertEqual(set(refkeys), set(['1', '4', '8', '88']))
        refkeys = ref.ref_keys('8*')
        self.assertEqual(set(refkeys), set(['8', '88']))
        self.assertRaises(KeyError, ref.ref_keys, '')

    def test_contains(self):
        """test contains function."""
        config = {'1': {'2': '3', '10': {}}, '4': [5, 6, 7], '8': 8}
        ref = config_reference.ConfigReference(config)
        self.assertIn('/1/2', ref)
        self.assertIn('1/10/', ref)
        self.assertIn('4/', ref)
        self.assertIn('/1/2/..', ref)
        self.assertNotIn('/1/3/7', ref)
        self.assertNotIn('/1/2/3/..', ref)

    def test_getitem(self):
        """test getitem function."""
        config = {'1': {'2': '3', '10': {}}, '4': [5, 6, 7], '8': 8}
        ref = config_reference.ConfigReference(config)
        self.assertEqual(ref['1'], config['1'])
        self.assertEqual(ref['1/2'], config['1']['2'])
        self.assertEqual(ref['/1'], config['1'])
        self.assertEqual(ref['1/2/../../4'], config['4'])

    def test_setitem(self):
        """test setitem function."""
        config = {'1': {'2': '3', '10': {}}, '4': [5, 6, 7], '8': 8}
        ref = config_reference.ConfigReference(config)
        ref['/1/2'] = '6'
        self.assertEqual(config['1']['2'], '6')
        self.assertEqual(ref['/1/2'], '6')
        ref['1/10/5'] = 7
        self.assertEqual(config['1']['10']['5'], 7)
        self.assertEqual(ref['1/10/5'], 7)
        ref['3/6/8'] = [1, 3, 5]
        self.assertEqual(config['3']['6']['8'], [1, 3, 5])
        self.assertEqual(ref['3/6/8'], [1, 3, 5])

    def test_del(self):
        """test del function."""
        config = {'1': {'2': '3', '10': {}}, '4': [5, 6, 7], '8': 8}
        ref = config_reference.ConfigReference(config)
        del ref['/8']
        self.assertNotIn('8', config)
        del ref['1/2']
        self.assertNotIn('2', config['1'])
        del ref['1']
        self.assertNotIn('1', config)
        self.assertRaises(KeyError, ref.__delitem__, '9')

    def test_len(self):
        config = {'1': {'2': '3', '10': {}}, '4': [5, 6, 7], '8': 8}
        ref = config_reference.ConfigReference(config)
        self.assertEqual(len(ref), 5)

    def test_bool(self):
        ref = config_reference.ConfigReference({})
        self.assertFalse(ref)
        ref = config_reference.ConfigReference({'1': 1})
        self.assertTrue(ref)

    def test_get(self):
        """test get function."""
        config = {'1': {'2': '3', '10': {}}, '4': [5, 6, 7], '8': 8}
        ref = config_reference.ConfigReference(config)
        self.assertEqual(ref.get('1/2'), config['1']['2'])
        self.assertIsNone(ref.get('1/3'))
        self.assertEqual(ref.get('1/3', 3), 3)
        self.assertNotIn('3', config['1'])

    def test_setdefault(self):
        """test setdefault function."""
        config = {'1': {'2': '3', '10': {}}, '4': [5, 6, 7], '8': 8}
        ref = config_reference.ConfigReference(config)
        self.assertEqual(ref.setdefault('1/2').config, config['1']['2'])
        self.assertIsNone(ref.setdefault('1/3').config)
        self.assertEqual(ref.setdefault('1/4', 4).config, 4)
        self.assertEqual(4, config['1']['4'])

    def test_update(self):
        """test update function."""
        config = {'1': {'2': '3', '10': {}}, '4': [5, 6, 7], '8': 8}
        expected_config = copy.deepcopy(config)

        ref = config_reference.ConfigReference(config)
        config2 = {'9': 9, '10': {'10': 10}}
        util.merge_dict(expected_config, config2)
        ref.update(config2)
        self.assertEqual(ref.config, expected_config)
        ref.update(10, False)
        self.assertEqual(ref.config, expected_config)
        ref.update(10)
        self.assertEqual(ref.config, 10)

    def test_iter(self):
        """test iter function."""
        config = {'1': {'2': '3', '10': {}}, '4': [5, 6, 7], '8': 8}
        ref = config_reference.ConfigReference(config)
        items = dict(ref.items())
        self.assertEqual({
            '1': {'2': '3', '10': {}},
            '1/2': '3',
            '1/10': {},
            '4': [5, 6, 7],
            '8': 8}, items)
        self.assertEqual(
            set(ref.keys()),
            set(['1', '1/2', '1/10', '4', '8']))

    def test_match(self):
        config = {'1': {'2': 'abcdef'}, '3': ['efg', 'hij', 'k']}
        ref = config_reference.ConfigReference(config)
        self.assertTrue(ref.match({'1/2': 'abcdef'}))
        self.assertFalse(ref.match({'1/2': 'abceef'}))
        self.assertTrue(ref.match({'1/2': '[a-z]+'}))
        self.assertFalse(ref.match({'1/2': '[0-9]+'}))
        self.assertTrue(ref.match({'3': 'efg'}))
        self.assertFalse(ref.match({'3': 'm'}))
        self.assertTrue(ref.match({'3': 'hij'}))

    def test_filter(self):
        config = {'1': {'2': 'abcdef', '4': 4}, '3': ['efg', 'hij', 'k']}
        ref = config_reference.ConfigReference(config)
        self.assertEqual(ref.filter(['1/2', '1/4', '5']),
                         {'1/2': 'abcdef', '1/4': 4})


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
