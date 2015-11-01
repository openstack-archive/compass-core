#!/usr/bin/python
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
import datetime
import os
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from compass.utils import flags
from compass.utils import logsetting
from compass.utils import util


class TestParseDatetime(unittest2.TestCase):
    """Test parse datetime."""

    def setUp(self):
        super(TestParseDatetime, self).setUp()

    def tearDown(self):
        super(TestParseDatetime, self).tearDown()

    def test_correct_format(self):
        date_time = '2014-7-10 9:10:40'
        parsed_datetime = util.parse_datetime(date_time)
        expected_datetime = datetime.datetime(2014, 7, 10, 9, 10, 40)
        self.assertEqual(parsed_datetime, expected_datetime)


class TestParseDatetimeRange(unittest2.TestCase):
    """Test parse datetime range."""

    def setUp(self):
        super(TestParseDatetimeRange, self).setUp()

    def tearDown(self):
        super(TestParseDatetimeRange, self).tearDown()

    def test_both_start_end_datetime(self):
        range = '2014-7-10 9:10:40,2014-7-11 9:10:40'
        parsed_datetime_range = util.parse_datetime_range(range)
        expected_datetime_range = (
            datetime.datetime(2014, 7, 10, 9, 10, 40),
            datetime.datetime(2014, 7, 11, 9, 10, 40)
        )
        self.assertEqual(expected_datetime_range, parsed_datetime_range)

    def test_none_start(self):
        range = ',2014-7-11 9:10:40'
        parsed_datetime_range = util.parse_datetime_range(range)
        expected_datetime_range = (
            None,
            datetime.datetime(2014, 7, 11, 9, 10, 40)
        )
        self.assertEqual(expected_datetime_range, parsed_datetime_range)

    def test_none_end(self):
        range = '2014-7-10 9:10:40,'
        parsed_datetime_range = util.parse_datetime_range(range)
        expected_datetime_range = (
            datetime.datetime(2014, 7, 10, 9, 10, 40),
            None
        )
        self.assertEqual(expected_datetime_range, parsed_datetime_range)

    def test_none_both(self):
        range = ','
        parsed_datetime_range = util.parse_datetime_range(range)
        expected_datetime_range = (None, None)
        self.assertEqual(expected_datetime_range, parsed_datetime_range)


class TestParseRequestArgDict(unittest2.TestCase):
    """Test parse request arg dict."""

    def setUp(self):
        super(TestParseRequestArgDict, self).setUp()

    def tearDown(self):
        super(TestParseRequestArgDict, self).tearDown()

    def test_single_pair(self):
        arg = 'a=b'
        parsed_arg_dict = util.parse_request_arg_dict(arg)
        expected_arg_dict = {'a': 'b'}
        self.assertEqual(parsed_arg_dict, expected_arg_dict)


class TestMergeDict(unittest2.TestCase):
    """Test merge dict."""

    def setUp(self):
        super(TestMergeDict, self).setUp()

    def tearDown(self):
        super(TestMergeDict, self).tearDown()

    def test_single_merge(self):
        lhs = {1: 1}
        rhs = {2: 2}
        merged_dict = util.merge_dict(lhs, rhs)
        expected_dict = {1: 1, 2: 2}
        self.assertEqual(merged_dict, expected_dict)

    def test_recursive_merge(self):
        lhs = {1: {2: 3}}
        rhs = {1: {3: 4}}
        merged_dict = util.merge_dict(lhs, rhs)
        expected_dict = {1: {2: 3, 3: 4}}
        self.assertEqual(merged_dict, expected_dict)

    def test_single_merge_override(self):
        lhs = {1: 1}
        rhs = {1: 2}
        merged_dict = util.merge_dict(lhs, rhs)
        expected_dict = {1: 2}
        self.assertEqual(merged_dict, expected_dict)

    def test_recursive_merge_override(self):
        lhs = {1: {2: 3, 3: 5}}
        rhs = {1: {2: 4, 4: 6}}
        merged_dict = util.merge_dict(lhs, rhs)
        expected_dict = {1: {2: 4, 3: 5, 4: 6}}
        self.assertEqual(merged_dict, expected_dict)

    def test_single_merge_no_override(self):
        lhs = {1: 1}
        rhs = {1: 2}
        merged_dict = util.merge_dict(lhs, rhs, False)
        expected_dict = {1: 1}
        self.assertEqual(merged_dict, expected_dict)

    def test_recursive_merge_no_override(self):
        lhs = {1: {2: 3, 3: 5}}
        rhs = {1: {2: 4, 4: 6}}
        merged_dict = util.merge_dict(lhs, rhs, False)
        expected_dict = {1: {2: 3, 3: 5, 4: 6}}
        self.assertEqual(merged_dict, expected_dict)

    def test_merge_dict_with_list(self):
        lhs = {1: {2: 3}}
        rhs = {1: {3: [4, 5, 6]}}
        merged_dict = util.merge_dict(lhs, rhs)
        expected_dict = {1: {2: 3, 3: [4, 5, 6]}}
        self.assertEqual(merged_dict, expected_dict)

    def test_inputs_not_dict(self):
        """test inputs not dict."""
        lhs = [1, 2, 3]
        rhs = {1: 2}
        merged = util.merge_dict(lhs, rhs)
        expected = {1: 2}
        self.assertEqual(merged, expected)

        lhs = [1, 2, 3]
        rhs = {1: 2}
        merged = util.merge_dict(lhs, rhs, False)
        expected = [1, 2, 3]
        self.assertEqual(merged, expected)

        lhs = {1: 2}
        rhs = [1, 2, 3]
        merged = util.merge_dict(lhs, rhs)
        expected = [1, 2, 3]
        self.assertEqual(merged, expected)

        lhs = {1: 2}
        rhs = [1, 2, 3]
        merged = util.merge_dict(lhs, rhs, False)
        expected = {1: 2}
        self.assertEqual(merged, expected)


class TestEncrypt(unittest2.TestCase):
    """Test encrypt."""

    def setUp(self):
        super(TestEncrypt, self).setUp()

    def tearDown(self):
        super(TestEncrypt, self).tearDown()


class TestParseTimeInterval(unittest2.TestCase):
    """Test parse time interval."""

    def setUp(self):
        super(TestParseTimeInterval, self).setUp()

    def tearDown(self):
        super(TestParseTimeInterval, self).tearDown()


class TestGetPluginsConfigFiles(unittest2.TestCase):
    """Test get plugins config files."""

    def setUp(self):
        super(TestGetPluginsConfigFiles, self).setUp()
        self.TEST_UTIL_HOME = os.path.dirname(os.path.realpath(__file__))

    def tearDown(self):
        super(TestGetPluginsConfigFiles, self).tearDown()

    def test_get_plugins_config_files(self):
        setting.PLUGINS_DIR = self.TEST_UTIL_HOME + '/data/plugins'
        loaded = util.get_plugins_config_files(
            'adapter'
        )
        expected = [
            setting.PLUGINS_DIR + '/test_installer1/adapter/test.conf',
            setting.PLUGINS_DIR + '/test_installer1/adapter/test1.conf',
            setting.PLUGINS_DIR + '/test_installer2/adapter/test.conf',
            setting.PLUGINS_DIR + '/test_installer2/adapter/test2.conf',
        ]
        loaded.sort()
        expected.sort()
        self.assertEqual(loaded, expected)


class TestLoadConfigs(unittest2.TestCase):
    """Test load configs."""

    def setUp(self):
        super(TestLoadConfigs, self).setUp()
        self.TEST_UTIL_HOME = os.path.dirname(os.path.realpath(__file__))

    def tearDown(self):
        super(TestLoadConfigs, self).tearDown()

    def test_load_no_suffix(self):
        loaded = util.load_configs(
            self.TEST_UTIL_HOME + '/data/test_no_suffix'
        )
        expected = []
        self.assertEqual(loaded, expected)

    def test_load_conf(self):
        loaded = util.load_configs(
            self.TEST_UTIL_HOME + '/data/test_load_conf'
        )
        expected = [{'TEST': True, 'PROD': False}]
        self.assertEqual(loaded, expected)

    def test_load_confs(self):
        loaded = util.load_configs(
            self.TEST_UTIL_HOME + '/data/test_load_confs'
        )
        expected = [
            {
                'TEST': True,
                'PROD': False
            },
            {
                'UTIL_TEST': 'unittest'
            }
        ]
        loaded.sort()
        expected.sort()
        self.assertTrue(loaded, expected)

    def test_load_confs_global_env(self):
        loaded = util.load_configs(
            self.TEST_UTIL_HOME + '/data/test_load_confs',
            env_globals={'TEST': False}
        )
        expected = [
            {
                'UTIL_TEST': 'unittest'
            },
            {
                'TEST': True,
                'PROD': False
            }
        ]
        loaded.sort()
        expected.sort()
        self.assertTrue(loaded, expected)

    def test_load_confs_local_env(self):
        loaded = util.load_configs(
            self.TEST_UTIL_HOME + '/data/test_load_confs',
            env_globals={'TEST': True}
        )
        expected = [
            {
                'TEST': True,
                'UTIL_TEST': 'unittest'
            },
            {
                'TEST': True,
                'PROD': False
            }]
        loaded.sort()
        expected.sort()
        self.assertTrue(loaded, expected)

    def test_load_confs_local_env_no_override(self):
        loaded = util.load_configs(
            self.TEST_UTIL_HOME + '/data/test_load_confs',
            env_globals={'TEST': False}
        )
        expected = [
            {
                'TEST': False,
                'UTIL_TEST': 'unittest'
            },
            {
                'TEST': True,
                'PROD': False
            }
        ]
        loaded.sort()
        expected.sort()
        self.assertTrue(loaded, expected)

    def test_load_conf_error(self):
        err_dir = 'non-exist/dir'
        loaded = util.load_configs(err_dir)
        self.assertEqual([], loaded)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
