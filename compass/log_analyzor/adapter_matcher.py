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

"""Module to provider installing progress calculation for the adapter.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import logging
import re


class AdapterItemMatcher(object):
    """Progress matcher for the os installing or package installing."""

    def __init__(self, file_matchers):
        self.file_matchers_ = file_matchers

    def __repr__(self):
        return '%r[file_matchers: %r]' % (
            self.__class__.__name__, self.file_matchers_
        )

    def update_progress(
        self, file_reader_factory, name, state, log_history_mapping
    ):
        """Update progress.

        :param name: the fullname of the installing host.
        :type name: str
        :param progress: Progress instance to update.
        """
        for file_matcher in self.file_matchers_:
            filename = file_matcher.filename_
            if filename not in log_history_mapping:
                log_history_mapping[filename] = {
                    'filename': filename,
                    'partial_line': '',
                    'position': 0,
                    'line_matcher_name': 'start',
                    'percentage': 0.0,
                    'message': '',
                    'severity': 'INFO'
                }
            log_history = log_history_mapping[filename]
            file_matcher.update_progress(
                file_reader_factory, name, state, log_history
            )


class OSMatcher(object):
    """Progress matcher for os installer."""

    def __init__(
        self, os_installer_name,
        os_pattern, item_matcher,
        file_reader_factory
    ):
        self.name_ = re.compile(os_installer_name)
        self.os_regex_ = re.compile(os_pattern)
        self.matcher_ = item_matcher
        self.file_reader_factory_ = file_reader_factory

    def __repr__(self):
        return '%r[name:%r, os_pattern:%r, matcher:%r]' % (
            self.__class__.__name__, self.name_.pattern,
            self.os_regex_.pattern, self.matcher_)

    def match(self, os_installer_name, os_name):
        """Check if the os matcher is acceptable."""
        if os_name is None:
            return False
        else:
            return all([
                self.name_.match(os_installer_name),
                self.os_regex_.match(os_name)
            ])

    def update_progress(self, name, state, log_history_mapping):
        """Update progress."""
        self.matcher_.update_progress(
            self.file_reader_factory_, name, state, log_history_mapping)


class PackageMatcher(object):
    """Progress matcher for package installer."""

    def __init__(
        self, package_installer_name, adapter_pattern,
        item_matcher, file_reader_factory
    ):
        self.name_ = re.compile(package_installer_name)
        self.adapter_regex_ = re.compile(adapter_pattern)
        self.matcher_ = item_matcher
        self.file_reader_factory_ = file_reader_factory

    def __repr__(self):
        return '%s[name:%s, adapter_pattern:%s, matcher:%s]' % (
            self.__class__.__name__, self.name_.pattern,
            self.adapter_regex_.pattern, self.matcher_)

    def match(self, package_installer_name, adapter_name):
        """Check if the package matcher is acceptable."""
        if package_installer_name is None:
            return False
        else:
            return all([
                self.name_.match(package_installer_name),
                self.adapter_regex_.match(adapter_name)
            ])

    def update_progress(self, name, state, log_history_mapping):
        """Update progress."""
        self.matcher_.update_progress(
            self.file_reader_factory_, name, state, log_history_mapping
        )
