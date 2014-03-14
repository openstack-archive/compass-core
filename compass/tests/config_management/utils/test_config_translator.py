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

"""test config translator module.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import os
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from compass.config_management.utils import config_reference
from compass.config_management.utils import config_translator
from compass.utils import flags
from compass.utils import logsetting


class TestKeyTranslator(unittest2.TestCase):
    """test key translator class."""

    def setUp(self):
        super(TestKeyTranslator, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestKeyTranslator, self).tearDown()

    def test_init(self):
        config_translator.KeyTranslator(
            translated_keys=['/a/b/c', '/d/e'])
        config_translator.KeyTranslator(
            translated_keys=[u'/a/b/c', u'/d/e'])
        config_translator.KeyTranslator(
            translated_keys=(lambda sub_ref, ref_key: []))
        config_translator.KeyTranslator(
            translated_keys=[lambda sub_ref, ref_key: '/d/e'])
        self.assertRaises(
            TypeError, config_translator.KeyTranslator,
            translated_keys='/a/b/c')
        self.assertRaises(
            TypeError, config_translator.KeyTranslator,
            translated_keys={'/a/b/c': 'd/e'})
        self.assertRaises(
            TypeError, config_translator.KeyTranslator,
            translated_keys=[5, 6, 7])
        self.assertRaises(
            TypeError, config_translator.KeyTranslator,
            translated_keys=[('5', '6')])
        self.assertRaises(
            KeyError, config_translator.KeyTranslator,
            translated_keys=['/a/*/b'])
        config_translator.KeyTranslator(
            translated_keys=['/a/b/c', '/d/e'], from_keys={'m': '/m/n'})
        config_translator.KeyTranslator(
            translated_keys=['/a/b/c', '/d/e'], from_keys={u'm': u'/m/n'})
        self.assertRaises(
            TypeError, config_translator.KeyTranslator,
            translated_keys=['/a/b/c'], from_keys=['m'])
        self.assertRaises(
            TypeError, config_translator.KeyTranslator,
            translated_keys=['/a/b/c'], from_keys='m')
        self.assertRaises(
            TypeError, config_translator.KeyTranslator,
            translated_keys=['/a/b/c'], from_keys={5: 'm'})
        self.assertRaises(
            TypeError, config_translator.KeyTranslator,
            translated_keys=['/a/b/c'], from_keys={'m': 5})
        self.assertRaises(
            TypeError, config_translator.KeyTranslator,
            translated_keys=['/a/b/c'], from_keys={'m': ['/m/n']})
        self.assertRaises(
            KeyError, config_translator.KeyTranslator,
            translated_keys=['/a/b/c'], from_keys={'m': '/m/*/n'})
        config_translator.KeyTranslator(
            translated_keys=['/a/b/c'], from_values={'m': '/m'})
        config_translator.KeyTranslator(
            translated_keys=['/a/b/c'], from_values={u'm': u'/m'})
        self.assertRaises(
            TypeError, config_translator.KeyTranslator,
            translated_keys=['/a/b/c'], from_values=['m'])
        self.assertRaises(
            TypeError, config_translator.KeyTranslator,
            translated_keys=['/a/b/c'], from_values='m')
        self.assertRaises(
            TypeError, config_translator.KeyTranslator,
            translated_keys=['/a/b/c'], from_values={5: 'm'})
        self.assertRaises(
            TypeError, config_translator.KeyTranslator,
            translated_keys=['/a/b/c'], from_keys={'m': 5})
        self.assertRaises(
            TypeError, config_translator.KeyTranslator,
            translated_keys=['/a/b/c'], from_values={'m': ['/m/n']})
        self.assertRaises(
            KeyError, config_translator.KeyTranslator,
            translated_keys=['/a/b/c'], from_values={'m': '/m/*/n'})
        config_translator.KeyTranslator(
            translated_keys=['1/2/3', '/4/5/6'],
            override_conditions={'hello': 'hi'})
        self.assertRaises(
            TypeError, config_translator.KeyTranslator,
            translated_keys=['1/2/3', '/4/5/6'],
            override_conditions=['hello', 'hi'])
        self.assertRaises(
            TypeError, config_translator.KeyTranslator,
            translated_keys=['1/2/3', '/4/5/6'],
            override_conditions='hello')
        self.assertRaises(
            TypeError, config_translator.KeyTranslator,
            translated_keys=['1/2/3', '/4/5/6'],
            override_conditions={5: 'hi'})
        self.assertRaises(
            TypeError, config_translator.KeyTranslator,
            translated_keys=['1/2/3', '/4/5/6'],
            override_conditions={'hello': 5})
        self.assertRaises(
            KeyError, config_translator.KeyTranslator,
            translated_keys=['1/2/3', '/4/5/6'],
            override_conditions={'hello': 'hi*hi'})

    def test_translate(self):
        # test get translated keys.
        config = {
            'key1': 'abc',
            'key2': 'bcd',
            'key3': 'mnq'
        }
        ref = config_reference.ConfigReference(config)
        translated_config = {}
        translated_ref = config_reference.ConfigReference(translated_config)
        translator = config_translator.KeyTranslator(
            translated_keys=['key2', 'key3'])
        translator.translate(ref, 'key1', translated_ref)
        self.assertEqual(translated_config, {'key2': 'abc', 'key3': 'abc'})
        translated_config = {}
        translated_ref = config_reference.ConfigReference(translated_config)
        translator = config_translator.KeyTranslator(
            translated_keys=(
                lambda sub_ref, ref_key: ['m%s' % ref_key, 'n%s' % ref_key]))
        translator.translate(ref, 'key*', translated_ref)
        self.assertEqual(
            translated_config, {
                'mkey1': 'abc', 'mkey2': 'bcd', 'mkey3': 'mnq',
                'nkey1': 'abc', 'nkey2': 'bcd', 'nkey3': 'mnq',
            }
        )
        translated_config = {}
        translated_ref = config_reference.ConfigReference(translated_config)
        translator = config_translator.KeyTranslator(
            translated_keys=['key1', (lambda sub_ref, ref_key: 'mkey2')])
        translator.translate(ref, 'key1', translated_ref)
        self.assertEqual(
            translated_config, {'key1': 'abc', 'mkey2': 'abc'})
        config = {
            'key': 'abc',
            'key_suffix': 'A',
            'key_prefix': 'B'
        }

        def _generate_key(sub_ref, ref_key, prefix='', suffix=''):
            return '%s%s%s' % (prefix, ref_key, suffix)

        def _generate_keys(sub_ref, ref_key, prefix='', suffix=''):
            return ['%s%s%s' % (prefix, ref_key, suffix)]

        ref = config_reference.ConfigReference(config)
        translated_config = {}
        translated_ref = config_reference.ConfigReference(translated_config)
        translator = config_translator.KeyTranslator(
            translated_keys=[_generate_key],
            from_keys={'prefix': '/key_prefix', 'suffix': '/key_suffix'})
        translator.translate(ref, 'key', translated_ref)
        self.assertEqual(translated_config, {'BkeyA': 'abc'})
        translated_config = {}
        translated_ref = config_reference.ConfigReference(translated_config)
        translator = config_translator.KeyTranslator(
            translated_keys=_generate_keys,
            from_keys={'prefix': '/key_prefix', 'suffix': '/key_suffix'})
        translator.translate(ref, 'key', translated_ref)
        self.assertEqual(translated_config, {'BkeyA': 'abc'})
        translated_config = {}
        translated_ref = config_reference.ConfigReference(translated_config)
        translator = config_translator.KeyTranslator(
            translated_keys=['mnq'],
            translated_value='mnq')
        translator.translate(ref, 'key', translated_ref)
        self.assertEqual(translated_config, {'mnq': 'mnq'})
        translated_config = {}
        translated_ref = config_reference.ConfigReference(translated_config)

        def _generate_none(
            sub_ref, ref_key, translated_sub_ref, translated_key
        ):
            return None

        translator = config_translator.KeyTranslator(
            translated_keys=['mnq'],
            translated_value=_generate_none)
        translator.translate(ref, 'key', translated_ref)
        self.assertEqual(translated_config, {'mnq': None})
        translated_config = {}
        translated_ref = config_reference.ConfigReference(translated_config)

        def _generate_value(
            sub_ref, ref_key, translated_sub_ref, translated_key,
            prefix='', suffix=''
        ):
            return '%s%s%s' % (prefix, sub_ref.config, suffix)

        translator = config_translator.KeyTranslator(
            translated_keys=['mnq'],
            translated_value=_generate_value,
            from_values={'prefix': '/key_prefix', 'suffix': '/key_suffix'})
        translator.translate(ref, 'key', translated_ref)
        self.assertEqual(translated_config, {'mnq': 'BabcA'})
        translated_config = {'mnq': 'mnq'}
        translated_ref = config_reference.ConfigReference(translated_config)
        translator = config_translator.KeyTranslator(
            translated_keys=['mnq'], override=False)
        translator.translate(ref, 'key', translated_ref)
        self.assertEqual(translated_config, {'mnq': 'mnq'})
        translator = config_translator.KeyTranslator(
            translated_keys=['mnq'], override=True)
        translator.translate(ref, 'key', translated_ref)
        self.assertEqual(translated_config, {'mnq': 'abc'})
        translated_config = {'klm': 'klm', 'mnq': 'mnq'}
        translated_ref = config_reference.ConfigReference(translated_config)

        def _generate_override(
            sub_ref, ref_key,
            translated_sub_ref, translated_key
        ):
            return translated_key == 'klm'

        translator = config_translator.KeyTranslator(
            translated_keys=['klm', 'mnq'], override=_generate_override)
        translator.translate(ref, 'key', translated_ref)
        self.assertEqual(translated_config, {'klm': 'abc', 'mnq': 'mnq'})
        translated_config = {'BmA': 'BmA', 'mnq': 'mnq'}
        translated_ref = config_reference.ConfigReference(translated_config)

        def _generate_override2(
            sub_ref, ref_key,
            translated_sub_ref, translated_key, prefix='', suffix='',
        ):
            return (
                translated_key.startswith(prefix) and
                translated_key.endswith(suffix))

        translator = config_translator.KeyTranslator(
            translated_keys=['BmA', 'mnq'],
            override=_generate_override2,
            override_conditions={
                'prefix': '/key_prefix', 'suffix': '/key_suffix'
            }
        )
        translator.translate(ref, 'key', translated_ref)
        self.assertEqual(translated_config, {'BmA': 'abc', 'mnq': 'mnq'})


class TestConfigTranslatorFunctions(unittest2.TestCase):
    """test config translator class."""

    def setUp(self):
        super(TestConfigTranslatorFunctions, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestConfigTranslatorFunctions, self).tearDown()

    def test_init(self):
        config_translator.ConfigTranslator(
            mapping={
                'key1': [config_translator.KeyTranslator(
                    translated_keys=['abc']
                )]
            }
        )
        config_translator.ConfigTranslator(
            mapping={
                u'key1': [config_translator.KeyTranslator(
                    translated_keys=['abc']
                )]
            }
        )
        self.assertRaises(
            TypeError, config_translator.ConfigTranslator,
            mapping=[config_translator.KeyTranslator(translated_keys=['abc'])]
        )
        self.assertRaises(
            TypeError, config_translator.ConfigTranslator,
            mapping=config_translator.KeyTranslator(translated_keys=['abc'])
        )
        self.assertRaises(
            TypeError, config_translator.ConfigTranslator,
            mapping={
                'abc': config_translator.KeyTranslator(translated_keys=['abc'])
            }
        )
        self.assertRaises(
            TypeError, config_translator.ConfigTranslator,
            mapping={
                1: [config_translator.KeyTranslator(translated_keys=['abc'])]
            }
        )
        self.assertRaises(
            TypeError, config_translator.ConfigTranslator,
            mapping={
                'abc': [
                    {
                        'm': config_translator.KeyTranslator(
                            translated_keys=['abc'])
                    }
                ]
            }
        )

    def test_translate(self):
        config = {
            'key1': 'abc',
            'key2': 'bcd'
        }
        translator = config_translator.ConfigTranslator(
            mapping={
                'key1': [
                    config_translator.KeyTranslator(
                        translated_keys=['mkey1']
                    )
                ],
                'key2': [
                    config_translator.KeyTranslator(
                        translated_keys=['mkey2'],
                        translated_value='mkey2'
                    ),
                    config_translator.KeyTranslator(
                        translated_keys=['mkey2'],
                        translated_value='nkey2'
                    )
                ]
            }
        )
        translated_config = translator.translate(config)
        self.assertEqual(translated_config,
                         {'mkey1': 'abc', 'mkey2': 'mkey2'})
        translator = config_translator.ConfigTranslator(
            mapping={
                'key1': [
                    config_translator.KeyTranslator(
                        translated_keys=['mkey1']
                    )
                ],
                'key2': [
                    config_translator.KeyTranslator(
                        translated_keys=['mkey2'],
                        translated_value='mkey2'
                    ),
                    config_translator.KeyTranslator(
                        translated_keys=['mkey2'],
                        translated_value='nkey2',
                        override=True
                    )
                ]
            }
        )
        translated_config = translator.translate(config)
        self.assertEqual(translated_config,
                         {'mkey1': 'abc', 'mkey2': 'nkey2'})

        def _generate_none(
            sub_ref, ref_key, translated_sub_ref, translated_key
        ):
            return None

        translator = config_translator.ConfigTranslator(
            mapping={
                'key1': [
                    config_translator.KeyTranslator(
                        translated_keys=['mkey1'],
                        translated_value=_generate_none
                    )
                ]
            }
        )
        translated_config = translator.translate(config)
        self.assertEqual(translated_config,
                         None)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
