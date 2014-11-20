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

"""test file matcher module"""

import datetime
import os
import unittest2

os.environ['COMPASS_IGNORE_SETTING'] = 'true'

from compass.utils import setting_wrapper as setting
reload(setting)

from compass.log_analyzor import file_matcher
from compass.log_analyzor.line_matcher import LineMatcher

from compass.utils import flags
from compass.utils import logsetting


class TestFilterFileExist(unittest2.TestCase):
    def setUp(self):
        super(TestFilterFileExist, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestFilterFileExist, self).tearDown()

    def test_filter(self):
        pathname = 'NeverExists'
        filter = file_matcher.FilterFileExist()
        res = filter.filter(pathname)
        self.assertFalse(res)


class TestCompositeFileFilter(unittest2.TestCase):
    def setUp(self):
        super(TestCompositeFileFilter, self).setUp()
        self.file_path = os.path.dirname(os.path.abspath(__file__))
        logsetting.init()

    def tearDown(self):
        super(TestCompositeFileFilter, self).tearDown()

    def test_filter(self):
        filter_list = [
            file_matcher.FilterFileExist(),
            file_matcher.FilterFileExist(),
        ]
        exists = self.file_path + '/test_file_matcher.py'
        non_exists = '/nonexists'
        composite_filter = file_matcher.CompositeFileFilter(
            filter_list)
        self.assertTrue(
            composite_filter.filter(exists))
        self.assertFalse(
            composite_filter.filter(non_exists))

    def test_append_filter(self):
        filter_list = [
            file_matcher.FilterFileExist(),
            file_matcher.FilterFileExist(),
        ]
        composite_filter = file_matcher.CompositeFileFilter(
            filter_list)
        new_filter = file_matcher.FilterFileExist()
        composite_filter.append_filter(new_filter)
        self.assertEqual(3, len(composite_filter.filters_))


class TestFileReader(unittest2.TestCase):
    def setUp(self):
        super(TestFileReader, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestFileReader, self).tearDown()

    def test_readline(self):
        data = {
            'pathname': os.path.dirname(
                os.path.abspath(__file__)) + '/data/sample_log',
            'log_history': {
                'position': 0,
                'partial_line': '',
            }
        }
        matcher = file_matcher.FileReader(**data)
        lines = list(matcher.readline())
        expected = ['Line1\n', 'Line2\n', 'Line3\n']
        for line in lines:
            self.assertIn(line, expected)


class TestFileReaderFactory(unittest2.TestCase):
    def setUp(self):
        super(TestFileReaderFactory, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestFileReaderFactory, self).tearDown()

    def test_get_file_reader_None(self):
        reader_factory = file_matcher.FileReaderFactory(
            'dummy',
        )
        data = {
            'hostname': 'dummy',
            'filename': 'dummy',
            'log_history': {
                'position': 0,
                'partial_line': '',
            }
        }
        reader = reader_factory.get_file_reader(**data)
        self.assertIsNone(reader)


class TestFileMatcher(unittest2.TestCase):
    def setUp(self):
        super(TestFileMatcher, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestFileMatcher, self).tearDown()

    def test_init_wrong_key(self):
        data = {
            'min_progress': 0.0,
            'max_progress': 0.1,
            'filename': 'sys.log',
            'line_matchers': {
                'dummy': LineMatcher(
                    pattern=r' ',
                    unmatch_nextline_next_matcher_name='start',
                    match_nextline_next_matcher_name='exit'
                )
            }
        }
        self.assertRaises(
            KeyError,
            file_matcher.FileMatcher,
            **data
        )

    def test_init_wrong_progress(self):
        data = {
            'min_progress': 0.5,
            'max_progress': 0.1,
            'filename': 'sys.log',
            'line_matchers': {
                'start': LineMatcher(
                    pattern=r' ',
                    unmatch_nextline_next_matcher_name='start',
                    match_nextline_next_matcher_name='exit'
                )
            }
        }
        self.assertRaises(
            IndexError,
            file_matcher.FileMatcher,
            **data
        )

    def test_update_progress_from_log_history(self):
        data = {
            'min_progress': 0.6,
            'max_progress': 0.9,
            'filename': 'sys.log',
            'line_matchers': {
                'start': LineMatcher(
                    pattern=r' ',
                    unmatch_nextline_next_matcher_name='start',
                    match_nextline_next_matcher_name='exit'
                )
            }
        }
        matcher = file_matcher.FileMatcher(**data)
        state = {
            'message': 'dummy',
            'severity': 'dummy',
            'percentage': 0.5
        }
        log_history = {
            'message': 'dummy',
            'severity': 'dummy',
            'percentage': 0.7
        }
        matcher.update_progress_from_log_history(
            state,
            log_history
        )
        self.assertEqual(0.81, state['percentage'])


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
