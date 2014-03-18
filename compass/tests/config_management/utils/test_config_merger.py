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

"""test config merger module.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import os
import unittest2

os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from compass.config_management.utils import config_merger
from compass.config_management.utils import config_reference
from compass.utils import flags
from compass.utils import logsetting


class TestConfigMapping(unittest2.TestCase):
    """test config mapping class."""

    def setUp(self):
        super(TestConfigMapping, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestConfigMapping, self).tearDown()

    def test_init(self):
        # path_list should be list of string.
        config_merger.ConfigMapping(
            path_list=['1/2/3', '/4/5/6'])
        config_merger.ConfigMapping(
            path_list=[u'1/2/3', u'/4/5/6'])
        self.assertRaises(
            TypeError,
            config_merger.ConfigMapping, path_list={'1/2/3': '4'})
        self.assertRaises(
            TypeError, config_merger.ConfigMapping, path_list='1234')
        self.assertRaises(
            TypeError, config_merger.ConfigMapping,
            path_list=[{'1/2/3': '4'}])

    def test_init_from_upper_keys(self):
        # from_upper_keys should be dict of string to string.
        config_merger.ConfigMapping(
            path_list=['1/2/3', '/4/5/6'], from_upper_keys={'4': '4'})
        config_merger.ConfigMapping(
            path_list=['1/2/3', '/4/5/6'], from_upper_keys={u'4': u'4'})
        self.assertRaises(
            TypeError, config_merger.ConfigMapping,
            path_list=['1/2/3', '/4/5/6'],
            from_upper_keys=['4'])
        self.assertRaises(
            TypeError, config_merger.ConfigMapping,
            path_list=['1/2/3', '/4/5/6'],
            from_upper_keys='4')
        self.assertRaises(
            TypeError, config_merger.ConfigMapping,
            path_list=['1/2/3', '/4/5/6'],
            from_upper_keys={4: '4'})
        self.assertRaises(
            TypeError, config_merger.ConfigMapping,
            path_list=['1/2/3', '/4/5/6'],
            from_upper_keys={'4': 4})

    def test_init_from_lower_keys(self):
        # from_lower_keys should be dict of string to string.
        config_merger.ConfigMapping(
            path_list=['1/2/3', '/4/5/6'], from_lower_keys={'4': '4'})
        config_merger.ConfigMapping(
            path_list=['1/2/3', '/4/5/6'], from_lower_keys={u'4': u'4'})
        self.assertRaises(
            TypeError, config_merger.ConfigMapping,
            path_list=['1/2/3', '/4/5/6'],
            from_lower_keys=['4'])
        self.assertRaises(
            TypeError, config_merger.ConfigMapping,
            path_list=['1/2/3', '/4/5/6'],
            from_lower_keys='4')
        self.assertRaises(
            TypeError, config_merger.ConfigMapping,
            path_list=['1/2/3', '/4/5/6'],
            from_lower_keys={4: '4'})
        self.assertRaises(
            TypeError, config_merger.ConfigMapping,
            path_list=['1/2/3', '/4/5/6'],
            from_lower_keys={'4': 4})

    def test_init_overlap_upper_keys_lower_keys(self):
        # there should be overlap between from_upper_keys and from_lower_keys.
        self.assertRaises(
            KeyError, config_merger.ConfigMapping,
            path_list=['1/2/3', '/4/5/6'],
            from_upper_keys={'1': '1', '2': '2'},
            from_lower_keys={'1': '1', '3': '3'})
        config_merger.ConfigMapping(
            path_list=['1/2/3', '/4/5/6'],
            from_upper_keys={'1': '1', '2': '2'},
            from_lower_keys={'3': '3', '4': '4'})

    def test_init_to_key(self):
        # to_key type should be string.
        config_merger.ConfigMapping(
            path_list=['1/2/3', '/4/5/6'],
            to_key='hello')
        config_merger.ConfigMapping(
            path_list=['1/2/3', '/4/5/6'],
            to_key=u'hello')
        self.assertRaises(
            TypeError, config_merger.ConfigMapping,
            path_list=['1/2/3', '/4/5/6'],
            to_key=['hello'])
        self.assertRaises(
            TypeError, config_merger.ConfigMapping,
            path_list=['1/2/3', '/4/5/6'],
            to_key=123)

    def test_init_to_key_no_asterrisks(self):
        # to_key should not contains '*'.
        self.assertRaises(
            KeyError, config_merger.ConfigMapping,
            path_list=['1/2/3', '/4/5/6'],
            to_key='abc*def')

    def test_init_override_conditions(self):
        # override_conditions type should be dict of string to string.
        config_merger.ConfigMapping(
            path_list=['1/2/3', '/4/5/6'],
            override_conditions={'hello': 'hi'})
        self.assertRaises(
            TypeError, config_merger.ConfigMapping,
            path_list=['1/2/3', '/4/5/6'],
            override_conditions=['hello', 'hi'])
        self.assertRaises(
            TypeError, config_merger.ConfigMapping,
            path_list=['1/2/3', '/4/5/6'],
            override_conditions='hello')
        self.assertRaises(
            TypeError, config_merger.ConfigMapping,
            path_list=['1/2/3', '/4/5/6'],
            override_conditions={5: 'hi'})
        self.assertRaises(
            TypeError, config_merger.ConfigMapping,
            path_list=['1/2/3', '/4/5/6'],
            override_conditions={'hello': 5})

    def test_init_override_conditions_no_asterrisks(self):
        # the value in each override_conditions key value pair
        # should not contains '*'.
        self.assertRaises(
            KeyError, config_merger.ConfigMapping,
            path_list=['1/2/3', '/4/5/6'],
            override_conditions={'hello': 'hi*hi'})

    def test_merge(self):
        # the key in path_list will be copied
        # from upper config to lower configs.
        upper_config = {
            'key': 'abc',
            'key2': 'def'
        }
        upper_ref = config_reference.ConfigReference(upper_config)
        lower_configs = {
            1: {}, 2: {}, 3: {}
        }
        lower_refs = {}
        for lower_key, lower_config in lower_configs.items():
            lower_refs[lower_key] = config_reference.ConfigReference(
                lower_config)

        merger = config_merger.ConfigMapping(
            path_list=['key'])
        merger.merge(upper_ref, lower_refs)
        self.assertEqual(
            lower_configs,
            {1: {'key': 'abc'}, 2: {'key': 'abc'}, 3: {'key': 'abc'}})

    def test_merge_all_matching_keys_copied(self):
        # all the keys matching the pattern will be copied
        # from upper config to lower configs.
        upper_config = {
            'key': 'abc',
            'key2': 'def'
        }
        upper_ref = config_reference.ConfigReference(upper_config)
        lower_configs = {
            1: {}, 2: {}, 3: {}
        }
        lower_refs = {}
        for lower_key, lower_config in lower_configs.items():
            lower_refs[lower_key] = config_reference.ConfigReference(
                lower_config)

        merger = config_merger.ConfigMapping(
            path_list=['key*'])
        merger.merge(upper_ref, lower_refs)
        self.assertEqual(
            lower_configs,
            {
                1: {'key': 'abc', 'key2': 'def'},
                2: {'key': 'abc', 'key2': 'def'},
                3: {'key': 'abc', 'key2': 'def'}
            }
        )

    def test_merge_value_set_explictly(self):
        # key in lower configs are set to expected value.
        upper_config = {
            'key': 'abc',
            'key2': 'def'
        }
        upper_ref = config_reference.ConfigReference(upper_config)
        lower_configs = {
            1: {}, 2: {}, 3: {}
        }
        lower_refs = {}
        for lower_key, lower_config in lower_configs.items():
            lower_refs[lower_key] = config_reference.ConfigReference(
                lower_config)

        merger = config_merger.ConfigMapping(
            path_list=['key'], value='def')
        merger.merge(upper_ref, lower_refs)
        self.assertEqual(
            lower_configs,
            {
                1: {'key': 'def'},
                2: {'key': 'def'},
                3: {'key': 'def'}
            }
        )

    def test_merge_value_set_by_callback(self):
        # key in lower config is called a callback to expected value .
        upper_config = {
            'key': 'abc',
            'key2': 'def'
        }
        upper_ref = config_reference.ConfigReference(upper_config)
        lower_configs = {
            1: {}, 2: {}, 3: {}
        }
        lower_refs = {}
        for lower_key, lower_config in lower_configs.items():
            lower_refs[lower_key] = config_reference.ConfigReference(
                lower_config)

        def _merge_value(sub_ref, ref_key, lower_sub_refs, to_key):
            values = {}
            for lower_key, lower_sub_ref in lower_sub_refs.items():
                values[lower_key] = '%s.%s' % (sub_ref.config, lower_key)

            return values

        merger = config_merger.ConfigMapping(
            path_list=['key'], value=_merge_value)
        merger.merge(upper_ref, lower_refs)
        self.assertEqual(
            lower_configs,
            {
                1: {'key': 'abc.1'},
                2: {'key': 'abc.2'},
                3: {'key': 'abc.3'}
            }
        )

    def test_merge_to_key(self):
        # set lower configs expected key from the key in upper config.
        upper_config = {
            'key': 'abc',
            'key2': 'def'
        }
        upper_ref = config_reference.ConfigReference(upper_config)
        lower_configs = {
            1: {}, 2: {}, 3: {}
        }
        lower_refs = {}
        for lower_key, lower_config in lower_configs.items():
            lower_refs[lower_key] = config_reference.ConfigReference(
                lower_config)

        def _merge_value(sub_ref, ref_key, lower_sub_refs, to_key):
            values = {}
            for lower_key, lower_sub_ref in lower_sub_refs.items():
                values[lower_key] = '%s.%s' % (sub_ref.config, lower_key)

            return values

        merger = config_merger.ConfigMapping(
            path_list=['key'], value=_merge_value, to_key='/key2')
        merger.merge(upper_ref, lower_refs)
        self.assertEqual(
            lower_configs,
            {
                1: {'key': None, 'key2': 'abc.1'},
                2: {'key': None, 'key2': 'abc.2'},
                3: {'key': None, 'key2': 'abc.3'}
            }
        )

    def test_merge_from_upper_and_lower_configs(self):
        # set lower configs from some keys of upper config and lower configs.
        upper_config = {
            'key': 'abc',
            'key_prefix': 'A',
            'key_suffix': 'B'
        }
        upper_ref = config_reference.ConfigReference(upper_config)
        lower_configs = {
            1: {'name': 'hello'}, 2: {'name': 'hi'}, 3: {'name': 'today'}
        }
        lower_refs = {}
        for lower_key, lower_config in lower_configs.items():
            lower_refs[lower_key] = config_reference.ConfigReference(
                lower_config)

        def _merge_value2(
            sub_ref, ref_key, lower_sub_refs, to_key,
            prefix='', suffix='', names={}
        ):
            values = {}
            for lower_key, lower_sub_ref in lower_sub_refs.items():
                values[lower_key] = '%s%s%s' % (
                    prefix, names.get(lower_key, ''), suffix)

            return values

        merger = config_merger.ConfigMapping(
            path_list=['key'], value=_merge_value2,
            from_upper_keys={'prefix': '/key_prefix', 'suffix': '/key_suffix'},
            from_lower_keys={'names': '/name'})
        merger.merge(upper_ref, lower_refs)
        self.assertEqual(
            lower_configs,
            {
                1: {'name': 'hello', 'key': 'AhelloB'},
                2: {'name': 'hi', 'key': 'AhiB'},
                3: {'name': 'today', 'key': 'AtodayB'}
            }
        )

    def test_merge_multikey_to_same_tokey_nooverride(self):
        # mutli key in upper config writes the same dest key, the later one
        # will be ignored if override is False.
        upper_config = {
            'key1': 'abc',
            'key2': 'bcd'
        }
        upper_ref = config_reference.ConfigReference(upper_config)
        lower_configs = {
            1: {}, 2: {}, 3: {}
        }
        lower_refs = {}
        for lower_key, lower_config in lower_configs.items():
            lower_refs[lower_key] = config_reference.ConfigReference(
                lower_config)
        merger = config_merger.ConfigMapping(
            path_list=['key1', 'key2'], to_key='/key', override=False)
        merger.merge(upper_ref, lower_refs)
        self.assertEqual(
            lower_configs,
            {
                1: {'key': 'abc', 'key1': None, 'key2': None},
                2: {'key': 'abc', 'key1': None, 'key2': None},
                3: {'key': 'abc', 'key1': None, 'key2': None}
            }
        )

    def test_merge_multikey_to_sam_tokey_override(self):
        # if multi key in upper config writes the same dest key,
        # the later one will override the former one if override is True.
        upper_config = {
            'key1': 'abc',
            'key2': 'bcd'
        }
        upper_ref = config_reference.ConfigReference(upper_config)
        lower_configs = {
            1: {}, 2: {}, 3: {}
        }
        lower_refs = {}
        for lower_key, lower_config in lower_configs.items():
            lower_refs[lower_key] = config_reference.ConfigReference(
                lower_config)
        merger = config_merger.ConfigMapping(
            path_list=['key1', 'key2'], to_key='/key', override=True)
        merger.merge(upper_ref, lower_refs)
        self.assertEqual(
            lower_configs,
            {
                1: {'key': 'bcd', 'key1': None, 'key2': None},
                2: {'key': 'bcd', 'key1': None, 'key2': None},
                3: {'key': 'bcd', 'key1': None, 'key2': None}
            }
        )

    def test_merge_override_callback(self):
        # override param can be set from callback.
        upper_config = {
            'key1': 'abc',
            'key2': 'bcd',
            'key3': 'def',
            'key_prefix': 'b',
            'key_suffix': 'd'
        }
        upper_ref = config_reference.ConfigReference(upper_config)
        lower_configs = {
            1: {}, 2: {}, 3: {}
        }
        lower_refs = {}
        for lower_key, lower_config in lower_configs.items():
            lower_refs[lower_key] = config_reference.ConfigReference(
                lower_config)

        def _generate_override(
            sub_ref, ref_key, lower_ref, to_key, prefix='', suffix=''
        ):
            return (
                sub_ref.config.startswith(prefix) and
                sub_ref.config.endswith(suffix)
            )

        merger = config_merger.ConfigMapping(
            path_list=['key1', 'key2', 'key3'], to_key='/key',
            override=_generate_override,
            override_conditions={
                'prefix': '/key_prefix', 'suffix': '/key_suffix'
            }
        )
        merger.merge(upper_ref, lower_refs)
        self.assertEqual(
            lower_configs,
            {
                1: {'key': 'bcd', 'key1': None, 'key2': None, 'key3': None},
                2: {'key': 'bcd', 'key1': None, 'key2': None, 'key3': None},
                3: {'key': 'bcd', 'key1': None, 'key2': None, 'key3': None}
            }
        )


class TestConfigMerger(unittest2.TestCase):
    """test config merger class."""

    def setUp(self):
        super(TestConfigMerger, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestConfigMerger, self).tearDown()

    def test_init(self):
        # mappings should be list of ConfigMapping.
        config_merger.ConfigMerger(mappings=[])
        config_merger.ConfigMerger(
            mappings=[
                config_merger.ConfigMapping(
                    path_list=['1/2/3', '/4/5/6'])
            ]
        )
        self.assertRaises(
            TypeError, config_merger.ConfigMerger,
            mapping={'hello': config_merger.ConfigMapping(path_list=[])})
        self.assertRaises(
            TypeError, config_merger.ConfigMerger,
            mapping=config_merger.ConfigMapping(path_list=[]))
        self.assertRaises(
            TypeError, config_merger.ConfigMerger,
            mapping='config_merger.ConfigMapping(path_list=[])')
        self.assertRaises(
            TypeError, config_merger.ConfigMerger,
            mapping=[{'hello': config_merger.ConfigMapping(path_list=[])}])
        self.assertRaises(
            TypeError, config_merger.ConfigMerger,
            mapping=['config_merger.ConfigMapping(path_list=[])'])

    def test_merge(self):
        # if multi ConfigMapping updates the same key and no override is set
        # for the later one, the later one will be ignored.
        config = {
            'key1': 'abc',
            'key2': 'bcd'
        }
        lower_configs = {
            1: {}, 2: {}, 3: {}
        }
        merger = config_merger.ConfigMerger(
            mappings=[
                config_merger.ConfigMapping(
                    path_list=['key1'], to_key='/mkey'),
                config_merger.ConfigMapping(
                    path_list=['key2'], to_key='/mkey')
            ]
        )
        merger.merge(config, lower_configs)
        self.assertEqual(
            lower_configs,
            {1: {'mkey': 'abc'}, 2: {'mkey': 'abc'}, 3: {'mkey': 'abc'}}
        )

    def test_merge_multi_mapping_to_same_tokey(self):
        # if multi ConfigMapping updates the same key and override is set
        # for the later one, the later one will override the former one.
        config = {
            'key1': 'abc',
            'key2': 'bcd'
        }
        lower_configs = {
            1: {}, 2: {}, 3: {}
        }
        merger = config_merger.ConfigMerger(
            mappings=[
                config_merger.ConfigMapping(
                    path_list=['key1'], to_key='/mkey'),
                config_merger.ConfigMapping(
                    path_list=['key2'], to_key='/mkey',
                    override=True)
            ]
        )
        merger.merge(config, lower_configs)
        self.assertEqual(
            lower_configs,
            {1: {'mkey': 'bcd'}, 2: {'mkey': 'bcd'}, 3: {'mkey': 'bcd'}}
        )

    def test_merge_override_callback(self):
        # override param can be callback.
        config = {
            'key1': 'abc',
            'key2': 'bcd'
        }
        lower_configs = {
            1: {}, 2: {}, 3: {}
        }

        def _merge_value(sub_ref, ref_key, lower_sub_refs, to_key):
            values = {}
            for lower_key, lower_sub_ref in lower_sub_refs.items():
                values[lower_key] = None

            return values

        merger = config_merger.ConfigMerger(
            mappings=[
                config_merger.ConfigMapping(
                    path_list=['key1'],
                    value=_merge_value,
                    to_key='/mkey')
            ]
        )
        merger.merge(config, lower_configs)
        self.assertEqual(
            lower_configs,
            {1: None, 2: None, 3: None}
        )


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
