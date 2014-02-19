"""Module to provider installing progress calculation for the adapter.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import logging
import re

from compass.db import database
from compass.db.model import Cluster, ClusterHost
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

    def update_progress(self, hostname, clusterid, progress):
        """Update progress.

        :param hostname: the hostname of the installing host.
        :type hostname: str
        :param clusterid: the cluster id of the installing host.
        :type clusterid: int
        :param progress: Progress instance to update.
        """
        for file_matcher in self.file_matchers_:
            file_matcher.update_progress(hostname, clusterid, progress)


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

    def update_progress(self, hostname, clusterid, progress):
        """Update progress."""
        self.matcher_.update_progress(hostname, clusterid, progress)


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

    def update_progress(self, hostname, clusterid, progress):
        """Update progress."""
        self.matcher_.update_progress(hostname, clusterid, progress)


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
            ClusterHost).filter_by(
            id=hostid).first()
        if not host:
            logging.error(
                'there is no host for %s in ClusterHost', hostid)
            return None, None, None

        if not host.state:
            logging.error('there is no related HostState for %s',
                          hostid)
            return host.hostname, None, None

        return (
            host.hostname,
            host.state.state,
            Progress(host.state.progress,
                     host.state.message,
                     host.state.severity))

    @classmethod
    def _update_host_progress(cls, hostid, progress):
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

        if host.state.state != 'INSTALLING':
            logging.error(
                'host %s is not in INSTALLING state',
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
        host_progresses = {}
        with database.session():
            for hostid in hostids:
                hostname, host_state, host_progress = (
                    self._get_host_progress(hostid))
                if not hostname or not host_progress:
                    logging.error(
                        'nothing to update host %s => hostname %s '
                        'state %s progress %s',
                        hostid, hostname, host_state, host_progress)
                    continue

                logging.debug('got host %s hostname %s state %s progress %s',
                              hostid, hostname, host_state, host_progress)
                host_progresses[hostid] = (
                    hostname, host_state, host_progress)

        for hostid, host_value in host_progresses.items():
            hostname, host_state, host_progress = host_value
            if host_state == 'INSTALLING' and host_progress.progress < 1.0:
                self.os_matcher_.update_progress(
                    hostname, clusterid, host_progress)
                self.package_matcher_.update_progress(
                    hostname, clusterid, host_progress)
            else:
                logging.error(
                    'there is no need to update host %s '
                    'progress: hostname %s state %s progress %s',
                    hostid, hostname, host_state, host_progress)

        with database.session():
            for hostid in hostids:
                if hostid not in host_progresses:
                    continue

                _, _, host_progress = host_progresses[hostid]
                self._update_host_progress(hostid, host_progress)

            self._update_cluster_progress(clusterid)
