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

"""Module to get the progress when found match with a line of the log."""
import logging
import re

from abc import ABCMeta

from compass.utils import util


class ProgressCalculator(object):
    """base class to generate progress."""

    __metaclass__ = ABCMeta

    @classmethod
    def update_progress(
        cls, progress_data, message,
        severity, log_history
    ):
        """Update progress with the given progress_data, message and severity.

        :param progress_data: installing progress.
        :type progress_data: float between 0 to 1.
        :param message: installing progress message.
        :param severity: installing message severity.
        :param progress: :class:`Progress` instance to update
        """
        # the progress is only updated when the new progress
        # is greater than the stored progress or the progress
        # to update is the same but the message is different.
        if (
            progress_data > log_history['percentage'] or (
                progress_data == log_history['percentage'] and
                message != log_history['message']
            )
        ):
            log_history['percentage'] = progress_data
            if message:
                log_history['message'] = message
            if severity:
                log_history['severity'] = severity
            logging.debug('update progress to %s', log_history)
        else:
            logging.debug('ignore update progress %s to %s',
                          progress_data, log_history)

    def update(self, message, severity, log_history):
        """vritual method to update progress by message and severity.

        :param message: installing message.
        :param severity: installing severity.
        """
        raise NotImplementedError(str(self))

    def __repr__(self):
        return self.__class__.__name__


class IncrementalProgress(ProgressCalculator):
    """Class to increment the progress."""

    def __init__(self, min_progress,
                 max_progress, incremental_ratio):
        super(IncrementalProgress, self).__init__()
        if not 0.0 <= min_progress <= max_progress <= 1.0:
            raise IndexError(
                '%s restriction is not mat: 0.0 <= min_progress(%s)'
                ' <= max_progress(%s) <= 1.0' % (
                    self.__class__.__name__, min_progress, max_progress))

        if not 0.0 <= incremental_ratio <= 1.0:
            raise IndexError(
                '%s restriction is not mat: '
                '0.0 <= incremental_ratio(%s) <=  1.0' % (
                    self.__class__.__name__, incremental_ratio))

        self.min_progress_ = min_progress
        self.max_progress_ = max_progress
        self.incremental_progress_ = (
            incremental_ratio * (max_progress - min_progress))

    def __str__(self):
        return '%s[%s:%s:%s]' % (
            self.__class__.__name__,
            self.min_progress_,
            self.max_progress_,
            self.incremental_progress_
        )

    def update(self, message, severity, log_history):
        """update progress from message and severity."""
        progress_data = max(
            self.min_progress_,
            min(
                self.max_progress_,
                log_history['percentage'] + self.incremental_progress_
            )
        )
        self.update_progress(progress_data,
                             message, severity, log_history)


class RelativeProgress(ProgressCalculator):
    """class to update progress to the given relative progress."""

    def __init__(self, progress):
        super(RelativeProgress, self).__init__()
        if not 0.0 <= progress <= 1.0:
            raise IndexError(
                '%s restriction is not mat: 0.0 <= progress(%s) <= 1.0' % (
                    self.__class__.__name__, progress))

        self.progress_ = progress

    def __str__(self):
        return '%s[%s]' % (self.__class__.__name__, self.progress_)

    def update(self, message, severity, log_history):
        """update progress from message and severity."""
        self.update_progress(
            self.progress_, message, severity, log_history)


class SameProgress(ProgressCalculator):
    """class to update message and severity for  progress."""

    def update(self, message, severity, log_history):
        """update progress from the message and severity."""
        self.update_progress(log_history['percentage'], message,
                             severity, log_history)


class LineMatcher(object):
    """Progress matcher for each line."""

    def __init__(self, pattern, progress=None,
                 message_template='', severity=None,
                 unmatch_sameline_next_matcher_name='',
                 unmatch_nextline_next_matcher_name='',
                 match_sameline_next_matcher_name='',
                 match_nextline_next_matcher_name=''):
        self.regex_ = re.compile(pattern)
        if not progress:
            self.progress_ = SameProgress()
        elif isinstance(progress, ProgressCalculator):
            self.progress_ = progress
        elif isinstance(progress, (int, long, float)):
            self.progress_ = RelativeProgress(progress)
        else:
            raise TypeError(
                'progress unsupport type %s: %s' % (
                    type(progress), progress))

        self.message_template_ = message_template
        self.severity_ = severity
        self.unmatch_sameline_ = unmatch_sameline_next_matcher_name
        self.unmatch_nextline_ = unmatch_nextline_next_matcher_name
        self.match_sameline_ = match_sameline_next_matcher_name
        self.match_nextline_ = match_nextline_next_matcher_name

    def __repr__(self):
        return '%r[pattern:%r, message_template:%r, severity:%r]' % (
            self.__class__.__name__, self.regex_.pattern,
            self.message_template_, self.severity_)

    def update_progress(self, line, log_history):
        """Update progress by the line.

        :param line: one line in log file to indicate the installing progress.
           .. note::
              The line may be partial if the latest line of the log file is
              not the whole line. But the whole line may be resent
              in the next run.
        :param progress: the :class:`Progress` instance to update.
        """
        mat = self.regex_.search(line)
        if not mat:
            return (
                self.unmatch_sameline_,
                self.unmatch_nextline_)

        try:
            message = self.message_template_ % mat.groupdict()
        except Exception as error:
            logging.error('failed to get message %s %% %s in line matcher %s',
                          self.message_template_, mat.groupdict(), self)
            raise error

        self.progress_.update(message, self.severity_, log_history)
        return (
            self.match_sameline_,
            self.match_nextline_)
