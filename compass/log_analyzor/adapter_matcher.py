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

from compass.db.api import cluster as cluster_api
from compass.db.api import database
from compass.db.api import host as host_api
from compass.db.api import user as user_api

from compass.db.models import Cluster
from compass.db.models import ClusterHost
from compass.db.models import Host

from compass.log_analyzor.line_matcher import Progress

import datetime


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
        """Get Host Progress from HostState."""

        session = database.current_session()
        host = session.query(
            Host
        ).filter_by(id=hostid).first()
        if not host:
            logging.error(
                'there is no host for %s in Host', hostid)
            return None, None, None

        if not host.state:
            logging.error('there is no related HostState for %s',
                          hostid)
            return host.name, None, None

        return (
            host.name,
            host.state.state,
            Progress(host.state.percentage,
                     host.state.message,
                     host.state.severity))

    @classmethod
    def _get_clusterhost_progress(cls, hostid):
        """Get ClusterHost progress from ClusterHostState."""

        session = database.current_session()
        clusterhost = session.query(
            ClusterHost
        ).filter_by(id=hostid).first()
        if not clusterhost:
            logging.error(
                'there is no clusterhost for %s in ClusterHost',
                hostid
            )
            return None, None, None

        if not clusterhost.state:
            logging.error(
                'there is no related ClusterHostState for %s',
                hostid
            )
            return clusterhost.name, None, None

        return (
            clusterhost.name,
            clusterhost.state.state,
            Progress(clusterhost.state.percentage,
                     clusterhost.state.message,
                     clusterhost.state.severity))

    @classmethod
    def _update_host_progress(cls, hostid, host_progress, updater):
        """Updates host progress to db."""

        session = database.current_session()
        host = session.query(
            Host).filter_by(id=hostid).first()
        if not host:
            logging.error(
                'there is no host for %s in table Host',
                hostid
            )

        if not host.state:
            logging.error(
                'there is no related HostState for %s',
                hostid
            )

        if host.state.percentage > host_progress.progress:
            logging.error(
                'host %s progress has not been increased'
                ' from %s to $s',
                hostid, host.state, host_progress
            )
            return

        if (host.state.percentage == host_progress.progress and
                host.state.message == host_progress.message):
            logging.info(
                'host %s update ignored due to same progress'
                'in database',
                hostid
            )
            return

        host.state.percentage = host_progress.progress
        host.state.message = host_progress.message
        if host_progress.severity:
            host.state.severity = host_progress.severity

        if host.state.percentage >= 1.0:
            host.state.state = 'SUCCESSFUL'

        if host.state.severity == 'ERROR':
            host.state.state = 'ERROR'

        if host.state.state != 'INSTALLING':
            host.mutable = True

        host_api.update_host_state(
            session,
            updater,
            hostid,
            state=host.state.state,
            percentage=host.state.percentage,
            message=host.state.message,
            id=hostid
        )

        logging.debug(
            'update host %s state %s',
            hostid, host.state)

    @classmethod
    def _update_clusterhost_progress(
        cls,
        hostid,
        clusterhost_progress,
        updater
    ):

        session = database.current_session()
        clusterhost = session.query(
            ClusterHost).filter_by(id=hostid).first()

        if not clusterhost.state:
            logging.error(
                'ClusterHost state not found for %s',
                hostid)

        if clusterhost.state.percentage > clusterhost_progress.progress:
            logging.error(
                'clusterhost %s state has not been increased'
                ' from %s to %s',
                hostid, clusterhost.state, clusterhost_progress
            )
            return

        if (clusterhost.state.percentage == clusterhost_progress.progress and
                clusterhost.state.message == clusterhost_progress.message):
            logging.info(
                'clusterhost %s update ignored due to same progress'
                'in database',
                hostid
            )
            return

        clusterhost.state.percentage = clusterhost_progress.progress
        clusterhost.state.message = clusterhost_progress.message
        if clusterhost_progress.severity:
            clusterhost.state.severity = clusterhost_progress.severity

        if clusterhost.state.percentage >= 1.0:
            clusterhost.state.state = 'SUCCESSFUL'

        if clusterhost.state.severity == 'ERROR':
            clusterhost.state.state = 'ERROR'

        if clusterhost.state.state != 'INSTALLING':
            clusterhost.mutable = True

        cluster_api.update_clusterhost_state(
            session,
            updater,
            hostid,
            state=clusterhost.state.state,
            percentage=clusterhost.state.percentage,
            message=clusterhost.state.message
        )

        logging.debug(
            'update clusterhost %s state %s',
            hostid, clusterhost.state)

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
        cluster_installing_hosts = 0
        cluster_failed_hosts = 0
        hostids = []
        clusterhosts = cluster.clusterhosts
        hosts = [clusterhost.host for clusterhost in clusterhosts]
        for host in hosts:
            if host.state:
                hostids.append(host.id)
                cluster_progress += host.state.percentage
                if host.state.message:
                    cluster_messages[host.name] = host.state.message

                if host.state.severity:
                    cluster_severities.add(host.state.severity)

        for clusterhost in clusterhosts:
            if clusterhost.state:
                cluster_progress += clusterhost.state.percentage
                if clusterhost.state.state == 'INSTALLING':
                    cluster_installing_hosts += 1
                elif (clusterhost.host.state.state not in
                        ['ERROR', 'INITIALIZED'] and
                        clusterhost.state.state != 'ERORR'):
                    cluster_installing_hosts += 1
                elif (clusterhost.state.state == 'ERROR' or
                        clusterhost.host.state.state == 'ERROR'):
                    cluster_failed_hosts += 1

            if clusterhost.state.message:
                cluster_messages[host.name] = clusterhost.state.message

            if clusterhost.state.severity:
                cluster_severities.add(clusterhost.state.severity)

        cluster.state.percentage = cluster_progress / (len(hostids) * 2)
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

        if cluster.state.percentage >= 1.0:
            cluster.state.state = 'READY'

        if cluster.state.severity == 'ERROR':
            cluster.state.state = 'ERROR'

        if cluster.state.state != 'INSTALLING':
            cluster.mutable = True

        cluster.state.installing_hosts = cluster_installing_hosts
        cluster.state.total_hosts = len(clusterhosts)
        cluster.state.failed_hosts = cluster_failed_hosts
        cluster.state.completed_hosts = cluster.state.total_hosts - \
            cluster.state.installing_hosts - cluster.state.failed_hosts

        logging.debug(
            'update cluster %s state %s',
            clusterid, cluster.state)

    def update_progress(self, clusterid, hostids):

        host_progresses = {}
        clusterhost_progresses = {}
        updater = user_api.get_user_object(
            'admin@abc.com',
            expire_timestamp=datetime.datetime.now() +
            datetime.timedelta(seconds=10000))
        with database.session():
            for hostid in hostids:
                host_name, host_state, host_progress = \
                    self._get_host_progress(hostid)
                _, clusterhost_state, clusterhost_progress = \
                    self._get_clusterhost_progress(hostid)

                if (not host_name or
                        not host_progress or
                        not clusterhost_progress):
                    logging.error(
                        'nothing to update host %s',
                        host_name)
                    continue

                logging.debug('got host %s host_state: %s '
                              'host_progress: %s, '
                              'clusterhost_state: %s, '
                              'clusterhost_progress: %s ',
                              host_name,
                              host_state,
                              host_progress,
                              clusterhost_state,
                              clusterhost_progress)

                host_progresses[hostid] = (
                    host_name, host_state, host_progress)
                clusterhost_progresses[hostid] = (
                    host_name, clusterhost_state, clusterhost_progress)

            for hostid, host_value in host_progresses.items():
                host_name, host_state, host_progress = host_value
                if (host_state == 'INSTALLING' and
                        host_progress.progress < 1.0):
                    self.os_matcher_.update_progress(
                        host_name, host_progress)
                else:
                    logging.error(
                        'there is no need to update host %s '
                        'progress: state %s progress %s',
                        host_name, host_state, host_progress)

            for hostid, clusterhost_value in clusterhost_progresses.items():
                host_name, clusterhost_state, clusterhost_progress = \
                    clusterhost_value
                if (clusterhost_state == 'INSTALLING' and
                        clusterhost_progress.progress < 1.0):
                    self.package_matcher_.update_progress(
                        host_name, clusterhost_progress)
                else:
                    logging.error(
                        'no need  to update clusterhost %s'
                        'progress: state %s progress %s',
                        host_name, clusterhost_state, clusterhost_progress)

            for hostid in hostids:
                if hostid not in host_progresses:
                    continue
                if hostid not in clusterhost_progresses:
                    continue

                _, _, host_progress = host_progresses[hostid]
                _, _, clusterhost_progress = clusterhost_progresses[hostid]
                self._update_host_progress(hostid, host_progress, updater)
                self._update_clusterhost_progress(
                    hostid,
                    clusterhost_progress,
                    updater
                )

            self._update_cluster_progress(clusterid)
