"""Module to update intalling progress by processing log file.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import logging
import os.path

from compass.db import database
from compass.db.model import LogProgressingHistory
from compass.log_analyzor.line_matcher import Progress
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
    """filter log file based on the list of filters"""
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
            logging.error("%s is not exist", pathname)

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
    def __init__(self, pathname):
        self.pathname_ = pathname
        self.position_ = 0
        self.partial_line_ = ''

    def __repr__(self):
        return (
            '%s[pathname:%s, position:%s, partial_line:%s]' % (
                self.__class__.__name__, self.pathname_, self.position_,
                self.partial_line_
            )
        )

    def get_history(self):
        """Get log file read history from database.

        :returns: (line_matcher_name progress)

        .. note::
           The function should be called out of database session.
           It reads the log_progressing_history table to get the
           position in the log file it has read in last run,
           the partial line of the log, the line matcher name
           in the last run, the progress, the message and the
           severity it has got in the last run.
        """
        with database.session() as session:
            history = session.query(
                LogProgressingHistory).filter_by(
                pathname=self.pathname_).first()
            if history:
                self.position_ = history.position
                self.partial_line_ = history.partial_line
                line_matcher_name = history.line_matcher_name
                progress = Progress(history.progress,
                                    history.message,
                                    history.severity)
            else:
                line_matcher_name = 'start'
                progress = Progress(0.0, '', None)

            return line_matcher_name, progress

    def update_history(self, line_matcher_name, progress):
        """Update log_progressing_history table.

        :param line_matcher_name: the line matcher name.
        :param progress: Progress instance to record the installing progress.

        .. note::
           The function should be called out of database session.
           It updates the log_processing_history table.
        """
        with database.session() as session:
            history = session.query(LogProgressingHistory).filter_by(
                pathname=self.pathname_).first()

            if history:
                if history.position >= self.position_:
                    logging.error(
                        '%s history position %s is ahead of currrent '
                        'position %s',
                        self.pathname_,
                        history.position,
                        self.position_)
                    return

                history.position = self.position_
                history.partial_line = self.partial_line_
                history.line_matcher_name = line_matcher_name
                history.progress = progress.progress
                history.message = progress.message
                history.severity = progress.severity
            else:
                history = LogProgressingHistory(
                    pathname=self.pathname_, position=self.position_,
                    partial_line=self.partial_line_,
                    line_matcher_name=line_matcher_name,
                    progress=progress.progress,
                    message=progress.message,
                    severity=progress.severity)
                session.merge(history)
            logging.debug('update file %s to history %s',
                          self.pathname_, history)

    def readline(self):
        """Generate each line of the log file."""
        old_position = self.position_
        try:
            with open(self.pathname_) as logfile:
                logfile.seek(self.position_)
                while True:
                    line = logfile.readline()
                    self.partial_line_ += line
                    position = logfile.tell()
                    if position > self.position_:
                        self.position_ = position

                    if self.partial_line_.endswith('\n'):
                        yield_line = self.partial_line_
                        self.partial_line_ = ''
                        yield yield_line
                    else:
                        break

                if self.partial_line_:
                    yield self.partial_line_

        except Exception as error:
            logging.error('failed to processing file %s', self.pathname_)
            raise error

        logging.debug(
            'processing file %s log %s bytes to position %s',
            self.pathname_, self.position_ - old_position,
            self.position_)


class FileReaderFactory(object):
    """factory class to create FileReader instance."""

    def __init__(self, logdir, filefilter):
        self.logdir_ = logdir
        self.filefilter_ = filefilter

    def __str__(self):
        return '%s[logdir: %s filefilter: %s]' % (
            self.__class__.__name__, self.logdir_, self.filefilter_)

    def get_file_reader(self, hostname, clusterid, filename):
        """Get FileReader instance.

        :param hostname: hostname of installing host.
        :param clusterid: cluster id of the installing host.
        :param filename: the filename of the log file.

        :returns: :class:`FileReader` instance if it is not filtered.
        """
        pathname = os.path.join(
            self.logdir_, '%s.%s' % (hostname, clusterid),
            filename)
        logging.debug('get FileReader from %s', pathname)
        if not self.filefilter_.filter(pathname):
            logging.error('%s is filtered', pathname)
            return None

        return FileReader(pathname)


FILE_READER_FACTORY = FileReaderFactory(
    setting.INSTALLATION_LOGDIR, get_file_filter())


class FileMatcher(object):
    """
       File matcher the get the lastest installing progress
       from the log file.
    """
    def __init__(self, line_matchers, min_progress, max_progress, filename):
        if not 0.0 <= min_progress <= max_progress <= 1.0:
            raise IndexError(
                '%s restriction is not mat: 0.0 <= min_progress'
                '(%s) <= max_progress(%s) <= 1.0' % (
                    self.__class__.__name__,
                    min_progress,
                    max_progress))

        self.line_matchers_ = line_matchers
        self.min_progress_ = min_progress
        self.max_progress_ = max_progress
        self.absolute_min_progress_ = 0.0
        self.absolute_max_progress_ = 1.0
        self.absolute_progress_diff_ = 1.0
        self.filename_ = filename

    def update_absolute_progress_range(self, min_progress, max_progress):
        """update the min progress and max progress the log file indicates."""
        progress_diff = max_progress - min_progress
        self.absolute_min_progress_ = (
            min_progress + self.min_progress_ * progress_diff)
        self.absolute_max_progress_ = (
            min_progress + self.max_progress_ * progress_diff)
        self.absolute_progress_diff_ = (
            self.absolute_max_progress_ - self.absolute_min_progress_)

    def __str__(self):
        return (
            '%s[ filename: %s, progress range: [%s:%s], '
            'line_matchers: %s]' % (
                self.__class__.__name__, self.filename_,
                self.absolute_min_progress_,
                self.absolute_max_progress_, self.line_matchers_)
        )

    def update_total_progress(self, file_progress, total_progress):
        """Get the total progress from file progress."""
        if not file_progress.message:
            logging.info(
                'ignore update file %s progress %s to total progress',
                self.filename_, file_progress)
            return

        total_progress_data = min(
            self.absolute_min_progress_
                +
            file_progress.progress * self.absolute_progress_diff_,
            self.absolute_max_progress_)

        # total progress should only be updated when the new calculated
        # progress is greater than the recored total progress or the
        # progress to update is the same but the message is different.
        if (
            total_progress.progress < total_progress_data or (
                total_progress.progress == total_progress_data and
                total_progress.message != file_progress.message
            )
        ):
            total_progress.progress = total_progress_data
            total_progress.message = file_progress.message
            total_progress.severity = file_progress.severity
            logging.debug('update file %s total progress %s',
                          self.filename_, total_progress)
        else:
            logging.info(
                'ignore update file %s progress %s to total progress %s',
                self.filename_, file_progress, total_progress)

    def update_progress(self, hostname, clusterid, total_progress):
        """update progress from file.

        :param hostname: the hostname of the installing host.
        :type hostname: str
        :param clusterid: the cluster id of the installing host.
        :type clusterid: int
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
        file_reader = FILE_READER_FACTORY.get_file_reader(
            hostname, clusterid, self.filename_)
        if not file_reader:
            return

        line_matcher_name, file_progress = file_reader.get_history()
        for line in file_reader.readline():
            if line_matcher_name not in self.line_matchers_:
                logging.debug('early exit at\n%s\nbecause %s is not in %s',
                              line, line_matcher_name, self.line_matchers_)
                break

            index = line_matcher_name
            while index in self.line_matchers_:
                line_matcher = self.line_matchers_[index]
                index, line_matcher_name = line_matcher.update_progress(
                    line, file_progress)

        file_reader.update_history(line_matcher_name, file_progress)
        self.update_total_progress(file_progress, total_progress)
