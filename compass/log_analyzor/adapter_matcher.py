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

from compass.db import database
from compass.db.model import Cluster
from compass.db.model import ClusterHost
from compass.log_analyzor.line_matcher import Progress


class AdapterItemMatcher(object):
    """Progress matcher for the os installing or package installing."""

    def __init__(self, file_matchers):
        self.file_matchers_ = file_matchers
        self.min_progress_ = 0.0
        self.max_progress_ = 1.0

    def update_progress_range(self, min_progress, max_progress):
        """update min_progress and max_progress."""
        self.min_progress_ = min_progress
        self.max_progress_ = max_progress
        for file_matcher in self.file_matchers_:
            file_matcher.update_absolute_progress_range(
                self.min_progress_, self.max_progress_)

    def __str__(self):
        return '%s[file_matchers: %s, min_progress: %s, max_progress: %s]' % (
            self.__class__.__name__, self.file_matchers_,
            self.min_progress_, self.max_progress_)

    def update_progress(self, fullname, progress):
        """Update progress.

        :param fullname: the fullname of the installing host.
        :type fullname: str
        :param progress: Progress instance to update.
        """
        for file_matcher in self.file_matchers_:
            file_matcher.update_progress(fullname, progress)


class OSMatcher(object):
    """Progress matcher for os installer."""

    def __init__(self, os_installer_name, os_pattern,
                 item_matcher, min_progress, max_progress):
        if not (0.0 <= min_progress <= max_progress <= 1.0):
            raise IndexError('%s restriction not mat:'
                             '0.0 <= min_progress(%s) '
                             '<= max_progress(%s) <= 1.0' % (
                                 self.__class__.__name__,
                                 min_progress, max_progress))

        self.name_ = os_installer_name
        self.os_regex_ = re.compile(os_pattern)
        self.matcher_ = item_matcher
        self.matcher_.update_progress_range(min_progress, max_progress)

    def __repr__(self):
        return '%s[name:%s, os_pattern:%s, matcher:%s]' % (
            self.__class__.__name__, self.name_,
            self.os_regex_.pattern, self.matcher_)

    def match(self, os_installer_name, os_name):
        """Check if the os matcher is acceptable."""
        return all([
            self.name_ == os_installer_name,
            self.os_regex_.match(os_name)])

    def update_progress(self, fullname, progress):
        """Update progress."""
        logging.debug('selfname: %s', self.name_)
        self.matcher_.update_progress(fullname, progress)


class PackageMatcher(object):
    """Progress matcher for package installer."""

    def __init__(self, package_installer_name, target_system,
                 item_matcher, min_progress, max_progress):
        if not (0.0 <= min_progress <= max_progress <= 1.0):
            raise IndexError('%s restriction not mat:'
                             '0.0 <= min_progress(%s) '
                             '<= max_progress(%s) <= 1.0' % (
                                 self.__class__.__name__,
                                 min_progress, max_progress))

        self.name_ = package_installer_name
        self.target_system_ = target_system
        self.matcher_ = item_matcher
        self.matcher_.update_progress_range(min_progress, max_progress)

    def __repr__(self):
        return '%s[name:%s, target_system:%s, matcher:%s]' % (
            self.__class__.__name__, self.name_,
            self.target_system_, self.matcher_)

    def match(self, package_installer_name, target_system):
        """Check if the package matcher is acceptable."""
        return all([
            self.name_ == package_installer_name,
            self.target_system_ == target_system])

    def update_progress(self, fullname, progress):
        """Update progress."""
        self.matcher_.update_progress(fullname, progress)


class AdapterMatcher(object):
    """Adapter matcher to update adapter installing progress."""

    def __init__(self, os_matcher, package_matcher):
        self.os_matcher_ = os_matcher
        self.package_matcher_ = package_matcher

    def match(self, os_installer_name, os_name,
              package_installer_name, target_system):
        """Check if the adapter matcher is acceptable.

        :param os_installer_name: the os installer name.
        :type os_installer_name: str
        :param os_name: the os name.
        :type os_name: str
        :param package_installer_name: the package installer name.
        :type package_installer_name: str
        :param target_system: the target system to deploy
        :type target_system: str

        :returns: bool

           .. note::
              Return True if the AdapterMatcher can process the log files
              generated from the os installation and package installation.
        """
        return all([
            self.os_matcher_.match(os_installer_name, os_name),
            self.package_matcher_.match(
                package_installer_name, target_system)])

    def __str__(self):
        return '%s[os_matcher:%s, package_matcher:%s]' % (
            self.__class__.__name__,
            self.os_matcher_, self.package_matcher_)

    @classmethod
    def _get_host_progress(cls, hostid):
        """Get Host Progress from database.

        .. notes::
           The function should be called in database session.
        """
        session = database.current_session()
        host = session.query(
            ClusterHost
        ).filter_by(id=hostid).first()
        if not host:
            logging.error(
                'there is no host for %s in ClusterHost', hostid)
            return None, None, None

        if not host.state:
            logging.error('there is no related HostState for %s',
                          hostid)
            return host.fullname, None, None

        """
        return (
            host.fullname,
            host.state.state,
            Progress(host.state.progress,
                     host.state.message,
                     host.state.severity))
        """
        return {
            'os': (
                host.fullname,
                host.state.state,
                Progress(host.state.os_progress,
                         host.state.os_message,
                         host.state.os_severity)),
            'package': (
                host.fullname,
                host.state.state,
                Progress(host.state.progress,
                         host.state.message,
                         host.state.severity))}

    @classmethod
    def _update_host_os_progress(cls, hostid, os_progress):
        """Update host progress to database.

        .. note::
           The function should be called in database session.
        """
        session = database.current_session()
        host = session.query(
            ClusterHost).filter_by(id=hostid).first()
        if not host:
            logging.error(
                'there is no host for %s in ClusterHost', hostid)
            return

        if not host.state:
            logging.error(
                'there is no related HostState for %s', hostid)
            return

        logging.debug('os progress: %s', os_progress.progress)

        if host.state.os_progress > os_progress.progress:
            logging.error(
                'host %s os_progress is not increased '
                'from %s to %s',
                hostid, host.state, os_progress)
            return
        if (
            host.state.os_progress == os_progress.progress and
            host.state.os_message == os_progress.message
        ):
            logging.info(
                'ignore update host %s progress %s to %s',
                hostid, os_progress, host.state)
            return

        host.state.os_progress = os_progress.progress
        """host.state.os_progress = progress.progress"""
        host.state.os_message = os_progress.message
        if os_progress.severity:
            host.state.os_severity = os_progress.severity

        if host.state.os_progress >= 1.0:
            host.state.os_state = 'OS_READY'

        if host.state.os_severity == 'ERROR':
            host.state.os_state = 'ERROR'

        if host.state.os_state != 'INSTALLING':
            host.mutable = True

        logging.debug(
            'update host %s state %s',
            hostid, host.state)

    @classmethod
    def _update_host_package_progress(cls, hostid, progress):
        """Update host progress to database.

        .. note::
           The function should be called in database session.
        """
        session = database.current_session()
        host = session.query(
            ClusterHost).filter_by(id=hostid).first()

        logging.debug('package progress: %s', progress.progress)
        logging.debug('package ssssstate: %s', host.state.state)
        if not host:
            logging.error(
                'there is no host for %s in ClusterHost', hostid)
            return

        if not host.state:
            logging.error(
                'there is no related HostState for %s', hostid)
            return

        if not host.state.state in ['OS_READY', 'INSTALLING']:
            logging.error(
                'host %s issssss not in INSTALLING state',
                hostid)
            return

        if host.state.progress > progress.progress:
            logging.error(
                'host %s progress is not increased '
                'from %s to %s',
                hostid, host.state, progress)
            return

        if (
            host.state.progress == progress.progress and
            host.state.message == progress.message
        ):
            logging.info(
                'ignore update host %s progress %s to %s',
                hostid, progress, host.state)
            return

        host.state.progress = progress.progress
        host.state.message = progress.message
        if progress.severity:
            host.state.severity = progress.severity

        if host.state.progress >= 1.0:
            host.state.state = 'READY'

        if host.state.severity == 'ERROR':
            host.state.state = 'ERROR'

        if host.state.state != 'INSTALLING':
            host.mutable = True

        logging.debug(
            'update host %s state %s',
            hostid, host.state)

    @classmethod
    def _update_cluster_progress(cls, clusterid):
        """Update cluster installing progress to database.

        .. note::
           The function should be called in the database session.
        """
        session = database.current_session()
        cluster = session.query(
            Cluster).filter_by(id=clusterid).first()
        if not cluster:
            logging.error(
                'there is no cluster for %s in Cluster',
                clusterid)
            return

        if not cluster.state:
            logging.error(
                'there is no ClusterState for %s',
                clusterid)

        if cluster.state.state != 'INSTALLING':
            logging.error('cluster %s is not in INSTALLING state',
                          clusterid)
            return

        cluster_progress = 0.0
        cluster_messages = {}
        cluster_severities = set([])
        hostids = []
        for host in cluster.hosts:
            if host.state:
                hostids.append(host.id)
                cluster_progress += host.state.progress
                if host.state.message:
                    cluster_messages[host.hostname] = host.state.message

                if host.state.severity:
                    cluster_severities.add(host.state.severity)

        cluster.state.progress = cluster_progress / len(hostids)
        cluster.state.message = '\n'.join(
            [
                '%s: %s' % (hostname, message)
                for hostname, message in cluster_messages.items()
            ]
        )
        for severity in ['ERROR', 'WARNING', 'INFO']:
            if severity in cluster_severities:
                cluster.state.severity = severity
                break

        if cluster.state.progress >= 1.0:
            cluster.state.state = 'READY'

        if cluster.state.severity == 'ERROR':
            cluster.state.state = 'ERROR'

        if cluster.state.state != 'INSTALLING':
            cluster.mutable = True

        logging.debug(
            'update cluster %s state %s',
            clusterid, cluster.state)

    def update_progress(self, clusterid, hostids):
        """Update cluster progress and hosts progresses.

        :param clusterid: the id of the cluster to update.
        :type clusterid: int.
        :param hostids: the ids of the hosts to update.
        :type hostids: list of int.
        """
        logging.debug('printing os_matcher %s', self.__str__())
        host_os_progresses = {}
        host_package_progresses = {}
        with database.session():
            for hostid in hostids:
                host_overall_state = (
                    self._get_host_progress(hostid))
                logging.debug('host overall state: %s', host_overall_state)
                fullname, host_state, host_os_progress = host_overall_state['os']
                _, _, host_package_progress = host_overall_state['package']
                if not fullname or not host_os_progress or not host_package_progress:
                    logging.error(
                        'nothing to update host %s',
                        fullname)
                    continue

                logging.debug('got host %s state %s os_progress %s'
                              'package_progress %s',
                              fullname, host_state, host_os_progress, host_package_progress)

                host_os_progresses[hostid] = (
                    fullname, host_state, host_os_progress)
                host_package_progresses[hostid] = (
                    fullname, host_state, host_package_progress)

        for hostid, host_value in host_os_progresses.items():
            fullname, host_state, host_os_progress = host_value
            if host_state == 'INSTALLING' and host_os_progress.progress < 1.0:
                self.os_matcher_.update_progress(
                    fullname, host_os_progress)
            else:
                logging.error(
                    'there is no need to update host %s '
                    'OS progress: state %s os_progress %s',
                    fullname, host_state, host_os_progress)

        for hostid, host_value in host_package_progresses.items():
            fullname, host_state,host_package_progress = host_value
            if host_state == 'INSTALLING' and host_package_progress.progress < 1.0:
                self.package_matcher_.update_progress(
                    fullname, host_package_progress)
            else:
                logging.error(
                    'there is no need to update host %s '
                    'Package progress: state %s package_progress %s',
                    fullname, host_state, host_package_progress)

        with database.session():
            for hostid in hostids:
                if hostid not in host_os_progresses:
                    continue

                if hostid not in host_package_progresses:
                    continue

                _, _, host_os_progress = host_os_progresses[hostid]
                _, _, host_package_progress = host_package_progresses[hostid]
                self._update_host_os_progress(hostid, host_os_progress)
                self._update_host_package_progress(hostid, host_package_progress)

            self._update_cluster_progress(clusterid)
