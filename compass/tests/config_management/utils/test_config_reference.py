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

    def setUp(self):
        super(TestConfigReference, self).setUp()
        logsetting.init()
        self.config_ = {'1': {'2': 3, '10': {}}, '4': [5, 6, 7], '8': 8}
        self.ref_ = config_reference.ConfigReference(self.config_)

    def tearDown(self):
        super(TestConfigReference, self).tearDown()

    def test_init(self):
        """test init function."""
        # create ConfigReference instance.
        self.assertEqual(self.ref_.config, self.config_)
        self.assertEqual(id(self.ref_.config), id(self.config_))

    def test_init_with_parent(self):
        # create ConfigReference instance with parent param.
        # it will add a key value pair in parent config if not exists.
        config2 = {'5': {'6': 6}}
        ref2 = config_reference.ConfigReference(config2['5'], self.ref_, '5')
        expected_config = copy.deepcopy(self.config_)
        util.merge_dict(expected_config, config2)
        self.assertEqual(self.config_, expected_config)
        self.assertEqual(id(self.config_['5']), id(ref2.config))
        self.assertEqual(id(ref2.config), id(config2['5']))

    def test_init_with_parent_update(self):
        # create ConfigReference instance with parent param.
        # it will update the key value pair in parent config if it exists.
        config3 = {'5': {'7': 7}}
        ref3 = config_reference.ConfigReference(config3['5'], self.ref_, '5')
        expected_config = copy.deepcopy(self.config_)
        util.merge_dict(expected_config, config3)
        self.assertEqual(self.config_, expected_config)
        self.assertEqual(id(self.config_['5']), id(ref3.config))
        self.assertEqual(id(ref3.config), id(config3['5']))

    def test_init_config_keys(self):
        # config key should be string.
        config_reference.ConfigReference(1)
        config_reference.ConfigReference('1')
        config_reference.ConfigReference([1, 2])
        config_reference.ConfigReference({'1': 2})
        config_reference.ConfigReference({u'1': 2})
        self.assertRaises(
            TypeError, config_reference.ConfigReference, {1: 2})

    def test_init_parent_type(self):
        # parent instance should be of ConfigReference.
        self.assertRaises(
            TypeError, config_reference.ConfigReference,
            {'1': 2}, parent=object())

    def test_init_parent_key_type(self):
        # parent key should be string.
        self.assertRaises(
            TypeError, config_reference.ConfigReference,
            {'1': 2}, parent=self.ref_, parent_key=6)

    def test_ref_noexist_key(self):
        # raise KeyError when accessing noexist key.
        self.assertRaises(KeyError, self.ref_.ref, '')
        self.assertRaises(KeyError, self.ref_.ref, '/1/2/4')

    def test_ref_dot_key(self):
        # . key returns the same reference.
        self.assertEqual(id(self.ref_.ref('.')), id(self.ref_))
        self.assertEqual(self.ref_.ref('.').config, self.config_)

    def test_ref_double_dot_key(self):
        # .. key returns the same reference if ref itself
        # is the top level reference.
        self.assertEqual(id(self.ref_.ref('..')), id(self.ref_))
        self.assertEqual(self.ref_.ref('..').config, self.config_)

    def test_ref_slash_key(self):
        # / key returns the same reference if the ref itself is
        # the top level reference.
        self.assertEqual(id(self.ref_.ref('/')), id(self.ref_))
        self.assertEqual(self.ref_.ref('/').config, self.config_)

    def test_ref_key(self):
        # ref(<key>) returns the reference of the <key>.
        self.assertEqual(self.ref_.ref('1').config, self.config_['1'])
        self.assertEqual(self.ref_.ref('1/2').config,
                         self.config_['1']['2'])
        self.assertEqual(self.ref_.ref('1/2/.').config,
                         self.config_['1']['2'])
        self.assertEqual(self.ref_.ref('1/2/..').config,
                         self.config_['1'])
        self.assertEqual(self.ref_.ref('1/2//').config,
                         self.config_['1']['2'])
        self.assertEqual(self.ref_.ref('/1').config,
                         self.config_['1'])
        self.assertEqual(self.ref_.ref('/1/2').config,
                         self.config_['1']['2'])

    def test_ref_key_in_parent(self):
        # from sub ref, we can get the reference of it parent or root.
        subref = self.ref_.ref('1')
        self.assertEqual(id(subref.ref('..')), id(self.ref_))
        self.assertEqual(subref.ref('..').config, self.config_)
        self.assertEqual(id(subref.ref('../..')), id(self.ref_))
        self.assertEqual(subref.ref('../..').config, self.config_)
        self.assertEqual(id(subref.ref('/')), id(self.ref_))
        self.assertEqual(subref.ref('/').config, self.config_)
        self.assertEqual(subref.ref('2').config, self.config_['1']['2'])
        self.assertEqual(subref.ref('2/..').config, self.config_['1'])
        self.assertEqual(subref.ref('/4').config, self.config_['4'])

    def test_ref_key_not_exist(self):
        subref = self.ref_.ref('1')
        self.assertRaises(KeyError, subref.ref, '/4/5')
        self.assertRaises(KeyError, subref.ref, '/9')

    def test_ref_key_not_exist_and_create(self):
        # create sub reference if key does not exists and
        # create_if_not_exist param is True.
        subref2 = self.ref_.ref('9', True)
        self.assertEqual(self.ref_.ref('9'), subref2)

    def test_refs(self):
        """test refs function."""
        # ref_keys will return all matching refs.
        refkeys = self.ref_.ref_keys('1')
        self.assertEqual(set(refkeys), set(['1']))

    def test_refs_asterisks(self):
        refkeys = self.ref_.ref_keys('/1/*')
        self.assertEqual(set(refkeys), set(['/1/2', '/1/10']))
        refkeys = self.ref_.ref_keys('*')
        self.assertEqual(set(refkeys), set(['1', '4', '8']))
        refkeys = self.ref_.ref_keys('8*')
        self.assertEqual(set(refkeys), set(['8']))

    def test_refs_empty_key(self):
        # ref keys will raise KeyError if the param is empty.
        self.assertRaises(KeyError, self.ref_.ref_keys, '')

    def test_contains(self):
        """test contains function."""
        self.assertIn('/1/2', self.ref_)
        self.assertIn('1/10/', self.ref_)
        self.assertIn('4/', self.ref_)
        self.assertIn('/1/2/..', self.ref_)
        self.assertNotIn('/1/3/7', self.ref_)
        self.assertNotIn('/1/2/3/..', self.ref_)

    def test_getitem(self):
        """test getitem function."""
        self.assertEqual(self.ref_['1'], self.config_['1'])
        self.assertEqual(self.ref_['1/2'], self.config_['1']['2'])
        self.assertEqual(self.ref_['/1'], self.config_['1'])
        self.assertEqual(self.ref_['1/2/../../4'], self.config_['4'])

    def test_setitem(self):
        """test setitem function."""
        self.ref_['/1/2'] = '6'
        self.assertEqual(self.config_['1']['2'], '6')
        self.assertEqual(self.ref_['/1/2'], '6')
        self.ref_['1/10/5'] = 7
        self.assertEqual(self.config_['1']['10']['5'], 7)
        self.assertEqual(self.ref_['1/10/5'], 7)
        self.ref_['3/6/8'] = [1, 3, 5]
        self.assertEqual(self.config_['3']['6']['8'], [1, 3, 5])
        self.assertEqual(self.ref_['3/6/8'], [1, 3, 5])

    def test_del(self):
        """test del function."""
        del self.ref_['/8']
        self.assertNotIn('8', self.config_)
        del self.ref_['1/2']
        self.assertNotIn('2', self.config_['1'])
        del self.ref_['1']
        self.assertNotIn('1', self.config_)

    def test_del_noexist_key(self):
        # del nonexist key will raise KeyError
        self.assertRaises(KeyError, self.ref_.__delitem__, '9')

    def test_len(self):
        ref = config_reference.ConfigReference({})
        self.assertEqual(len(ref), 0)
        ref = config_reference.ConfigReference({'1': '2', '2': '4'})
        self.assertEqual(len(ref), 2)
        ref = config_reference.ConfigReference(
            {'1': {'2': '3', '4': '5'}, '2': '4'})
        self.assertEqual(len(ref), 4)

    def test_bool(self):
        ref = config_reference.ConfigReference({})
        self.assertFalse(ref)
        ref = config_reference.ConfigReference({'1': 1})
        self.assertTrue(ref)

    def test_get(self):
        """test get function."""
        self.assertEqual(self.ref_.get('1/2'), self.config_['1']['2'])
        self.assertIsNone(self.ref_.get('1/3'))
        self.assertEqual(self.ref_.get('1/3', 3), 3)
        self.assertNotIn('3', self.config_['1'])

    def test_setdefault(self):
        """test setdefault function."""
        self.assertEqual(self.ref_.setdefault('1/2').config,
                         self.config_['1']['2'])
        self.assertIsNone(self.ref_.setdefault('1/3').config)
        self.assertEqual(self.ref_.setdefault('1/4', 4).config, 4)
        self.assertEqual(4, self.config_['1']['4'])

    def test_update(self):
        """test update function."""
        expected_config = copy.deepcopy(self.config_)
        config2 = {'9': 9, '10': {'10': 10}}
        util.merge_dict(expected_config, config2)
        self.ref_.update(config2)
        self.assertEqual(self.ref_.config, expected_config)

    def test_update_nooverride(self):
        # if override is False and ref config is not None, ignore the update.
        expected_config = copy.deepcopy(self.config_)
        self.ref_.update(10, False)
        self.assertEqual(self.config_, expected_config)

    def test_update_override(self):
        # if override is True, it will force update the config.
        self.ref_.update(10)
        self.assertEqual(self.ref_.config, 10)

    def test_iter(self):
        """test iter function."""
        items = dict(self.ref_.items())
        self.assertEqual({
            '1': {'2': 3, '10': {}},
            '1/2': 3,
            '1/10': {},
            '4': [5, 6, 7],
            '8': 8}, items)
        self.assertEqual(
            set(self.ref_.keys()),
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
