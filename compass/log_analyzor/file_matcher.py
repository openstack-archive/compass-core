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

"""Module to update intalling progress by processing log file.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import logging
import os.path

from compass.utils import setting_wrapper as setting


class FileFilter(object):
    """base class to filter log file."""
    def __repr__(self):
        return self.__class__.__name__

    def filter(self, pathname):
        """Filter log file.

        :param pathname: the absolute path name to the log file.
        """
        raise NotImplementedError(str(self))


class CompositeFileFilter(FileFilter):
    """filter log file based on the list of filters."""
    def __init__(self, filters):
        self.filters_ = filters

    def __str__(self):
        return 'CompositeFileFilter[%s]' % self.filters_

    def append_filter(self, file_filter):
        """append filter."""
        self.filters_.append(file_filter)

    def filter(self, pathname):
        """filter log file."""
        for file_filter in self.filters_:
            if not file_filter.filter(pathname):
                return False

        return True


class FilterFileExist(FileFilter):
    """filter log file if not exists."""
    def filter(self, pathname):
        """filter log file."""
        file_exist = os.path.isfile(pathname)
        if not file_exist:
            logging.debug("%s is not exist", pathname)

        return file_exist


def get_file_filter():
    """get file filter"""
    composite_filter = CompositeFileFilter([FilterFileExist()])
    return composite_filter


class FileReader(object):
    """Class to read log file.

    The class provide support to read log file from the position
    it has read last time. and update the position when it finish
    reading the log.
    """
    def __init__(self, pathname, log_history):
        self.pathname_ = pathname
        self.log_history_ = log_history

    def __repr__(self):
        return (
            '%s[pathname:%s, log_history:%s]' % (
                self.__class__.__name__, self.pathname_,
                self.log_history_
            )
        )

    def readline(self):
        """Generate each line of the log file."""
        old_position = self.log_history_['position']
        position = self.log_history_['position']
        partial_line = self.log_history_['partial_line']
        try:
            with open(self.pathname_) as logfile:
                logfile.seek(position)
                while True:
                    line = logfile.readline()
                    partial_line += line
                    position = logfile.tell()
                    if position > self.log_history_['position']:
                        self.log_history_['position'] = position

                    if partial_line.endswith('\n'):
                        self.log_history_['partial_line'] = ''
                        yield partial_line
                        partial_line = self.log_history_['partial_line']
                    else:
                        self.log_history_['partial_line'] = partial_line
                        break
                if partial_line:
                    yield partial_line

        except Exception as error:
            logging.error('failed to processing file %s', self.pathname_)
            raise error

        logging.debug(
            'processing file %s log %s bytes to position %s',
            self.pathname_, position - old_position, position
        )


class FileReaderFactory(object):
    """factory class to create FileReader instance."""

    def __init__(self, logdir):
        self.logdir_ = logdir
        self.filefilter_ = get_file_filter()

    def __str__(self):
        return '%s[logdir: %s filefilter: %s]' % (
            self.__class__.__name__, self.logdir_, self.filefilter_)

    def get_file_reader(self, hostname, filename, log_history):
        """Get FileReader instance.

        :param fullname: fullname of installing host.
        :param filename: the filename of the log file.

        :returns: :class:`FileReader` instance if it is not filtered.
        """
        pathname = os.path.join(self.logdir_, hostname, filename)
        logging.debug('get FileReader from %s', pathname)
        if not self.filefilter_.filter(pathname):
            logging.debug('%s is filtered', pathname)
            return None

        return FileReader(pathname, log_history)


class FileMatcher(object):
    """File matcher to get the installing progress from the log file."""
    def __init__(self, line_matchers, min_progress, max_progress, filename):
        if not 0.0 <= min_progress <= max_progress <= 1.0:
            raise IndexError(
                '%s restriction is not mat: 0.0 <= min_progress'
                '(%s) <= max_progress(%s) <= 1.0' % (
                    self.__class__.__name__,
                    min_progress,
                    max_progress))
        if 'start' not in line_matchers:
            raise KeyError(
                'key `start` does not in line matchers %s' % line_matchers
            )
        self.line_matchers_ = line_matchers
        self.min_progress_ = min_progress
        self.max_progress_ = max_progress
        self.progress_diff_ = max_progress - min_progress
        self.filename_ = filename

    def __repr__(self):
        return (
            '%r[filename: %r, progress:[%r:%r], '
            'line_matchers: %r]' % (
                self.__class__.__name__, self.filename_,
                self.min_progress_,
                self.max_progress_, self.line_matchers_)
        )

    def update_progress_from_log_history(self, state, log_history):
        file_percentage = log_history['percentage']
        percentage = max(
            self.min_progress_,
            min(
                self.max_progress_,
                self.min_progress_ + file_percentage * self.progress_diff_
            )
        )
        if (
            percentage > state['percentage'] or
            (
                percentage == state['percentage'] and
                log_history['message'] != state['message']
            )
        ):
            state['percentage'] = percentage
            state['message'] = log_history['message']
            state['severity'] = log_history['severity']
        else:
            logging.debug(
                'ingore update state %s from log history %s '
                'since the updated progress %s lag behind',
                state, log_history, percentage
            )

    def update_progress(self, file_reader_factory, name, state, log_history):
        """update progress from file.

        :param fullname: the fullname of the installing host.
        :type fullname: str
        :param total_progress: Progress instance to update.

        the function update installing progress by reading the log file.
        It contains a list of line matcher, when one log line matches
        with current line matcher, the installing progress is updated.
        and the current line matcher got updated.
        Notes: some line may be processed multi times. The case is the
        last line of log file is processed in one run, while in the other
        run, it will be reprocessed at the beginning because there is
        no line end indicator for the last line of the file.
        """
        file_reader = file_reader_factory.get_file_reader(
            name, self.filename_, log_history)
        if not file_reader:
            return

        line_matcher_name = log_history['line_matcher_name']
        for line in file_reader.readline():
            if line_matcher_name not in self.line_matchers_:
                logging.debug('early exit at\n%s\nbecause %s is not in %s',
                              line, line_matcher_name, self.line_matchers_)
                break

            same_line_matcher_name = line_matcher_name
            while same_line_matcher_name in self.line_matchers_:
                line_matcher = self.line_matchers_[same_line_matcher_name]
                same_line_matcher_name, line_matcher_name = (
                    line_matcher.update_progress(line, log_history)
                )
        log_history['line_matcher_name'] = line_matcher_name
        logging.debug(
            'updated log history %s after processing %s',
            log_history, self
        )
        self.update_progress_from_log_history(state, log_history)
