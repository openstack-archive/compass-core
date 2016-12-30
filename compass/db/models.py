# Copyright 2014 Huawei Technologies Co. Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Database model"""
import copy
import datetime
import logging
import netaddr
import re
import simplejson as json

from sqlalchemy import BigInteger
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import ColumnDefault
from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy.orm import relationship, backref
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator
from sqlalchemy import UniqueConstraint

from compass.db import exception
from compass.utils import util


BASE = declarative_base()


class JSONEncoded(TypeDecorator):
    """Represents an immutable structure as a json-encoded string."""

    impl = Text

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


class TimestampMixin(object):
    """Provides table fields for each row created/updated timestamp."""
    created_at = Column(DateTime, default=lambda: datetime.datetime.now())
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(),
                        onupdate=lambda: datetime.datetime.now())


class HelperMixin(object):
    """Provides general fuctions for all compass table models."""

    def initialize(self):
        self.update()

    def update(self):
        pass

    @staticmethod
    def type_compatible(value, column_type):
        """Check if value type is compatible with the column type."""
        if value is None:
            return True
        if not hasattr(column_type, 'python_type'):
            return True
        column_python_type = column_type.python_type
        if isinstance(value, column_python_type):
            return True
        if issubclass(column_python_type, basestring):
            return isinstance(value, basestring)
        if column_python_type in [int, long]:
            return type(value) in [int, long]
        if column_python_type in [float]:
            return type(value) in [float]
        if column_python_type in [bool]:
            return type(value) in [bool]
        return False

    def validate(self):
        """Generate validate function to make sure the record is legal."""
        columns = self.__mapper__.columns
        for key, column in columns.items():
            value = getattr(self, key)
            if not self.type_compatible(value, column.type):
                raise exception.InvalidParameter(
                    'column %s value %r type is unexpected: %s' % (
                        key, value, column.type
                    )
                )

    def to_dict(self):
        """General function to convert record to dict.

        Convert all columns not starting with '_' to
        {<column_name>: <column_value>}
        """
        keys = self.__mapper__.columns.keys()
        dict_info = {}
        for key in keys:
            if key.startswith('_'):
                continue
            value = getattr(self, key)
            if value is not None:
                if isinstance(value, datetime.datetime):
                    value = util.format_datetime(value)
                dict_info[key] = value
        return dict_info


class StateMixin(TimestampMixin, HelperMixin):
    """Provides general fields and functions for state related table."""

    state = Column(
        Enum(
            'UNINITIALIZED', 'INITIALIZED', 'UPDATE_PREPARING',
            'INSTALLING', 'SUCCESSFUL', 'ERROR'
        ),
        ColumnDefault('UNINITIALIZED')
    )
    percentage = Column(Float, default=0.0)
    message = Column(Text, default='')
    severity = Column(
        Enum('INFO', 'WARNING', 'ERROR'),
        ColumnDefault('INFO')
    )
    ready = Column(Boolean, default=False)

    def update(self):
        # In state table, some field information is redundant.
        # The update function to make sure all related fields
        # are set to correct state.
        if self.ready:
            self.state = 'SUCCESSFUL'
        if self.state in ['UNINITIALIZED', 'INITIALIZED']:
            self.percentage = 0.0
            self.severity = 'INFO'
            self.message = ''
        if self.state == 'INSTALLING':
            if self.severity == 'ERROR':
                self.state = 'ERROR'
            elif self.percentage >= 1.0:
                self.state = 'SUCCESSFUL'
                self.percentage = 1.0
        if self.state == 'SUCCESSFUL':
            self.percentage = 1.0
        super(StateMixin, self).update()


class LogHistoryMixin(TimestampMixin, HelperMixin):
    """Provides general fields and functions for LogHistory related tables."""
    position = Column(Integer, default=0)
    partial_line = Column(Text, default='')
    percentage = Column(Float, default=0.0)
    message = Column(Text, default='')
    severity = Column(
        Enum('ERROR', 'WARNING', 'INFO'),
        ColumnDefault('INFO')
    )
    line_matcher_name = Column(
        String(80), default='start'
    )

    def validate(self):
        # TODO(xicheng): some validation can be moved to column.
        if not self.filename:
            raise exception.InvalidParameter(
                'filename is not set in %s' % self.id
            )


class HostNetwork(BASE, TimestampMixin, HelperMixin):
    """Host network table."""
    __tablename__ = 'host_network'

    id = Column(Integer, primary_key=True)
    host_id = Column(
        Integer,
        ForeignKey('host.id', onupdate='CASCADE', ondelete='CASCADE')
    )
    interface = Column(
        String(80), nullable=False)
    subnet_id = Column(
        Integer,
        ForeignKey('subnet.id', onupdate='CASCADE', ondelete='CASCADE')
    )
    user_id = Column(Integer, ForeignKey('user.id'))
    ip_int = Column(BigInteger, nullable=False)
    is_mgmt = Column(Boolean, default=False)
    is_promiscuous = Column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint('host_id', 'interface', name='interface_constraint'),
        UniqueConstraint('ip_int', 'user_id', name='ip_constraint')
    )

    def __init__(self, host_id, interface, user_id, **kwargs):
        self.host_id = host_id
        self.interface = interface
        self.user_id = user_id
        super(HostNetwork, self).__init__(**kwargs)

    def __str__(self):
        return 'HostNetwork[%s=%s]' % (self.interface, self.ip)

    @property
    def ip(self):
        return str(netaddr.IPAddress(self.ip_int))

    @ip.setter
    def ip(self, value):
        self.ip_int = int(netaddr.IPAddress(value))

    @property
    def netmask(self):
        return str(netaddr.IPNetwork(self.subnet.subnet).netmask)

    def update(self):
        self.host.config_validated = False

    def validate(self):
        # TODO(xicheng): some validation can be moved to column.
        super(HostNetwork, self).validate()
        if not self.subnet:
            raise exception.InvalidParameter(
                'subnet is not set in %s interface %s' % (
                    self.host_id, self.interface
                )
            )
        if not self.ip_int:
            raise exception.InvalidParameter(
                'ip is not set in %s interface %s' % (
                    self.host_id, self.interface
                )
            )
        ip = netaddr.IPAddress(self.ip_int)
        subnet = netaddr.IPNetwork(self.subnet.subnet)
        if ip not in subnet:
            raise exception.InvalidParameter(
                'ip %s is not in subnet %s' % (
                    str(ip), str(subnet)
                )
            )

    def to_dict(self):
        dict_info = super(HostNetwork, self).to_dict()
        dict_info['ip'] = self.ip
        dict_info['interface'] = self.interface
        dict_info['netmask'] = self.netmask
        dict_info['subnet'] = self.subnet.subnet
        dict_info['user_id'] = self.user_id
        return dict_info


class ClusterHostLogHistory(BASE, LogHistoryMixin):
    """clusterhost installing log history for each file.

    """
    __tablename__ = 'clusterhost_log_history'

    clusterhost_id = Column(
        'id', Integer,
        ForeignKey('clusterhost.id', onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True
    )
    filename = Column(String(80), primary_key=True, nullable=False)
    cluster_id = Column(
        Integer,
        ForeignKey('cluster.id')
    )
    host_id = Column(
        Integer,
        ForeignKey('host.id')
    )

    def __init__(self, clusterhost_id, filename, **kwargs):
        self.clusterhost_id = clusterhost_id
        self.filename = filename
        super(ClusterHostLogHistory, self).__init__(**kwargs)

    def __str__(self):
        return 'ClusterHostLogHistory[%s:%s]' % (
            self.clusterhost_id, self.filename
        )

    def initialize(self):
        self.cluster_id = self.clusterhost.cluster_id
        self.host_id = self.clusterhost.host_id
        super(ClusterHostLogHistory, self).initialize()


class HostLogHistory(BASE, LogHistoryMixin):
    """host installing log history for each file.

    """
    __tablename__ = 'host_log_history'

    id = Column(
        Integer,
        ForeignKey('host.id', onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True)
    filename = Column(String(80), primary_key=True, nullable=False)

    def __init__(self, id, filename, **kwargs):
        self.id = id
        self.filename = filename
        super(HostLogHistory, self).__init__(**kwargs)

    def __str__(self):
        return 'HostLogHistory[%s:%s]' % (self.id, self.filename)


class ClusterHostState(BASE, StateMixin):
    """ClusterHost state table."""
    __tablename__ = 'clusterhost_state'

    id = Column(
        Integer,
        ForeignKey(
            'clusterhost.id',
            onupdate='CASCADE', ondelete='CASCADE'
        ),
        primary_key=True
    )

    def __str__(self):
        return 'ClusterHostState[%s state %s percentage %s]' % (
            self.id, self.state, self.percentage
        )

    def update(self):
        """Update clusterhost state.

        When clusterhost state is updated, the underlying host state
        may be updated accordingly.
        """
        super(ClusterHostState, self).update()
        host_state = self.clusterhost.host.state
        if self.state == 'INITIALIZED':
            if host_state.state in ['UNINITIALIZED', 'UPDATE_PREPARING']:
                host_state.state = 'INITIALIZED'
                host_state.update()
        elif self.state == 'INSTALLING':
            if host_state.state in [
                'UNINITIALIZED', 'UPDATE_PREPARING', 'INITIALIZED'
            ]:
                host_state.state = 'INSTALLING'
                host_state.update()
        elif self.state == 'SUCCESSFUL':
            if host_state.state != 'SUCCESSFUL':
                host_state.state = 'SUCCESSFUL'
                host_state.update()


class ClusterHost(BASE, TimestampMixin, HelperMixin):
    """ClusterHost table."""
    __tablename__ = 'clusterhost'

    clusterhost_id = Column('id', Integer, primary_key=True)
    cluster_id = Column(
        Integer,
        ForeignKey('cluster.id', onupdate='CASCADE', ondelete='CASCADE')
    )
    host_id = Column(
        Integer,
        ForeignKey('host.id', onupdate='CASCADE', ondelete='CASCADE')
    )
    # the list of role names.
    _roles = Column('roles', JSONEncoded, default=[])
    _patched_roles = Column('patched_roles', JSONEncoded, default=[])
    config_step = Column(String(80), default='')
    package_config = Column(JSONEncoded, default={})
    config_validated = Column(Boolean, default=False)
    deployed_package_config = Column(JSONEncoded, default={})

    log_histories = relationship(
        ClusterHostLogHistory,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('clusterhost')
    )

    __table_args__ = (
        UniqueConstraint('cluster_id', 'host_id', name='constraint'),
    )

    state = relationship(
        ClusterHostState,
        uselist=False,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('clusterhost')
    )

    def __init__(self, cluster_id, host_id, **kwargs):
        self.cluster_id = cluster_id
        self.host_id = host_id
        self.state = ClusterHostState()
        super(ClusterHost, self).__init__(**kwargs)

    def __str__(self):
        return 'ClusterHost[%s:%s]' % (self.clusterhost_id, self.name)

    def update(self):
        if self.host.reinstall_os:
            if self.state in ['SUCCESSFUL', 'ERROR']:
                if self.config_validated:
                    self.state.state = 'INITIALIZED'
                else:
                    self.state.state = 'UNINITIALIZED'
        self.cluster.update()
        self.host.update()
        self.state.update()
        super(ClusterHost, self).update()

    @property
    def name(self):
        return '%s.%s' % (self.host.name, self.cluster.name)

    @property
    def patched_package_config(self):
        return self.package_config

    @patched_package_config.setter
    def patched_package_config(self, value):
        package_config = copy.deepcopy(self.package_config)
        self.package_config = util.merge_dict(package_config, value)
        logging.debug(
            'patch clusterhost %s package_config: %s',
            self.clusterhost_id, value
        )
        self.config_validated = False

    @property
    def put_package_config(self):
        return self.package_config

    @put_package_config.setter
    def put_package_config(self, value):
        package_config = copy.deepcopy(self.package_config)
        package_config.update(value)
        self.package_config = package_config
        logging.debug(
            'put clusterhost %s package_config: %s',
            self.clusterhost_id, value
        )
        self.config_validated = False

    @property
    def patched_os_config(self):
        return self.host.os_config

    @patched_os_config.setter
    def patched_os_config(self, value):
        host = self.host
        host.patched_os_config = value

    @property
    def put_os_config(self):
        return self.host.os_config

    @put_os_config.setter
    def put_os_config(self, value):
        host = self.host
        host.put_os_config = value

    @property
    def deployed_os_config(self):
        return self.host.deployed_os_config

    @deployed_os_config.setter
    def deployed_os_config(self, value):
        host = self.host
        host.deployed_os_config = value

    @hybrid_property
    def os_name(self):
        return self.host.os_name

    @os_name.expression
    def os_name(cls):
        return cls.host.os_name

    @hybrid_property
    def clustername(self):
        return self.cluster.name

    @clustername.expression
    def clustername(cls):
        return cls.cluster.name

    @hybrid_property
    def hostname(self):
        return self.host.hostname

    @hostname.expression
    def hostname(cls):
        return Host.hostname

    @property
    def distributed_system_installed(self):
        return self.state.state == 'SUCCESSFUL'

    @property
    def resintall_os(self):
        return self.host.reinstall_os

    @property
    def reinstall_distributed_system(self):
        return self.cluster.reinstall_distributed_system

    @property
    def os_installed(self):
        return self.host.os_installed

    @property
    def roles(self):
        # only the role exists in flavor roles will be returned.
        # the role will be sorted as the order defined in flavor
        # roles.
        # duplicate role names will be removed.
        # The returned value is a list of dict like
        # [{'name': 'allinone', 'optional': False}]
        role_names = list(self._roles)
        if not role_names:
            return []
        cluster_roles = self.cluster.flavor['roles']
        if not cluster_roles:
            return []
        roles = []
        for cluster_role in cluster_roles:
            if cluster_role['name'] in role_names:
                roles.append(cluster_role)
        return roles

    @roles.setter
    def roles(self, value):
        """value should be a list of role name."""
        self._roles = list(value)
        self.config_validated = False

    @property
    def patched_roles(self):
        patched_role_names = list(self._patched_roles)
        if not patched_role_names:
            return []
        cluster_roles = self.cluster.flavor['roles']
        if not cluster_roles:
            return []
        roles = []
        for cluster_role in cluster_roles:
            if cluster_role['name'] in patched_role_names:
                roles.append(cluster_role)
        return roles

    @patched_roles.setter
    def patched_roles(self, value):
        """value should be a list of role name."""
        # if value is an empty list, we empty the field
        if value:
            roles = list(self._roles)
            roles.extend(value)
            self._roles = roles
            patched_roles = list(self._patched_roles)
            patched_roles.extend(value)
            self._patched_roles = patched_roles
            self.config_validated = False
        else:
            self._patched_roles = list(value)
            self.config_validated = False

    @hybrid_property
    def owner(self):
        return self.cluster.owner

    @owner.expression
    def owner(cls):
        return cls.cluster.owner

    def state_dict(self):
        """Get clusterhost state dict.

        The clusterhost state_dict is different from
        clusterhost.state.to_dict. The main difference is state_dict
        show the progress of both installing os on host and installing
        distributed system on clusterhost. While clusterhost.state.to_dict
        only shows the progress of installing distributed system on
        clusterhost.
        """
        cluster = self.cluster
        host = self.host
        host_state = host.state_dict()
        if not cluster.flavor_name:
            return host_state
        clusterhost_state = self.state.to_dict()
        if clusterhost_state['state'] in ['ERROR', 'SUCCESSFUL']:
            return clusterhost_state
        if (
            clusterhost_state['state'] in 'INSTALLING' and
            clusterhost_state['percentage'] > 0
        ):
            clusterhost_state['percentage'] = min(
                1.0, (
                    0.5 + clusterhost_state['percentage'] / 2
                )
            )
            return clusterhost_state

        host_state['percentage'] = host_state['percentage'] / 2
        if host_state['state'] == 'SUCCESSFUL':
            host_state['state'] = 'INSTALLING'
        return host_state

    def to_dict(self):
        dict_info = self.host.to_dict()
        dict_info.update(super(ClusterHost, self).to_dict())
        state_dict = self.state_dict()
        dict_info.update({
            'distributed_system_installed': self.distributed_system_installed,
            'reinstall_distributed_system': self.reinstall_distributed_system,
            'owner': self.owner,
            'clustername': self.clustername,
            'name': self.name,
            'state': state_dict['state']
        })
        dict_info['roles'] = self.roles
        dict_info['patched_roles'] = self.patched_roles
        return dict_info


class HostState(BASE, StateMixin):
    """Host state table."""
    __tablename__ = 'host_state'

    id = Column(
        Integer,
        ForeignKey('host.id', onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True
    )

    def __str__(self):
        return 'HostState[%s state %s percentage %s]' % (
            self.id, self.state, self.percentage
        )

    def update(self):
        """Update host state.

        When host state is updated, all clusterhosts on the
        host will update their state if necessary.
        """
        super(HostState, self).update()
        host = self.host
        if self.state == 'INSTALLING':
            host.reinstall_os = False
            for clusterhost in self.host.clusterhosts:
                if clusterhost.state in [
                    'SUCCESSFUL', 'ERROR'
                ]:
                    clusterhost.state = 'INSTALLING'
                    clusterhost.state.update()
        elif self.state == 'UNINITIALIZED':
            for clusterhost in self.host.clusterhosts:
                if clusterhost.state in [
                    'INITIALIZED', 'INSTALLING', 'SUCCESSFUL', 'ERROR'
                ]:
                    clusterhost.state = 'UNINITIALIZED'
                    clusterhost.state.update()
        elif self.state == 'UPDATE_PREPARING':
            for clusterhost in self.host.clusterhosts:
                if clusterhost.state in [
                    'INITIALIZED', 'INSTALLING', 'SUCCESSFUL', 'ERROR'
                ]:
                    clusterhost.state = 'UPDATE_PREPARING'
                    clusterhost.state.update()
        elif self.state == 'INITIALIZED':
            for clusterhost in self.host.clusterhosts:
                if clusterhost.state in [
                    'INSTALLING', 'SUCCESSFUL', 'ERROR'
                ]:
                    clusterhost.state = 'INITIALIZED'
                    clusterhost.state.update()


class Host(BASE, TimestampMixin, HelperMixin):
    """Host table."""
    __tablename__ = 'host'

    name = Column(String(80), nullable=True)
    config_step = Column(String(80), default='')
    os_config = Column(JSONEncoded, default={})
    config_validated = Column(Boolean, default=False)
    deployed_os_config = Column(JSONEncoded, default={})
    os_name = Column(String(80))
    creator_id = Column(Integer, ForeignKey('user.id'))
    owner = Column(String(80))
    os_installer = Column(JSONEncoded, default={})

    __table_args__ = (
        UniqueConstraint('name', 'owner', name='constraint'),
    )

    id = Column(
        Integer,
        ForeignKey('machine.id', onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True
    )
    reinstall_os = Column(Boolean, default=True)

    host_networks = relationship(
        HostNetwork,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('host')
    )
    clusterhosts = relationship(
        ClusterHost,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('host')
    )
    state = relationship(
        HostState,
        uselist=False,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('host')
    )
    log_histories = relationship(
        HostLogHistory,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('host')
    )

    def __str__(self):
        return 'Host[%s:%s]' % (self.id, self.name)

    @hybrid_property
    def mac(self):
        machine = self.machine
        if machine:
            return machine.mac
        else:
            return None

    @property
    def os_id(self):
        return self.os_name

    @os_id.setter
    def os_id(self, value):
        self.os_name = value

    @hybrid_property
    def hostname(self):
        return self.name

    @hostname.expression
    def hostname(cls):
        return cls.name

    @property
    def patched_os_config(self):
        return self.os_config

    @patched_os_config.setter
    def patched_os_config(self, value):
        os_config = copy.deepcopy(self.os_config)
        self.os_config = util.merge_dict(os_config, value)
        logging.debug('patch host os config in %s: %s', self.id, value)
        self.config_validated = False

    @property
    def put_os_config(self):
        return self.os_config

    @put_os_config.setter
    def put_os_config(self, value):
        os_config = copy.deepcopy(self.os_config)
        os_config.update(value)
        self.os_config = os_config
        logging.debug('put host os config in %s: %s', self.id, value)
        self.config_validated = False

    def __init__(self, id, **kwargs):
        self.id = id
        self.state = HostState()
        super(Host, self).__init__(**kwargs)

    def update(self):
        creator = self.creator
        if creator:
            self.owner = creator.email
        if self.reinstall_os:
            if self.state in ['SUCCESSFUL', 'ERROR']:
                if self.config_validated:
                    self.state.state = 'INITIALIZED'
                else:
                    self.state.state = 'UNINITIALIZED'
                self.state.update()
        self.state.update()
        super(Host, self).update()

    def validate(self):
        # TODO(xicheng): some validation can be moved to the column in future.
        super(Host, self).validate()
        creator = self.creator
        if not creator:
            raise exception.InvalidParameter(
                'creator is not set in host %s' % self.id
            )
        os_name = self.os_name
        if not os_name:
            raise exception.InvalidParameter(
                'os is not set in host %s' % self.id
            )
        os_installer = self.os_installer
        if not os_installer:
            raise exception.Invalidparameter(
                'os_installer is not set in host %s' % self.id
            )

    @property
    def os_installed(self):
        return self.state.state == 'SUCCESSFUL'

    @property
    def clusters(self):
        return [clusterhost.cluster for clusterhost in self.clusterhosts]

    def state_dict(self):
        return self.state.to_dict()

    def to_dict(self):
        """Host dict contains its underlying machine dict."""
        dict_info = self.machine.to_dict()
        dict_info.update(super(Host, self).to_dict())
        state_dict = self.state_dict()
        ip = None
        for host_network in self.host_networks:
            if host_network.is_mgmt:
                ip = host_network.ip
        dict_info.update({
            'machine_id': self.machine.id,
            'os_installed': self.os_installed,
            'hostname': self.hostname,
            'ip': ip,
            'networks': [
                host_network.to_dict()
                for host_network in self.host_networks
            ],
            'os_id': self.os_id,
            'clusters': [cluster.to_dict() for cluster in self.clusters],
            'state': state_dict['state']
        })
        return dict_info


class ClusterState(BASE, StateMixin):
    """Cluster state table."""
    __tablename__ = 'cluster_state'

    id = Column(
        Integer,
        ForeignKey('cluster.id', onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True
    )
    total_hosts = Column(
        Integer,
        default=0
    )
    installing_hosts = Column(
        Integer,
        default=0
    )
    completed_hosts = Column(
        Integer,
        default=0
    )
    failed_hosts = Column(
        Integer,
        default=0
    )

    def __init__(self, **kwargs):
        super(ClusterState, self).__init__(**kwargs)

    def __str__(self):
        return 'ClusterState[%s state %s percentage %s]' % (
            self.id, self.state, self.percentage
        )

    def to_dict(self):
        dict_info = super(ClusterState, self).to_dict()
        dict_info['status'] = {
            'total_hosts': self.total_hosts,
            'installing_hosts': self.installing_hosts,
            'completed_hosts': self.completed_hosts,
            'failed_hosts': self.failed_hosts
        }
        return dict_info

    def update(self):
        # all fields of cluster state should be calculated by
        # its each underlying clusterhost state.
        cluster = self.cluster
        clusterhosts = cluster.clusterhosts
        self.total_hosts = len(clusterhosts)
        self.installing_hosts = 0
        self.failed_hosts = 0
        self.completed_hosts = 0
        if not cluster.flavor_name:
            for clusterhost in clusterhosts:
                host = clusterhost.host
                host_state = host.state.state
                if host_state == 'INSTALLING':
                    self.installing_hosts += 1
                elif host_state == 'ERROR':
                    self.failed_hosts += 1
                elif host_state == 'SUCCESSFUL':
                    self.completed_hosts += 1
        else:
            for clusterhost in clusterhosts:
                clusterhost_state = clusterhost.state.state
                if clusterhost_state == 'INSTALLING':
                    self.installing_hosts += 1
                elif clusterhost_state == 'ERROR':
                    self.failed_hosts += 1
                elif clusterhost_state == 'SUCCESSFUL':
                    self.completed_hosts += 1
        if self.total_hosts:
            if self.completed_hosts == self.total_hosts:
                self.percentage = 1.0
            else:
                self.percentage = (
                    float(self.completed_hosts)
                    /
                    float(self.total_hosts)
                )
                if self.state == 'SUCCESSFUL':
                    self.state = 'INSTALLING'
                self.ready = False
        self.message = (
            'total %s, installing %s, completed: %s, error %s'
        ) % (
            self.total_hosts, self.installing_hosts,
            self.completed_hosts, self.failed_hosts
        )
        if self.failed_hosts:
            self.severity = 'ERROR'

        super(ClusterState, self).update()
        if self.state == 'INSTALLING':
            cluster.reinstall_distributed_system = False


class Cluster(BASE, TimestampMixin, HelperMixin):
    """Cluster table."""
    __tablename__ = 'cluster'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    reinstall_distributed_system = Column(Boolean, default=True)
    config_step = Column(String(80), default='')
    os_name = Column(String(80))
    flavor_name = Column(String(80), nullable=True)
    # flavor dict got from flavor id.
    flavor = Column(JSONEncoded, default={})
    os_config = Column(JSONEncoded, default={})
    package_config = Column(JSONEncoded, default={})
    deployed_os_config = Column(JSONEncoded, default={})
    deployed_package_config = Column(JSONEncoded, default={})
    config_validated = Column(Boolean, default=False)
    adapter_name = Column(String(80))
    creator_id = Column(Integer, ForeignKey('user.id'))
    owner = Column(String(80))
    clusterhosts = relationship(
        ClusterHost,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('cluster')
    )
    state = relationship(
        ClusterState,
        uselist=False,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('cluster')
    )
    __table_args__ = (
        UniqueConstraint('name', 'creator_id', name='constraint'),
    )

    def __init__(self, name, creator_id, **kwargs):
        self.name = name
        self.creator_id = creator_id
        self.state = ClusterState()
        super(Cluster, self).__init__(**kwargs)

    def __str__(self):
        return 'Cluster[%s:%s]' % (self.id, self.name)

    def update(self):
        creator = self.creator
        if creator:
            self.owner = creator.email
        if self.reinstall_distributed_system:
            if self.state in ['SUCCESSFUL', 'ERROR']:
                if self.config_validated:
                    self.state.state = 'INITIALIZED'
                else:
                    self.state.state = 'UNINITIALIZED'
                self.state.update()
        self.state.update()
        super(Cluster, self).update()

    def validate(self):
        # TODO(xicheng): some validation can be moved to column.
        super(Cluster, self).validate()
        creator = self.creator
        if not creator:
            raise exception.InvalidParameter(
                'creator is not set in cluster %s' % self.id
            )
        os_name = self.os_name
        if not os_name:
            raise exception.InvalidParameter(
                'os is not set in cluster %s' % self.id
            )
        adapter_name = self.adapter_name
        if not adapter_name:
            raise exception.InvalidParameter(
                'adapter is not set in cluster %s' % self.id
            )
        flavor_name = self.flavor_name
        if flavor_name:
            if 'name' not in self.flavor:
                raise exception.InvalidParameter(
                    'key name does not exist in flavor %s' % (
                        self.flavor
                    )
                )
            if flavor_name != self.flavor['name']:
                raise exception.InvalidParameter(
                    'flavor name %s is not match '
                    'the name key in flavor %s' % (
                        flavor_name, self.flavor
                    )
                )
        else:
            if self.flavor:
                raise exception.InvalidParameter(
                    'flavor %s is not empty' % self.flavor
                )

    @property
    def os_id(self):
        return self.os_name

    @os_id.setter
    def os_id(self, value):
        self.os_name = value

    @property
    def adapter_id(self):
        return self.adapter_name

    @adapter_id.setter
    def adapter_id(self, value):
        self.adapter_name = value

    @property
    def flavor_id(self):
        if self.flavor_name:
            return '%s:%s' % (self.adapter_name, self.flavor_name)
        else:
            return None

    @flavor_id.setter
    def flavor_id(self, value):
        if value:
            _, flavor_name = value.split(':', 1)
            self.flavor_name = flavor_name
        else:
            self.flavor_name = value

    @property
    def patched_os_config(self):
        return self.os_config

    @patched_os_config.setter
    def patched_os_config(self, value):
        os_config = copy.deepcopy(self.os_config)
        self.os_config = util.merge_dict(os_config, value)
        logging.debug('patch cluster %s os config: %s', self.id, value)
        self.config_validated = False

    @property
    def put_os_config(self):
        return self.os_config

    @put_os_config.setter
    def put_os_config(self, value):
        os_config = copy.deepcopy(self.os_config)
        os_config.update(value)
        self.os_config = os_config
        logging.debug('put cluster %s os config: %s', self.id, value)
        self.config_validated = False

    @property
    def patched_package_config(self):
        return self.package_config

    @patched_package_config.setter
    def patched_package_config(self, value):
        package_config = copy.deepcopy(self.package_config)
        self.package_config = util.merge_dict(package_config, value)
        logging.debug('patch cluster %s package config: %s', self.id, value)
        self.config_validated = False

    @property
    def put_package_config(self):
        return self.package_config

    @put_package_config.setter
    def put_package_config(self, value):
        package_config = dict(self.package_config)
        package_config.update(value)
        self.package_config = package_config
        logging.debug('put cluster %s package config: %s', self.id, value)
        self.config_validated = False

    @property
    def distributed_system_installed(self):
        return self.state.state == 'SUCCESSFUL'

    def state_dict(self):
        return self.state.to_dict()

    def to_dict(self):
        dict_info = super(Cluster, self).to_dict()
        dict_info['distributed_system_installed'] = (
            self.distributed_system_installed
        )
        dict_info['os_id'] = self.os_id
        dict_info['adapter_id'] = self.adapter_id
        dict_info['flavor_id'] = self.flavor_id
        return dict_info


# User, Permission relation table
class UserPermission(BASE, HelperMixin, TimestampMixin):
    """User permission  table."""
    __tablename__ = 'user_permission'
    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey('user.id', onupdate='CASCADE', ondelete='CASCADE')
    )
    permission_id = Column(
        Integer,
        ForeignKey('permission.id', onupdate='CASCADE', ondelete='CASCADE')
    )
    __table_args__ = (
        UniqueConstraint('user_id', 'permission_id', name='constraint'),
    )

    def __init__(self, user_id, permission_id, **kwargs):
        self.user_id = user_id
        self.permission_id = permission_id

    def __str__(self):
        return 'UserPermission[%s:%s]' % (self.id, self.name)

    @hybrid_property
    def name(self):
        return self.permission.name

    def to_dict(self):
        dict_info = self.permission.to_dict()
        dict_info.update(super(UserPermission, self).to_dict())
        return dict_info


class Permission(BASE, HelperMixin, TimestampMixin):
    """Permission table."""
    __tablename__ = 'permission'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True, nullable=False)
    alias = Column(String(100))
    description = Column(Text)
    user_permissions = relationship(
        UserPermission,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('permission')
    )

    def __init__(self, name, **kwargs):
        self.name = name
        super(Permission, self).__init__(**kwargs)

    def __str__(self):
        return 'Permission[%s:%s]' % (self.id, self.name)


class UserToken(BASE, HelperMixin):
    """user token table."""
    __tablename__ = 'user_token'

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey('user.id', onupdate='CASCADE', ondelete='CASCADE')
    )
    token = Column(String(256), unique=True, nullable=False)
    expire_timestamp = Column(DateTime, nullable=True)

    def __init__(self, token, **kwargs):
        self.token = token
        super(UserToken, self).__init__(**kwargs)

    def validate(self):
        # TODO(xicheng): some validation can be moved to column.
        super(UserToken, self).validate()
        if not self.user:
            raise exception.InvalidParameter(
                'user is not set in token: %s' % self.token
            )


class UserLog(BASE, HelperMixin):
    """User log table."""
    __tablename__ = 'user_log'

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey('user.id', onupdate='CASCADE', ondelete='CASCADE')
    )
    action = Column(Text)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now())

    @hybrid_property
    def user_email(self):
        return self.user.email

    def validate(self):
        # TODO(xicheng): some validation can be moved to column.
        super(UserLog, self).validate()
        if not self.user:
            raise exception.InvalidParameter(
                'user is not set in user log: %s' % self.id
            )


class User(BASE, HelperMixin, TimestampMixin):
    """User table."""
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    email = Column(String(80), unique=True, nullable=False)
    crypted_password = Column('password', String(225))
    firstname = Column(String(80))
    lastname = Column(String(80))
    is_admin = Column(Boolean, default=False)
    active = Column(Boolean, default=True)
    user_permissions = relationship(
        UserPermission,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('user')
    )
    user_logs = relationship(
        UserLog,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('user')
    )
    user_tokens = relationship(
        UserToken,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('user')
    )
    clusters = relationship(
        Cluster,
        backref=backref('creator')
    )
    hosts = relationship(
        Host,
        backref=backref('creator')
    )

    def __init__(self, email, **kwargs):
        self.email = email
        super(User, self).__init__(**kwargs)

    def __str__(self):
        return 'User[%s]' % self.email

    def validate(self):
        # TODO(xicheng): some validation can be moved to column.
        super(User, self).validate()
        if not self.crypted_password:
            raise exception.InvalidParameter(
                'password is not set in user : %s' % self.email
            )

    @property
    def password(self):
        return '***********'

    @password.setter
    def password(self, password):
        # password stored in database is crypted.
        self.crypted_password = util.encrypt(password)

    @hybrid_property
    def permissions(self):
        permissions = []
        for user_permission in self.user_permissions:
            permissions.append(user_permission.permission)

        return permissions

    def to_dict(self):
        dict_info = super(User, self).to_dict()
        dict_info['permissions'] = [
            permission.to_dict()
            for permission in self.permissions
        ]
        return dict_info


class SwitchMachine(BASE, HelperMixin, TimestampMixin):
    """Switch Machine table."""
    __tablename__ = 'switch_machine'
    switch_machine_id = Column(
        'id', Integer, primary_key=True
    )
    switch_id = Column(
        Integer,
        ForeignKey('switch.id', onupdate='CASCADE', ondelete='CASCADE')
    )
    machine_id = Column(
        Integer,
        ForeignKey('machine.id', onupdate='CASCADE', ondelete='CASCADE')
    )
    owner_id = Column(Integer, ForeignKey('user.id'))
    port = Column(String(80), nullable=True)
    vlans = Column(JSONEncoded, default=[])
    __table_args__ = (
        UniqueConstraint('switch_id', 'machine_id', name='constraint'),
    )

    def __init__(self, switch_id, machine_id, **kwargs):
        self.switch_id = switch_id
        self.machine_id = machine_id
        super(SwitchMachine, self).__init__(**kwargs)

    def __str__(self):
        return 'SwitchMachine[%s port %s]' % (
            self.switch_machine_id, self.port
        )

    def validate(self):
        # TODO(xicheng): some validation can be moved to column.
        super(SwitchMachine, self).validate()
        if not self.switch:
            raise exception.InvalidParameter(
                'switch is not set in %s' % self.id
            )
        if not self.machine:
            raise exception.Invalidparameter(
                'machine is not set in %s' % self.id
            )
        if not self.port:
            raise exception.InvalidParameter(
                'port is not set in %s' % self.id
            )

    @hybrid_property
    def mac(self):
        return self.machine.mac

    @hybrid_property
    def tag(self):
        return self.machine.tag

    @property
    def switch_ip(self):
        return self.switch.ip

    @hybrid_property
    def switch_ip_int(self):
        return self.switch.ip_int

    @switch_ip_int.expression
    def switch_ip_int(cls):
        return Switch.ip_int

    @hybrid_property
    def switch_vendor(self):
        return self.switch.vendor

    @switch_vendor.expression
    def switch_vendor(cls):
        return Switch.vendor

    @property
    def patched_vlans(self):
        return self.vlans

    @patched_vlans.setter
    def patched_vlans(self, value):
        if not value:
            return
        vlans = list(self.vlans)
        for item in value:
            if item not in vlans:
                vlans.append(item)
        self.vlans = vlans

    @property
    def filtered(self):
        """Check if switch machine should be filtered.

        port should be composed with <port_prefix><port_number><port_suffix>
        For each filter in switch machine filters,
        if filter_type is allow and port match the pattern, the switch
        machine is allowed to be got by api. If filter_type is deny and
        port match the pattern, the switch machine is not allowed to be got
        by api.
        If not filter is matched, if the last filter is allow, deny all
        unmatched switch machines, if the last filter is deny, allow all
        unmatched switch machines.
        If no filter defined, allow all switch machines.
        if ports defined in filter and 'all' in ports, the switch machine is
        matched.  if ports defined in filter and 'all' not in ports,
        the switch machine with the port name in ports will be matched.
        If the port pattern matches
        <<port_prefix><port_number><port_suffix> and port number is in the
        range of [port_start, port_end], the switch machine is matched.
        """
        filters = self.switch.machine_filters
        port = self.port
        unmatched_allowed = True
        ports_pattern = re.compile(r'(\D*)(\d+)-(\d+)(\D*)')
        port_pattern = re.compile(r'(\D*)(\d+)(\D*)')
        port_match = port_pattern.match(port)
        if port_match:
            port_prefix = port_match.group(1)
            port_number = int(port_match.group(2))
            port_suffix = port_match.group(3)
        else:
            port_prefix = ''
            port_number = 0
            port_suffix = ''
        for port_filter in filters:
            filter_type = port_filter.get('filter_type', 'allow')
            denied = filter_type != 'allow'
            unmatched_allowed = denied
            if 'ports' in port_filter:
                if 'all' in port_filter['ports']:
                    return denied
                if port in port_filter['ports']:
                    return denied
                if port_match:
                    for port_or_ports in port_filter['ports']:
                        ports_match = ports_pattern.match(port_or_ports)
                        if ports_match:
                            filter_port_prefix = ports_match.group(1)
                            filter_port_start = int(ports_match.group(2))
                            filter_port_end = int(ports_match.group(3))
                            filter_port_suffix = ports_match.group(4)
                            if (
                                filter_port_prefix == port_prefix and
                                filter_port_suffix == port_suffix and
                                filter_port_start <= port_number and
                                port_number <= filter_port_end
                            ):
                                return denied
            else:
                filter_port_prefix = port_filter.get('port_prefix', '')
                filter_port_suffix = port_filter.get('port_suffix', '')
                if (
                    port_match and
                    port_prefix == filter_port_prefix and
                    port_suffix == filter_port_suffix
                ):
                    if (
                        'port_start' not in port_filter or
                        port_number >= port_filter['port_start']
                    ) and (
                        'port_end' not in port_filter or
                        port_number <= port_filter['port_end']
                    ):
                        return denied
        return not unmatched_allowed

    def to_dict(self):
        dict_info = self.machine.to_dict()
        dict_info.update(super(SwitchMachine, self).to_dict())
        dict_info['switch_ip'] = self.switch.ip
        return dict_info


class Machine(BASE, HelperMixin, TimestampMixin):
    """Machine table."""
    __tablename__ = 'machine'
    id = Column(Integer, primary_key=True)
    mac = Column(String(24), unique=True, nullable=False)
    ipmi_credentials = Column(JSONEncoded, default={})
    tag = Column(JSONEncoded, default={})
    location = Column(JSONEncoded, default={})
    owner_id = Column(Integer, ForeignKey('user.id'))
    machine_attributes = Column(JSONEncoded, default={})

    switch_machines = relationship(
        SwitchMachine,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('machine')
    )
    host = relationship(
        Host,
        uselist=False,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('machine')
    )

    def __init__(self, mac, **kwargs):
        self.mac = mac
        super(Machine, self).__init__(**kwargs)

    def __str__(self):
        return 'Machine[%s:%s]' % (self.id, self.mac)

    def validate(self):
        # TODO(xicheng): some validation can be moved to column.
        super(Machine, self).validate()
        try:
            netaddr.EUI(self.mac)
        except Exception:
            raise exception.InvalidParameter(
                'mac address %s format uncorrect' % self.mac
            )

    @property
    def patched_ipmi_credentials(self):
        return self.ipmi_credentials

    @patched_ipmi_credentials.setter
    def patched_ipmi_credentials(self, value):
        if not value:
            return
        ipmi_credentials = copy.deepcopy(self.ipmi_credentials)
        self.ipmi_credentials = util.merge_dict(ipmi_credentials, value)

    @property
    def patched_tag(self):
        return self.tag

    @patched_tag.setter
    def patched_tag(self, value):
        if not value:
            return
        tag = copy.deepcopy(self.tag)
        tag.update(value)
        self.tag = value

    @property
    def patched_location(self):
        return self.location

    @patched_location.setter
    def patched_location(self, value):
        if not value:
            return
        location = copy.deepcopy(self.location)
        location.update(value)
        self.location = location

    def to_dict(self):
        # TODO(xicheng): move the filling of switches
        # to db/api.
        dict_info = {}
        dict_info['switches'] = [
            {
                'switch_ip': switch_machine.switch_ip,
                'port': switch_machine.port,
                'vlans': switch_machine.vlans
            }
            for switch_machine in self.switch_machines
            if not switch_machine.filtered
        ]
        if dict_info['switches']:
            dict_info.update(dict_info['switches'][0])
        dict_info.update(super(Machine, self).to_dict())
        return dict_info


class Switch(BASE, HelperMixin, TimestampMixin):
    """Switch table."""
    __tablename__ = 'switch'
    id = Column(Integer, primary_key=True)
    ip_int = Column('ip', BigInteger, unique=True, nullable=False)
    credentials = Column(JSONEncoded, default={})
    vendor = Column(String(256), nullable=True)
    state = Column(Enum('initialized', 'unreachable', 'notsupported',
                        'repolling', 'error', 'under_monitoring',
                        name='switch_state'),
                   ColumnDefault('initialized'))
    # filters is json formatted list, each element has following format:
    # keys: ['filter_type', 'ports', 'port_prefix', 'port_suffix',
    # 'port_start', 'port_end'].
    # each port name is divided into <port_prefix><port_number><port_suffix>
    # filter_type is one of ['allow', 'deny'], default is 'allow'
    # ports is a list of port name.
    # port_prefix is the prefix that filtered port should start with.
    # port_suffix is the suffix that filtered posrt should end with.
    # port_start is integer that the port number should start with.
    # port_end is the integer that the port number should end with.
    _filters = Column('filters', JSONEncoded, default=[])
    switch_machines = relationship(
        SwitchMachine,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('switch')
    )

    def __str__(self):
        return 'Switch[%s:%s]' % (self.id, self.ip)

    @classmethod
    def parse_filters(cls, filters):
        """parse filters set from outside to standard format.

        api can set switch filters with the flexible format, this
        function will parse the flexible format filters.

        Supported format:
           as string:
              allow ports ae10,ae20
              allow port_prefix ae port_start 30 port_end 40
              deny ports all
           as python object:
              [{
                  'filter_type': 'allow',
                  'ports': ['ae10', 'ae20']
              },{
                  'filter_type': 'allow',
                  'port_prefix': 'ae',
                  'port_suffix': '',
                  'port_start': 30,
                  'port_end': 40
              },{
                  'filter_type': 'deny',
                  'ports': ['all']
              }]
        """
        if isinstance(filters, basestring):
            filters = filters.replace('\r\n', '\n').replace('\n', ';')
            filters = [
                machine_filter for machine_filter in filters.split(';')
                if machine_filter
            ]
        if not isinstance(filters, list):
            filters = [filters]
        machine_filters = []
        for machine_filter in filters:
            if not machine_filter:
                continue
            if isinstance(machine_filter, basestring):
                filter_dict = {}
                filter_items = [
                    item for item in machine_filter.split() if item
                ]
                if filter_items[0] in ['allow', 'deny']:
                    filter_dict['filter_type'] = filter_items[0]
                    filter_items = filter_items[1:]
                elif filter_items[0] not in [
                    'ports', 'port_prefix', 'port_suffix',
                    'port_start', 'port_end'
                ]:
                    raise exception.InvalidParameter(
                        'unrecognized filter type %s' % filter_items[0]
                    )
                while filter_items:
                    if len(filter_items) >= 2:
                        filter_dict[filter_items[0]] = filter_items[1]
                        filter_items = filter_items[2:]
                    else:
                        filter_dict[filter_items[0]] = ''
                        filter_items = filter_items[1:]
                machine_filter = filter_dict
            if not isinstance(machine_filter, dict):
                raise exception.InvalidParameter(
                    'filter %s is not dict' % machine_filter
                )
            if 'filter_type' in machine_filter:
                if machine_filter['filter_type'] not in ['allow', 'deny']:
                    raise exception.InvalidParameter(
                        'filter_type should be `allow` or `deny` in %s' % (
                            machine_filter
                        )
                    )
            if 'ports' in machine_filter:
                if isinstance(machine_filter['ports'], basestring):
                    machine_filter['ports'] = [
                        port_or_ports
                        for port_or_ports in machine_filter['ports'].split(',')
                        if port_or_ports
                    ]
                if not isinstance(machine_filter['ports'], list):
                    raise exception.InvalidParameter(
                        '`ports` type is not list in filter %s' % (
                            machine_filter
                        )
                    )
                for port_or_ports in machine_filter['ports']:
                    if not isinstance(port_or_ports, basestring):
                        raise exception.InvalidParameter(
                            '%s type is not basestring in `ports` %s' % (
                                port_or_ports, machine_filter['ports']
                            )
                        )
            for key in ['port_start', 'port_end']:
                if key in machine_filter:
                    if isinstance(machine_filter[key], basestring):
                        if machine_filter[key].isdigit():
                            machine_filter[key] = int(machine_filter[key])
                    if not isinstance(machine_filter[key], (int, long)):
                        raise exception.InvalidParameter(
                            '`%s` type is not int in filer %s' % (
                                key, machine_filter
                            )
                        )
            machine_filters.append(machine_filter)
        return machine_filters

    @classmethod
    def format_filters(cls, filters):
        """format json formatted filters to string."""
        filter_strs = []
        for machine_filter in filters:
            filter_properties = []
            filter_properties.append(
                machine_filter.get('filter_type', 'allow')
            )
            if 'ports' in machine_filter:
                filter_properties.append(
                    'ports ' + ','.join(machine_filter['ports'])
                )
            if 'port_prefix' in machine_filter:
                filter_properties.append(
                    'port_prefix ' + machine_filter['port_prefix']
                )
            if 'port_suffix' in machine_filter:
                filter_properties.append(
                    'port_suffix ' + machine_filter['port_suffix']
                )
            if 'port_start' in machine_filter:
                filter_properties.append(
                    'port_start ' + str(machine_filter['port_start'])
                )
            if 'port_end' in machine_filter:
                filter_properties.append(
                    'port_end ' + str(machine_filter['port_end'])
                )
            filter_strs.append(' '.join(filter_properties))
        return ';'.join(filter_strs)

    def __init__(self, ip_int, **kwargs):
        self.ip_int = ip_int
        super(Switch, self).__init__(**kwargs)

    @property
    def ip(self):
        return str(netaddr.IPAddress(self.ip_int))

    @ip.setter
    def ip(self, ipaddr):
        self.ip_int = int(netaddr.IPAddress(ipaddr))

    @property
    def patched_credentials(self):
        return self.credentials

    @patched_credentials.setter
    def patched_credentials(self, value):
        if not value:
            return
        credentials = copy.deepcopy(self.credentials)
        self.credentials = util.merge_dict(credentials, value)

    @property
    def machine_filters(self):
        return self._filters

    @machine_filters.setter
    def machine_filters(self, value):
        if not value:
            return
        self._filters = self.parse_filters(value)

    @property
    def put_machine_filters(self):
        return self._filters

    @put_machine_filters.setter
    def put_machine_filters(self, value):
        if not value:
            return
        self._filters = self.parse_filters(value)

    @property
    def patched_machine_filters(self):
        return self._filters

    @patched_machine_filters.setter
    def patched_machine_filters(self, value):
        if not value:
            return
        filters = list(self.machine_filters)
        self._filters = self.parse_filters(value) + filters

    def to_dict(self):
        dict_info = super(Switch, self).to_dict()
        dict_info['ip'] = self.ip
        dict_info['filters'] = self.format_filters(self._filters)
        return dict_info


class Subnet(BASE, TimestampMixin, HelperMixin):
    """network table."""
    __tablename__ = 'subnet'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True, nullable=True)
    subnet = Column(String(80), unique=True, nullable=False)

    host_networks = relationship(
        HostNetwork,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('subnet')
    )

    def __init__(self, subnet, **kwargs):
        self.subnet = subnet
        super(Subnet, self).__init__(**kwargs)

    def __str__(self):
        return 'Subnet[%s:%s]' % (self.id, self.subnet)

    def to_dict(self):
        dict_info = super(Subnet, self).to_dict()
        if not self.name:
            dict_info['name'] = self.subnet
        return dict_info


# TODO(grace): move this global variable into HealthCheckReport.
HEALTH_REPORT_STATES = ('verifying', 'success', 'finished', 'error')


class HealthCheckReport(BASE, HelperMixin):
    """Health check report table."""
    __tablename__ = 'health_check_report'

    cluster_id = Column(
        Integer,
        ForeignKey('cluster.id', onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True
    )
    name = Column(String(80), nullable=False, primary_key=True)
    display_name = Column(String(100))
    report = Column(JSONEncoded, default={})
    category = Column(String(80), default='')
    state = Column(
        Enum(*HEALTH_REPORT_STATES, name='report_state'),
        ColumnDefault('verifying'),
        nullable=False
    )
    error_message = Column(Text, default='')

    def __init__(self, cluster_id, name, **kwargs):
        self.cluster_id = cluster_id
        self.name = name
        if 'state' in kwargs and kwargs['state'] not in HEALTH_REPORT_STATES:
            err_msg = 'State value %s is not accepted.' % kwargs['state']
            raise exception.InvalidParameter(err_msg)

        super(HealthCheckReport, self).__init__(**kwargs)

    def __str__(self):
        return 'HealthCheckReport[cluster_id: %s, name: %s]' % (
            self.cluster_id, self.name
        )
