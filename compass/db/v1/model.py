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

"""database model."""
from datetime import datetime
from hashlib import md5
import logging
import simplejson as json
import uuid

from sqlalchemy import Column, ColumnDefault, Integer, String
from sqlalchemy import Float, Enum, DateTime, ForeignKey, Text, Boolean
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property

from compass.utils import util

from flask.ext.login import UserMixin
from itsdangerous import URLSafeTimedSerializer

BASE = declarative_base()
# TODO(grace) SECRET_KEY should be generated when installing compass
# and save to a config file or DB
SECRET_KEY = "abcd"

# This is used for generating a token by user's ID and
# decode the ID from this token
login_serializer = URLSafeTimedSerializer(SECRET_KEY)


class User(BASE, UserMixin):
    """User table."""
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    email = Column(String(80), unique=True)
    password = Column(String(225), default='')
    active = Column(Boolean, default=True)

    def __init__(self, email, password, **kwargs):
        self.email = email
        self.password = self._set_password(password)

    def __repr__(self):
        return '<User name: %s>' % self.email

    def _set_password(self, password):
        return self._hash_password(password)

    def get_password(self):
        return self.password

    def valid_password(self, password):
        return self.password == self._hash_password(password)

    def get_auth_token(self):
        return login_serializer.dumps(self.id)

    def is_active(self):
        return self.active

    def _hash_password(self, password):
        return md5(password).hexdigest()


class SwitchConfig(BASE):
    """Swtich Config table.

    :param id: The unique identifier of the switch config.
    :param ip: The IP address of the switch.
    :param filter_port: The port of the switch which need to be filtered.
    """
    __tablename__ = 'switch_config'
    id = Column(Integer, primary_key=True)
    ip = Column(String(80))
    filter_port = Column(String(16))
    __table_args__ = (UniqueConstraint('ip', 'filter_port', name='filter1'), )

    def __init__(self, **kwargs):
        super(SwitchConfig, self).__init__(**kwargs)


class Switch(BASE):
    """Switch table.

    :param id: the unique identifier of the switch. int as primary key.
    :param ip: the IP address of the switch.
    :param vendor_info: the name of the vendor
    :param credential_data: used for accessing and retrieving information
                            from the switch. Store json format as string.
    :param state: Enum.'initialized/repolling': polling switch not complete to
                  learn all MAC addresses of devices connected to the switch;
                  'unreachable': one of the final state, indicates that the
                  switch is unreachable at this time, no MAC address could be
                  retrieved from the switch.
                  'notsupported': one of the final state, indicates that the
                  vendor found is not supported yet, no MAC address will be
                  retrieved from the switch.
                  'error': one of the final state, indicates that something
                           wrong happend.
                  'under_monitoring': one of the final state, indicates that
                  MAC addresses has been learned successfully from the switch.
    :param err_msg: Error message when polling switch failed.
    :param machines: refer to list of Machine connected to the switch.
    """
    __tablename__ = 'switch'

    id = Column(Integer, primary_key=True)
    ip = Column(String(80), unique=True)
    credential_data = Column(Text)
    vendor_info = Column(String(256), nullable=True)
    state = Column(Enum('initialized', 'unreachable', 'notsupported',
                        'repolling', 'error', 'under_monitoring',
                        name='switch_state'),
                   default='initialized')
    err_msg = Column(Text)

    def __init__(self, **kwargs):
        super(Switch, self).__init__(**kwargs)

    def __repr__(self):
        return '<Switch ip: %r, credential: %r, vendor: %r, state: %s>'\
            % (self.ip, self.credential, self.vendor, self.state)

    @hybrid_property
    def vendor(self):
        """vendor property getter"""
        return self.vendor_info

    @vendor.setter
    def vendor(self, value):
        """vendor property setter"""
        self.vendor_info = value

    @property
    def credential(self):
        """credential data getter.

        :returns: python primitive dictionary object.
        """
        if self.credential_data:
            try:
                credential = json.loads(self.credential_data)
                return credential
            except Exception as error:
                logging.error('failed to load credential data %s: %s',
                              self.id, self.credential_data)
                logging.exception(error)
                raise error
        else:
            return {}

    @credential.setter
    def credential(self, value):
        """credential property setter

        :param value: dict of configuration data needed to update.
        """
        if value:
            try:
                credential = {}
                if self.credential_data:
                    credential = json.loads(self.credential_data)

                credential.update(value)
                self.credential_data = json.dumps(credential)

            except Exception as error:
                logging.error('failed to dump credential data %s: %s',
                              self.id, value)
                logging.exception(error)
                raise error

        else:
            self.credential_data = json.dumps({})

        logging.debug('switch now is %s', self)


class Machine(BASE):
    """Machine table.

       .. note::
          currently, we are taking care of management plane.
          Therefore, we assume one machine is connected to one switch.

    :param id: int, identity as primary key
    :param mac: string, the MAC address of the machine.
    :param switch_id: switch id that this machine connected on to.
    :param port: nth port of the switch that this machine connected.
    :param vlan: vlan id that this machine connected on to.
    :param update_timestamp: last time this entry got updated.
    :param switch: refer to the Switch the machine connects to.
    """
    __tablename__ = 'machine'

    id = Column(Integer, primary_key=True)
    mac = Column(String(24), default='')
    port = Column(String(16), default='')
    vlan = Column(Integer, default=0)
    update_timestamp = Column(DateTime, default=datetime.now,
                              onupdate=datetime.now)
    switch_id = Column(Integer, ForeignKey('switch.id',
                                           onupdate='CASCADE',
                                           ondelete='SET NULL'))
    __table_args__ = (UniqueConstraint('mac', 'switch_id',
                                       name='unique_machine'),)
    switch = relationship('Switch', backref=backref('machines',
                                                    lazy='dynamic'))

    def __init__(self, **kwargs):
        super(Machine, self).__init__(**kwargs)

    def __repr__(self):
        return '<Machine %r: port=%r vlan=%r switch=%r>' % (
            self.mac, self.port, self.vlan, self.switch)


class HostState(BASE):
    """The state of the ClusterHost.

    :param id: int, identity as primary key.
    :param state: Enum. 'UNINITIALIZED': the host is ready to setup.
                 'INSTALLING': the host is not installing.
                 'READY': the host is setup.
                 'ERROR': the host has error.
    :param progress: float, the installing progress from 0 to 1.
    :param message: the latest installing message.
    :param severity: Enum, the installing message severity.
                     ('INFO', 'WARNING', 'ERROR')
    :param update_timestamp: the lastest timestamp the entry got updated.
    :param host: refer to ClusterHost.
    :param os_progress: float, the installing progress of OS from 0 to 1.
    """
    __tablename__ = "host_state"

    id = Column(Integer, ForeignKey('cluster_host.id',
                                    onupdate='CASCADE',
                                    ondelete='CASCADE'),
                primary_key=True)
    state = Column(Enum('UNINITIALIZED', 'INSTALLING', 'READY', 'ERROR'),
                   ColumnDefault('UNINITIALIZED'))
    progress = Column(Float, ColumnDefault(0.0))
    message = Column(Text)
    severity = Column(Enum('INFO', 'WARNING', 'ERROR'), ColumnDefault('INFO'))
    update_timestamp = Column(DateTime, default=datetime.now,
                              onupdate=datetime.now)
    host = relationship('ClusterHost', backref=backref('state',
                                                       uselist=False))

    os_progress = Column(Float, ColumnDefault(0.0))
    os_message = Column(Text)
    os_severity = Column(
        Enum('INFO', 'WARNING', 'ERROR'),
        ColumnDefault('INFO')
    )
    """
    this is added by Lei for separating os and package progress purposes
    os_state = Column(Enum('UNINITIALIZED', 'INSTALLING', 'OS_READY', 'ERROR'),
                   ColumnDefault('UNINITIALIZED'))
    """

    def __init__(self, **kwargs):
        super(HostState, self).__init__(**kwargs)

    @hybrid_property
    def hostname(self):
        """hostname getter"""
        return self.host.hostname

    @hybrid_property
    def fullname(self):
        """fullname getter"""
        return self.host.fullname

    def __repr__(self):
        return (
            '<HostState %r: state=%r, progress=%s, '
            'message=%s, severity=%s, os_progress=%s>'
        ) % (
            self.hostname, self.state, self.progress,
            self.message, self.severity, self.os_progress
        )


class ClusterState(BASE):
    """The state of the Cluster.

    :param id: int, identity as primary key.
    :param state: Enum, 'UNINITIALIZED': the cluster is ready to setup.
                 'INSTALLING': the cluster is not installing.
                 'READY': the cluster is setup.
                 'ERROR': the cluster has error.
    :param progress: float, the installing progress from 0 to 1.
    :param message: the latest installing message.
    :param severity: Enum, the installing message severity.
                     ('INFO', 'WARNING', 'ERROR').
    :param update_timestamp: the lastest timestamp the entry got updated.
    :param cluster: refer to Cluster.
    """
    __tablename__ = 'cluster_state'
    id = Column(Integer, ForeignKey('cluster.id',
                                    onupdate='CASCADE',
                                    ondelete='CASCADE'),
                primary_key=True)
    state = Column(Enum('UNINITIALIZED', 'INSTALLING', 'READY', 'ERROR'),
                   ColumnDefault('UNINITIALIZED'))
    progress = Column(Float, ColumnDefault(0.0))
    message = Column(Text)
    severity = Column(Enum('INFO', 'WARNING', 'ERROR'), ColumnDefault('INFO'))
    update_timestamp = Column(DateTime, default=datetime.now,
                              onupdate=datetime.now)
    cluster = relationship('Cluster', backref=backref('state',
                                                      uselist=False))

    def __init__(self, **kwargs):
        super(ClusterState, self).__init__(**kwargs)

    @hybrid_property
    def clustername(self):
        """clustername getter"""
        return self.cluster.name

    def __repr__(self):
        return (
            '<ClusterState %r: state=%r, progress=%s, '
            'message=%s, severity=%s>'
        ) % (
            self.clustername, self.state, self.progress,
            self.message, self.severity
        )


class Cluster(BASE):
    """Cluster configuration information.

    :param id: int, identity as primary key.
    :param name: str, cluster name.
    :param mutable: bool, if the Cluster is mutable.
    :param security_config: str stores json formatted security information.
    :param networking_config: str stores json formatted networking information.
    :param partition_config: string stores json formatted parition information.
    :param adapter_id: the refer id in the Adapter table.
    :param raw_config: str stores json formatted other cluster information.
    :param adapter: refer to the Adapter.
    :param state: refer to the ClusterState.
    """
    __tablename__ = 'cluster'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True)
    mutable = Column(Boolean, default=True)
    security_config = Column(Text)
    networking_config = Column(Text)
    partition_config = Column(Text)
    adapter_id = Column(Integer, ForeignKey('adapter.id',
                                            onupdate='CASCADE',
                                            ondelete='SET NULL'),
                        nullable=True)
    raw_config = Column(Text)
    adapter = relationship("Adapter", backref=backref('clusters',
                                                      lazy='dynamic'))

    def __init__(self, **kwargs):
        if 'name' not in kwargs or not kwargs['name']:
            kwargs['name'] = str(uuid.uuid4())

        super(Cluster, self).__init__(**kwargs)

    def __repr__(self):
        return '<Cluster %r: config=%r>' % (self.name, self.config)

    @property
    def partition(self):
        """partition getter"""
        if self.partition_config:
            try:
                return json.loads(self.partition_config)
            except Exception as error:
                logging.error('failed to load security config %s: %s',
                              self.id, self.partition_config)
                logging.exception(error)
                raise error
        else:
            return {}

    @partition.setter
    def partition(self, value):
        """partition setter"""
        logging.debug('cluster %s set partition %s', self.id, value)
        if value:
            try:
                self.partition_config = json.dumps(value)
            except Exception as error:
                logging.error('failed to dump partition config %s: %s',
                              self.id, value)
                logging.exception(error)
                raise error
        else:
            self.partition_config = None

    @property
    def security(self):
        """security getter"""
        if self.security_config:
            try:
                return json.loads(self.security_config)
            except Exception as error:
                logging.error('failed to load security config %s: %s',
                              self.id, self.security_config)
                logging.exception(error)
                raise error
        else:
            return {}

    @security.setter
    def security(self, value):
        """security setter"""
        logging.debug('cluster %s set security %s', self.id, value)
        if value:
            try:
                self.security_config = json.dumps(value)
            except Exception as error:
                logging.error('failed to dump security config %s: %s',
                              self.id, value)
                logging.exception(error)
                raise error
        else:
            self.security_config = None

    @property
    def networking(self):
        """networking getter"""
        if self.networking_config:
            try:
                return json.loads(self.networking_config)
            except Exception as error:
                logging.error('failed to load networking config %s: %s',
                              self.id, self.networking_config)
                logging.exception(error)
                raise error
        else:
            return {}

    @networking.setter
    def networking(self, value):
        """networking setter."""
        logging.debug('cluster %s set networking %s', self.id, value)
        if value:
            try:
                self.networking_config = json.dumps(value)
            except Exception as error:
                logging.error('failed to dump networking config %s: %s',
                              self.id, value)
                logging.exception(error)
                raise error
        else:
            self.networking_config = None

    @hybrid_property
    def config(self):
        """get config from security, networking, partition."""
        config = {}
        if self.raw_config:
            try:
                config = json.loads(self.raw_config)
            except Exception as error:
                logging.error('failed to load raw config %s: %s',
                              self.id, self.raw_config)
                logging.exception(error)
                raise error

        util.merge_dict(config, {'security': self.security})
        util.merge_dict(config, {'networking': self.networking})
        util.merge_dict(config, {'partition': self.partition})
        util.merge_dict(config, {'clusterid': self.id,
                                 'clustername': self.name})
        return config

    @config.setter
    def config(self, value):
        """set config to security, networking, partition."""
        logging.debug('cluster %s set config %s', self.id, value)
        if not value:
            self.security = None
            self.networking = None
            self.partition = None
            self.raw_config = None
            return

        self.security = value.get('security')
        self.networking = value.get('networking')
        self.partition = value.get('partition')

        try:
            self.raw_config = json.dumps(value)
        except Exception as error:
            logging.error('failed to dump raw config %s: %s',
                          self.id, value)
            logging.exception(error)
            raise error


class ClusterHost(BASE):
    """ClusterHost information.

    :param id: int, identity as primary key.
    :param machine_id: int, the id of the Machine.
    :param cluster_id: int, the id of the Cluster.
    :param mutable: if the ClusterHost information is mutable.
    :param hostname: str, host name.
    :param config_data: string, json formatted config data.
    :param cluster: refer to Cluster the host in.
    :param machine: refer to the Machine the host on.
    :param state: refer to HostState indicates the host state.
    """
    __tablename__ = 'cluster_host'

    id = Column(Integer, primary_key=True)

    machine_id = Column(Integer, ForeignKey('machine.id',
                                            onupdate='CASCADE',
                                            ondelete='CASCADE'),
                        nullable=True, unique=True)

    cluster_id = Column(Integer, ForeignKey('cluster.id',
                                            onupdate='CASCADE',
                                            ondelete='SET NULL'),
                        nullable=True)

    hostname = Column(String(80))
    config_data = Column(Text)
    mutable = Column(Boolean, default=True)
    __table_args__ = (UniqueConstraint('cluster_id', 'hostname',
                                       name='unique_host'),)

    cluster = relationship("Cluster",
                           backref=backref('hosts', lazy='dynamic'))
    machine = relationship("Machine",
                           backref=backref('host', uselist=False))

    def __init__(self, **kwargs):
        if 'hostname' not in kwargs or not kwargs['hostname']:
            kwargs['hostname'] = str(uuid.uuid4())

        super(ClusterHost, self).__init__(**kwargs)

    def __repr__(self):
        return '<ClusterHost %r: cluster=%r machine=%r>' % (
            self.hostname, self.cluster, self.machine)

    @hybrid_property
    def fullname(self):
        return '%s.%s' % (self.hostname, self.cluster.id)

    @property
    def config(self):
        """config getter."""
        config = {}
        try:
            if self.config_data:
                config.update(json.loads(self.config_data))

            config.update({
                'hostid': self.id,
                'hostname': self.hostname,
            })
            if self.cluster:
                config.update({
                    'clusterid': self.cluster.id,
                    'clustername': self.cluster.name,
                    'fullname': self.fullname,
                })

            if self.machine:
                util.merge_dict(
                    config, {
                        'networking': {
                            'interfaces': {
                                'management': {
                                    'mac': self.machine.mac
                                }
                            }
                        },
                        'switch_port': self.machine.port,
                        'vlan': self.machine.vlan,
                    })
                if self.machine.switch:
                    util.merge_dict(
                        config, {'switch_ip': self.machine.switch.ip})

        except Exception as error:
            logging.error('failed to load config %s: %s',
                          self.hostname, self.config_data)
            logging.exception(error)
            raise error

        return config

    @config.setter
    def config(self, value):
        """config setter"""
        if not self.config_data:
            config = {
            }
            self.config_data = json.dumps(config)

        if value:
            try:
                config = json.loads(self.config_data)
                util.merge_dict(config, value)

                self.config_data = json.dumps(config)
            except Exception as error:
                logging.error('failed to dump config %s: %s',
                              self.hostname, value)
                logging.exception(error)
                raise error


class LogProgressingHistory(BASE):
    """host installing log history for each file.

    :param id: int, identity as primary key.
    :param pathname: str, the full path of the installing log file. unique.
    :param position: int, the position of the log file it has processed.
    :param partial_line: str, partial line of the log.
    :param progressing: float, indicate the installing progress between 0 to 1.
    :param message: str, str, the installing message.
    :param severity: Enum, the installing message severity.
                     ('ERROR', 'WARNING', 'INFO')
    :param line_matcher_name: str, the line matcher name of the log processor.
    :param update_timestamp: datetime, the latest timestamp the entry updated.
    """
    __tablename__ = 'log_progressing_history'
    id = Column(Integer, primary_key=True)
    pathname = Column(String(80), unique=True)
    position = Column(Integer, ColumnDefault(0))
    partial_line = Column(Text)
    progress = Column(Float, ColumnDefault(0.0))
    message = Column(Text)
    severity = Column(Enum('ERROR', 'WARNING', 'INFO'), ColumnDefault('INFO'))
    line_matcher_name = Column(String(80), ColumnDefault('start'))
    update_timestamp = Column(DateTime, default=datetime.now,
                              onupdate=datetime.now)

    def __init__(self, **kwargs):
        super(LogProgressingHistory, self).__init__(**kwargs)

    def __repr__(self):
        return (
            'LogProgressingHistory[%r: position %r,'
            'partial_line %r,progress %r,message %r,'
            'severity %r]'
        ) % (
            self.pathname, self.position,
            self.partial_line,
            self.progress,
            self.message,
            self.severity
        )


class Adapter(BASE):
    """Table stores ClusterHost installing Adapter information.

    :param id: int, identity as primary key.
    :param name: string, adapter name, unique.
    :param os: string, os name for installing the host.
    :param target_system: string, target system to be installed on the host.
    :param clusters: refer to the list of Cluster.
    """
    __tablename__ = 'adapter'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True)
    os = Column(String(80))
    target_system = Column(String(80))
    __table_args__ = (
        UniqueConstraint('os', 'target_system', name='unique_adapter'),)

    def __init__(self, **kwargs):
        super(Adapter, self).__init__(**kwargs)

    def __repr__(self):
        return '<Adapter %r: os %r, target_system %r>' % (
            self.name, self.os, self.target_system
        )


class Role(BASE):
    """The Role table stores avaiable roles of one target system.

       .. note::
          the host can be deployed to one or several roles in the cluster.

    :param id: int, identity as primary key.
    :param name: role name.
    :param target_system: str, the target_system.
    :param description: str, the description of the role.
    """
    __tablename__ = 'role'
    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True)
    target_system = Column(String(80))
    description = Column(Text)

    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)

    def __repr__(self):
        return '<Role %r : target_system %r, description:%r>' % (
            self.name, self.target_system, self.description)
