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

"""test adapter matcher module"""

import os
import unittest2

os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)

from compass.log_analyzor import adapter_matcher
from compass.log_analyzor.file_matcher import FileMatcher
from compass.log_analyzor.file_matcher import FileReaderFactory
from compass.log_analyzor.line_matcher import LineMatcher

from compass.utils import flags
from compass.utils import logsetting


class TestAdapterItemMatcher(unittest2.TestCase):
    def setUp(self):
        super(TestAdapterItemMatcher, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestAdapterItemMatcher, self).tearDown()

    def test_update_progress(self):
        file_matchers = [
            FileMatcher(
                min_progress=0.6,
                max_progress=0.9,
                filename='test_log',
                line_matchers={
                    'start': LineMatcher(
                        pattern=r'',
                        severity='',
                    )
                }
            )
        ]
        adapter_item_matcher = adapter_matcher.AdapterItemMatcher(
            file_matchers
        )
        file_reader_factory = FileReaderFactory(
            logdir=os.path.dirname(
                os.path.abspath(__file__)) + '/data'
        )
        state = {
            'message': 'dummy',
            'severity': 'dummy',
            'percentage': 0.5
        }
        log_history_mapping = {
            'test_log': {
                'filename': 'test_log',
                'partial_line': '',
                'position': 0,
                'line_matcher_name': 'start',
                'percentage': 0.7,
                'message': '',
                'severity': 'INFO'
            }
        }
        adapter_item_matcher.update_progress(
            file_reader_factory=file_reader_factory,
            name='host1',
            state=state,
            log_history_mapping=log_history_mapping
        )
        self.assertEqual(0.81, state['percentage'])

    def test_no_filename_update_progress(self):
        file_matchers = [
            FileMatcher(
                min_progress=0.6,
                max_progress=0.9,
                filename='test_log',
                line_matchers={
                    'start': LineMatcher(
                        pattern=r'',
                        severity='',
                    )
                }
            )
        ]
        adapter_item_matcher = adapter_matcher.AdapterItemMatcher(
            file_matchers
        )
        file_reader_factory = FileReaderFactory(
            logdir=os.path.dirname(
                os.path.abspath(__file__)) + '/data'
        )
        state = {
            'message': 'dummy',
            'severity': 'dummy',
            'percentage': 0.5
        }
        log_history_mapping = {
            'dummy_log': {
                'filename': 'test_log',
                'partial_line': '',
                'position': 0,
                'line_matcher_name': 'start',
                'percentage': 0.7,
                'message': '',
                'severity': 'INFO'
            }
        }
        adapter_item_matcher.update_progress(
            file_reader_factory=file_reader_factory,
            name='host1',
            state=state,
            log_history_mapping=log_history_mapping
        )
        self.assertEqual(0.6, state['percentage'])


class TestOSMatcher(unittest2.TestCase):
    def setUp(self):
        super(TestOSMatcher, self).setUp()
        logsetting.init()
        file_matchers = [
            FileMatcher(
                min_progress=0.6,
                max_progress=0.9,
                filename='test_log',
                line_matchers={
                    'start': LineMatcher(
                        pattern=r'',
                        severity='',
                    )
                }
            )
        ]
        self.item_matcher = adapter_matcher.AdapterItemMatcher(file_matchers)
        file_reader_factory = FileReaderFactory(
            logdir=os.path.dirname(
                os.path.abspath(__file__)) + '/data'
        )
        self.os_matcher = adapter_matcher.OSMatcher(
            os_installer_name='cobbler',
            os_pattern=r'CentOS.*',
            item_matcher=self.item_matcher,
            file_reader_factory=file_reader_factory
        )

    def tearDown(self):
        super(TestOSMatcher, self).tearDown()

    def test_match_none(self):
        matcher = self.os_matcher.match(
            os_installer_name='cobbler',
            os_name=None
        )
        self.assertFalse(matcher)

    def test_match(self):
        test_match = {
            'os_installer_name': 'cobbler',
            'os_name': 'CentOS',
        }
        matcher = self.os_matcher.match(**test_match)
        self.assertTrue(matcher)

    def test_installer_unmatch(self):
        test_unmatch = {
            'os_installer_name': 'dummy',
            'os_name': 'CentOS',
        }
        matcher = self.os_matcher.match(**test_unmatch)
        self.assertFalse(matcher)

    def test_os_unmatch(self):
        test_unmatch = {
            'os_installer_name': 'cobbler',
            'os_name': 'dummy'
        }
        matcher = self.os_matcher.match(**test_unmatch)
        self.assertFalse(matcher)

    def test_both_unmatch(self):
        test_unmatch = {
            'os_installer_name': 'dummy',
            'os_name': 'dummy'
        }
        matcher = self.os_matcher.match(**test_unmatch)
        self.assertFalse(matcher)

    def test_update_progress(self):
        state = {
            'message': 'dummy',
            'severity': 'dummy',
            'percentage': 0.5
        }
        log_history_mapping = {
            'test_log': {
                'filename': 'test_log',
                'partial_line': '',
                'position': 0,
                'line_matcher_name': 'start',
                'percentage': 0.0,
                'message': '',
                'severity': 'INFO'
            }
        }
        self.os_matcher.update_progress(
            name='host1',
            state=state,
            log_history_mapping=log_history_mapping
        )
        self.assertEqual(0.6, state['percentage'])


class TestPackageMatcher(unittest2.TestCase):
    def setUp(self):
        super(TestPackageMatcher, self).setUp()
        logsetting.init()
        file_matchers = [
            FileMatcher(
                min_progress=0.6,
                max_progress=0.9,
                filename='test_log',
                line_matchers={
                    'start': LineMatcher(
                        pattern=r'',
                        severity='',
                    )
                }
            )
        ]
        self.item_matcher = adapter_matcher.AdapterItemMatcher(file_matchers)
        self.file_reader_factory = FileReaderFactory(
            logdir=os.path.dirname(
                os.path.abspath(__file__)) + '/data'
        )
        self.package_matcher = adapter_matcher.PackageMatcher(
            package_installer_name='chef',
            adapter_pattern=r'openstack',
            item_matcher=self.item_matcher,
            file_reader_factory=self.file_reader_factory
        )

    def tearDown(self):
        super(TestPackageMatcher, self).tearDown()

    def test_match_none(self):
        test_match_none = {
            'package_installer_name': None,
            'adapter_name': 'openstack'
        }
        matcher = self.package_matcher.match(**test_match_none)
        self.assertFalse(matcher)

    def test_match(self):
        test_match = {
            'package_installer_name': 'chef',
            'adapter_name': 'openstack'
        }
        matcher = self.package_matcher.match(**test_match)
        self.assertTrue(matcher)

    def test_installer_unmatch(self):
        test_unmatch = {
            'package_installer_name': 'dummy',
            'adapter_name': 'openstack'
        }
        matcher = self.package_matcher.match(**test_unmatch)
        self.assertFalse(matcher)

    def test_name_unmatch(self):
        test_unmatch = {
            'package_installer_name': 'chef',
            'adapter_name': 'dummy'
        }
        matcher = self.package_matcher.match(**test_unmatch)
        self.assertFalse(matcher)

    def test_both_unmatch(self):
        test_unmatch = {
            'package_installer_name': 'dummy',
            'adapter_name': 'dummy'
        }
        matcher = self.package_matcher.match(**test_unmatch)
        self.assertFalse(matcher)

    def test_update_progress(self):
        state = {
            'message': 'dummy',
            'severity': 'dummy',
            'percentage': 0.5
        }
        log_history_mapping = {
            'test_log': {
                'filename': 'test_log',
                'partial_line': '',
                'position': 0,
                'line_matcher_name': 'start',
                'percentage': 0.0,
                'message': '',
                'severity': 'INFO'
            }
        }
        self.package_matcher.update_progress(
            name='host1',
            state=state,
            log_history_mapping=log_history_mapping
        )
        self.assertEqual(0.6, state['percentage'])


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
