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

import os
import unittest2

os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from compass.log_analyzor import line_matcher
from compass.utils import flags
from compass.utils import logsetting


class TestProgress(unittest2.TestCase):
    """test class for Progress class."""

    def setUp(self):
        super(TestProgress, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestProgress, self).tearDown()

    def test_repr(self):
        config = {
            'progress': 0.5,
            'message': 'dummy',
            'severity': ''
        }
        expected = 'Progress[progress:0.5, message:dummy, severity:]'
        test_line_matcher = line_matcher.Progress(**config)
        self.assertEqual(expected, test_line_matcher.__repr__())


class TestProgressCalculator(unittest2.TestCase):
    def setUp(self):
        super(TestProgressCalculator, self).setUp()
        logsetting.init()
        self._mock_progress()

    def tearDown(self):
        super(TestProgressCalculator, self).tearDown()

    def _mock_progress(self):
        self.progress = line_matcher.Progress(
            progress=0.5,
            message='',
            severity='')

    def test_update_progress_progress(self):
        test_1 = {
            'progress_data': 0.7,
            'message': '',
            'severity': '',
            'progress': self.progress
        }
        expected_1 = 0.7
        line_matcher.ProgressCalculator.update_progress(
            **test_1)
        self.assertEqual(expected_1, self.progress.progress)

    def test_update_progress_other(self):
        test = {
            'progress_data': 0.5,
            'message': 'dummy',
            'severity': 'dummy',
            'progress': self.progress
        }
        expected_message = test['message']
        expected_severity = test['severity']
        line_matcher.ProgressCalculator.update_progress(
            **test)
        self.assertEqual(expected_message, self.progress.message)
        self.assertEqual(expected_severity, self.progress.severity)


class TestIncrementalProgress(unittest2.TestCase):
    def setUp(self):
        super(TestIncrementalProgress, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestIncrementalProgress, self).tearDown()

    def test_init(self):
        test_exceed_one = {
            'min_progress': 1.1,
            'max_progress': 1.1,
            'incremental_ratio': 0.5,
        }
        self.assertRaises(
            IndexError,
            line_matcher.IncrementalProgress,
            **test_exceed_one)

    def test_min_larger_than_max(self):
        test_min_larger_than_max = {
            'min_progress': 0.7,
            'max_progress': 0.3,
            'incremental_ratio': 0.5,
        }
        self.assertRaises(
            IndexError,
            line_matcher.IncrementalProgress,
            **test_min_larger_than_max)

    def test_invalid_ratio(self):
        test_invalid_ratio = {
            'min_progress': 0.3,
            'max_progress': 0.7,
            'incremental_ratio': 1.1,
        }
        self.assertRaises(
            IndexError,
            line_matcher.IncrementalProgress,
            **test_invalid_ratio)


class TestRelativeProgress(unittest2.TestCase):
    def setUp(self):
        super(TestRelativeProgress, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestRelativeProgress, self).tearDown()

    def test_init(self):
        self.assertRaises(
            IndexError,
            line_matcher.RelativeProgress,
            progress=1.1)


class TestLineMatcher(unittest2.TestCase):
    def setUp(self):
        super(TestLineMatcher, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestLineMatcher, self).tearDown()

    def test_progress_unsupported(self):
        test_progress_unsupported = {
            'pattern': r' ',
            'progress': 'dummy',
        }
        self.assertRaises(
            TypeError,
            line_matcher.LineMatcher,
            **test_progress_unsupported)

    def test_regex_not_match(self):
        line = 'abc'
        regex_ = r'^s'
        progress = line_matcher.Progress(
            progress=1, message='a', severity=' ')
        test_regex_not_match = {
            'pattern': regex_,
            'unmatch_sameline_next_matcher_name': 'usn',
            'unmatch_nextline_next_matcher_name': 'unn',
            'match_sameline_next_matcher_name': 'msn',
            'match_nextline_next_matcher_name': 'mnn',
        }
        matcher = line_matcher.LineMatcher(
            **test_regex_not_match)
        expected = ('usn', 'unn')
        self.assertEqual(
            expected,
            matcher.update_progress(
                line, progress))

    def test_regex_match(self):
        line = 'abc'
        regex_ = r'^a'
        progress = line_matcher.Progress(
            progress=1, message='a', severity=' ')
        test_regex_match = {
            'pattern': regex_,
            'unmatch_sameline_next_matcher_name': 'usn',
            'unmatch_nextline_next_matcher_name': 'unn',
            'match_sameline_next_matcher_name': 'msn',
            'match_nextline_next_matcher_name': 'mnn',
        }
        matcher = line_matcher.LineMatcher(
            **test_regex_match)
        expected = ('msn', 'mnn')
        self.assertEqual(
            expected,
            matcher.update_progress(
                line, progress))

    def test_wrong_message(self):
        line = 'abc'
        progress = line_matcher.Progress(
            progress=1, message='a', severity=' ')
        test_wrong_message = {
            'pattern': r'.*.',
            'message_template': 'Installing %(package)s'
        }
        matcher = line_matcher.LineMatcher(
            **test_wrong_message)
        self.assertRaises(
            KeyError,
            matcher.update_progress,
            line=line,
            progress=progress)

if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
