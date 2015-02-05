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

from compass.db import callback as metadata_callback
from compass.db import exception
from compass.db import validator as metadata_validator
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
    created_at = Column(DateTime, default=lambda: datetime.datetime.now())
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(),
                        onupdate=lambda: datetime.datetime.now())


class HelperMixin(object):
    def initialize(self):
        self.update()

    def update(self):
        pass

    @staticmethod
    def type_compatible(value, column_type):
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


class MetadataMixin(HelperMixin):
    name = Column(String(80), nullable=False)
    display_name = Column(String(80))
    path = Column(String(256))
    description = Column(Text)
    is_required = Column(Boolean, default=False)
    required_in_whole_config = Column(Boolean, default=False)
    mapping_to = Column(String(80), default='')
    _validator = Column('validator', Text)
    js_validator = Column(Text)
    default_value = Column(JSONEncoded)
    _default_callback = Column('default_callback', Text)
    default_callback_params = Column(
        'default_callback_params', JSONEncoded, default={}
    )
    options = Column(JSONEncoded)
    _options_callback = Column('options_callback', Text)
    options_callback_params = Column(
        'options_callback_params', JSONEncoded, default={}
    )
    _autofill_callback = Column('autofill_callback', Text)
    autofill_callback_params = Column(
        'autofill_callback_params', JSONEncoded, default={}
    )
    required_in_options = Column(Boolean, default=False)

    def initialize(self):
        if not self.display_name:
            if self.name:
                self.display_name = self.name
        super(MetadataMixin, self).initialize()

    def validate(self):
        super(MetadataMixin, self).validate()
        if not self.name:
            raise exception.InvalidParamter(
                'name is not set in os metadata %s' % self.id
            )

    @property
    def validator(self):
        if not self._validator:
            return None
        func = eval(
            self._validator,
            metadata_validator.VALIDATOR_GLOBALS,
            metadata_validator.VALIDATOR_LOCALS
        )
        if not callable(func):
            raise Exception(
                'validator %s is not callable' % self._validator
            )
        return func

    @validator.setter
    def validator(self, value):
        if not value:
            self._validator = None
        elif isinstance(value, basestring):
            self._validator = value
        elif callable(value):
            self._validator = value.func_name
        else:
            raise Exception(
                'validator %s is not callable' % value
            )

    @property
    def default_callback(self):
        if not self._default_callback:
            return None
        func = eval(
            self._default_callback,
            metadata_callback.CALLBACK_GLOBALS,
            metadata_callback.CALLBACK_LOCALS
        )
        if not callable(func):
            raise Exception(
                'default callback %s is not callable' % self._default_callback
            )
        return func

    @default_callback.setter
    def default_callback(self, value):
        if not value:
            self._default_callback = None
        elif isinstance(value, basestring):
            self._default_callback = value
        elif callable(value):
            self._default_callback = value.func_name
        else:
            raise Exception(
                'default callback %s is not callable' % value
            )

    @property
    def options_callback(self):
        if not self._options_callback:
            return None
        func = eval(
            self._options_callback,
            metadata_callback.CALLBACK_GLOBALS,
            metadata_callback.CALLBACK_LOCALS
        )
        if not callable(func):
            raise Exception(
                'options callback %s is not callable' % self._options_callback
            )
        return func

    @options_callback.setter
    def options_callback(self, value):
        if not value:
            self._options_callback = None
        elif isinstance(value, basestring):
            self._options_callback = value
        elif callable(value):
            self._options_callback = value.func_name
        else:
            raise Exception(
                'options callback %s is not callable' % value
            )

    @property
    def autofill_callback(self):
        if not self._autofill_callback:
            return None
        func = eval(
            self._autofill_callback,
            metadata_callback.CALLBACK_GLOBALS,
            metadata_callback.CALLBACK_LOCALS
        )
        if not callable(func):
            raise Exception(
                'autofill callback %s is not callable' % (
                    self._autofill_callback
                )
            )
        return func

    @autofill_callback.setter
    def autofill_callback(self, value):
        if not value:
            self._autofill_callback = None
        elif isinstance(value, basestring):
            self._autofill_callback = value
        elif callable(value):
            self._autofill_callback = value.func_name
        else:
            raise Exception(
                'autofill callback %s is not callable' % value
            )

    def to_dict(self):
        self_dict_info = {}
        if self.field:
            self_dict_info.update(self.field.to_dict())
        else:
            self_dict_info['field_type_data'] = 'dict'
            self_dict_info['field_type'] = dict
        self_dict_info.update(super(MetadataMixin, self).to_dict())
        validator = self.validator
        if validator:
            self_dict_info['validator'] = validator
        default_callback = self.default_callback
        if default_callback:
            self_dict_info['default_callback'] = default_callback
        options_callback = self.options_callback
        if options_callback:
            self_dict_info['options_callback'] = options_callback
        autofill_callback = self.autofill_callback
        if autofill_callback:
            self_dict_info['autofill_callback'] = autofill_callback
        js_validator = self.js_validator
        if js_validator:
            self_dict_info['js_validator'] = js_validator
        dict_info = {
            '_self': self_dict_info
        }
        for child in self.children:
            dict_info.update(child.to_dict())
        return {
            self.name: dict_info
        }
        return dict_info


class FieldMixin(HelperMixin):
    id = Column(Integer, primary_key=True)
    field = Column(String(80), unique=True, nullable=False)
    field_type_data = Column(
        'field_type',
        Enum(
            'basestring', 'int', 'float', 'list', 'bool',
            'dict', 'object'
        ),
        ColumnDefault('basestring')
    )
    display_type = Column(
        Enum(
            'checkbox', 'radio', 'select',
            'multiselect', 'combobox', 'text',
            'multitext', 'password'
        ),
        ColumnDefault('text')
    )
    _validator = Column('validator', Text)
    js_validator = Column(Text)
    description = Column(Text)

    @property
    def field_type(self):
        if not self.field_type_data:
            return None
        field_type = eval(self.field_type_data)
        if not type(field_type) == type:
            raise Exception(
                '%s is not type' % self.field_type_data
            )
        return field_type

    @field_type.setter
    def field_type(self, value):
        if not value:
            self.field_type_data = None
        elif isinstance(value, basestring):
            self.field_type_data = value
        elif type(value) == type:
            self.field_type_data = value.__name__
        else:
            raise Exception(
                '%s is not type' % value
            )

    @property
    def validator(self):
        if not self._validator:
            return None
        func = eval(
            self._validator,
            metadata_validator.VALIDATOR_GLOBALS,
            metadata_validator.VALIDATOR_LOCALS
        )
        if not callable(func):
            raise Exception(
                '%s is not callable' % self._validator
            )
        return func

    @validator.setter
    def validator(self, value):
        if not value:
            self._validator = None
        elif isinstance(value, basestring):
            self._validator = value
        elif callable(value):
            self._validator = value.func_name
        else:
            raise Exception(
                '%s is not callable' % value
            )

    def to_dict(self):
        dict_info = super(FieldMixin, self).to_dict()
        dict_info['field_type'] = self.field_type
        validator = self.validator
        if validator:
            dict_info['validator'] = self.validator
        js_validator = self.js_validator
        if js_validator:
            dict_info['js_validator'] = self.js_validator
        return dict_info


class InstallerMixin(HelperMixin):
    name = Column(String(80), nullable=False)
    alias = Column(String(80), unique=True, nullable=False)
    settings = Column(JSONEncoded, default={})

    def validate(self):
        super(InstallerMixin, self).validate()
        if not self.name:
            raise exception.InvalidParameter(
                'name is not set in installer %s' % self.name
            )


class StateMixin(TimestampMixin, HelperMixin):
    state = Column(
        Enum(
            'UNINITIALIZED', 'INITIALIZED',
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

    def update(self):
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
    ip_int = Column(BigInteger, unique=True, nullable=False)
    is_mgmt = Column(Boolean, default=False)
    is_promiscuous = Column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint('host_id', 'interface', name='constraint'),
    )

    def __init__(self, host_id, interface, **kwargs):
        self.host_id = host_id
        self.interface = interface
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
        super(ClusterHostState, self).update()
        host_state = self.clusterhost.host.state
        if self.state == 'INITIALIZED':
            if host_state.state in ['UNINITIALIZED']:
                host_state.state = 'INITIALIZED'
                host_state.update()
        elif self.state == 'INSTALLING':
            if host_state.state in ['UNINITIALIZED', 'INITIALIZED']:
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
    _roles = Column('roles', JSONEncoded, default=[])
    config_step = Column(String(80), default='')
    package_config = Column(JSONEncoded, default={})
    config_validated = Column(Boolean, default=False)
    deployed_package_config = Column(JSONEncoded, default={})

    log_history = relationship(
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
    def distributed_system_name(self):
        return self.cluster.distributed_system_name

    @distributed_system_name.expression
    def distributed_system_name(cls):
        return cls.cluster.distributed_system_name

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
        role_names = list(self._roles)
        if not role_names:
            return []
        flavor = self.cluster.flavor
        if not flavor:
            return []
        roles = []
        for flavor_role in flavor.ordered_flavor_roles:
            role = flavor_role.role
            if role.name in role_names:
                roles.append(role)
        return roles

    @roles.setter
    def roles(self, value):
        self._roles = list(value)
        self.config_validated = False

    @property
    def patched_roles(self):
        return self.roles

    @patched_roles.setter
    def patched_roles(self, value):
        roles = list(self._roles)
        roles.extend(value)
        self._roles = roles
        self.config_validated = False

    @hybrid_property
    def owner(self):
        return self.cluster.owner

    @owner.expression
    def owner(cls):
        return cls.cluster.owner

    def state_dict(self):
        cluster = self.cluster
        host = self.host
        host_state = host.state_dict()
        if not cluster.distributed_system:
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
            'distributed_system_name': self.distributed_system_name,
            'distributed_system_installed': self.distributed_system_installed,
            'reinstall_distributed_system': self.reinstall_distributed_system,
            'owner': self.owner,
            'clustername': self.clustername,
            'name': self.name,
            'state': state_dict['state']
        })
        roles = self.roles
        dict_info['roles'] = [
            role.to_dict() for role in roles
        ]
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

    name = Column(String(80), unique=True, nullable=True)
    os_id = Column(Integer, ForeignKey('os.id'))
    config_step = Column(String(80), default='')
    os_config = Column(JSONEncoded, default={})
    config_validated = Column(Boolean, default=False)
    deployed_os_config = Column(JSONEncoded, default={})
    os_name = Column(String(80))
    creator_id = Column(Integer, ForeignKey('user.id'))
    owner = Column(String(80))
    os_installer_id = Column(
        Integer,
        ForeignKey('os_installer.id')
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
    log_history = relationship(
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
        os = self.os
        if os:
            self.os_name = os.name
        else:
            self.os_name = None
        self.state.update()
        super(Host, self).update()

    def validate(self):
        super(Host, self).validate()
        creator = self.creator
        if not creator:
            raise exception.InvalidParameter(
                'creator is not set in host %s' % self.id
            )
        os = self.os
        if not os:
            raise exception.InvalidParameter(
                'os is not set in host %s' % self.id
            )
        os_installer = self.os_installer
        if not os_installer:
            raise exception.Invalidparameter(
                'os_installer is not set in host %s' % self.id
            )
        if not os.deployable:
            raise exception.InvalidParameter(
                'os %s is not deployable in host %s' % (os.name, self.id)
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
            'os_installer': self.os_installer.to_dict(),
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
        cluster = self.cluster
        clusterhosts = cluster.clusterhosts
        self.total_hosts = len(clusterhosts)
        if self.state in ['UNINITIALIZED', 'INITIALIZED', 'INSTALLING']:
            self.installing_hosts = 0
            self.failed_hosts = 0
            self.completed_hosts = 0
        if self.state == 'INSTALLING':
            cluster.reinstall_distributed_system = False
            if not cluster.distributed_system:
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
            self.message = (
                'total %s, installing %s, completed: %s, error %s'
            ) % (
                self.total_hosts, self.installing_hosts,
                self.completed_hosts, self.failed_hosts
            )
            if self.failed_hosts:
                self.severity = 'ERROR'
        super(ClusterState, self).update()


class Cluster(BASE, TimestampMixin, HelperMixin):
    """Cluster table."""
    __tablename__ = 'cluster'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True, nullable=False)
    reinstall_distributed_system = Column(Boolean, default=True)
    config_step = Column(String(80), default='')
    os_id = Column(Integer, ForeignKey('os.id'))
    os_name = Column(String(80))
    flavor_id = Column(
        Integer,
        ForeignKey('adapter_flavor.id'),
        nullable=True
    )
    flavor_name = Column(String(80), nullable=True)
    distributed_system_id = Column(
        Integer, ForeignKey('distributed_system.id'),
        nullable=True
    )
    distributed_system_name = Column(
        String(80), nullable=True
    )
    os_config = Column(JSONEncoded, default={})
    package_config = Column(JSONEncoded, default={})
    deployed_os_config = Column(JSONEncoded, default={})
    deployed_package_config = Column(JSONEncoded, default={})
    config_validated = Column(Boolean, default=False)
    adapter_id = Column(Integer, ForeignKey('adapter.id'))
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

    def __init__(self, name, **kwargs):
        self.name = name
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
        os = self.os
        if os:
            self.os_name = os.name
        else:
            self.os_name = None
            self.os_config = {}
        adapter = self.adapter
        if adapter:
            self.adapter_name = adapter.name
            distributed_system = adapter.adapter_distributed_system
            self.distributed_system = distributed_system
            if distributed_system:
                self.distributed_system_name = distributed_system.name
            else:
                self.distributed_system_name = None
            flavor = self.flavor
            if flavor:
                self.flavor_name = flavor.name
            else:
                self.flavor_name = None
        self.state.update()
        super(Cluster, self).update()

    def validate(self):
        super(Cluster, self).validate()
        creator = self.creator
        if not creator:
            raise exception.InvalidParameter(
                'creator is not set in cluster %s' % self.id
            )
        os = self.os
        if not os:
            raise exception.InvalidParameter(
                'os is not set in cluster %s' % self.id
            )
        if not os.deployable:
            raise exception.InvalidParameter(
                'os %s is not deployable' % os.name
            )
        adapter = self.adapter
        if not adapter:
            raise exception.InvalidParameter(
                'adapter is not set in cluster %s' % self.id
            )
        if not adapter.deployable:
            raise exception.InvalidParameter(
                'adapter %s is not deployable' % adapter.name
            )
        supported_os_ids = [
            adapter_os.os.id for adapter_os in adapter.supported_oses
        ]
        if os.id not in supported_os_ids:
            raise exception.InvalidParameter(
                'os %s is not supported' % os.name
            )
        distributed_system = self.distributed_system
        if distributed_system:
            if not distributed_system.deployable:
                raise exception.InvalidParamerter(
                    'distributed system %s is not deployable' % (
                        distributed_system.name
                    )
                )
        flavor = self.flavor
        if not flavor:
            if distributed_system:
                raise exception.InvalidParameter(
                    'flavor is not set in cluster %s' % self.id
                )
        else:
            flavor_adapter_id = flavor.adapter_id
            adapter_id = self.adapter_id
            if flavor_adapter_id != adapter_id:
                raise exception.InvalidParameter(
                    'flavor adapter id %s does not match adapter id %s' % (
                        flavor_adapter_id, adapter_id
                    )
                )

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
        if self.flavor:
            dict_info['flavor'] = self.flavor.to_dict()
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
        filters = self.switch.filters
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
        if isinstance(filters, basestring):
            filters = filters.replace('\r\n', '\n').replace('\n', ';')
            filters = [
                switch_filter for switch_filter in filters.split(';')
                if switch_filter
            ]
        if not isinstance(filters, list):
            filters = [filters]
        switch_filters = []
        for switch_filter in filters:
            if not switch_filter:
                continue
            if isinstance(switch_filter, basestring):
                filter_dict = {}
                filter_items = [
                    item for item in switch_filter.split() if item
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
                switch_filter = filter_dict
            if not isinstance(switch_filter, dict):
                raise exception.InvalidParameter(
                    'filter %s is not dict' % switch_filter
                )
            if 'filter_type' in switch_filter:
                if switch_filter['filter_type'] not in ['allow', 'deny']:
                    raise exception.InvalidParameter(
                        'filter_type should be `allow` or `deny` in %s' % (
                            switch_filter
                        )
                    )
            if 'ports' in switch_filter:
                if isinstance(switch_filter['ports'], basestring):
                    switch_filter['ports'] = [
                        port_or_ports
                        for port_or_ports in switch_filter['ports'].split(',')
                        if port_or_ports
                    ]
                if not isinstance(switch_filter['ports'], list):
                    raise exception.InvalidParameter(
                        '`ports` type is not list in filter %s' % switch_filter
                    )
                for port_or_ports in switch_filter['ports']:
                    if not isinstance(port_or_ports, basestring):
                        raise exception.InvalidParameter(
                            '%s type is not basestring in `ports` %s' % (
                                port_or_ports, switch_filter['ports']
                            )
                        )
            for key in ['port_start', 'port_end']:
                if key in switch_filter:
                    if isinstance(switch_filter[key], basestring):
                        if switch_filter[key].isdigit():
                            switch_filter[key] = int(switch_filter[key])
                    if not isinstance(switch_filter[key], int):
                        raise exception.InvalidParameter(
                            '`%s` type is not int in filer %s' % (
                                key, switch_filter
                            )
                        )
            switch_filters.append(switch_filter)
        return switch_filters

    @classmethod
    def format_filters(cls, filters):
        filter_strs = []
        for switch_filter in filters:
            filter_properties = []
            filter_properties.append(
                switch_filter.get('filter_type', 'allow')
            )
            if 'ports' in switch_filter:
                filter_properties.append(
                    'ports ' + ','.join(switch_filter['ports'])
                )
            if 'port_prefix' in switch_filter:
                filter_properties.append(
                    'port_prefix ' + switch_filter['port_prefix']
                )
            if 'port_suffix' in switch_filter:
                filter_properties.append(
                    'port_suffix ' + switch_filter['port_suffix']
                )
            if 'port_start' in switch_filter:
                filter_properties.append(
                    'port_start ' + str(switch_filter['port_start'])
                )
            if 'port_end' in switch_filter:
                filter_properties.append(
                    'port_end ' + str(switch_filter['port_end'])
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
    def filters(self):
        return self._filters

    @filters.setter
    def filters(self, value):
        if not value:
            return
        self._filters = self.parse_filters(value)

    @property
    def put_filters(self):
        return self._filters

    @put_filters.setter
    def put_filters(self, value):
        if not value:
            return
        self._filters = self.parse_filters(value)

    @property
    def patched_filters(self):
        return self._filters

    @patched_filters.setter
    def patched_filters(self, value):
        if not value:
            return
        filters = list(self.filters)
        self.filters = self.parse_filters(value) + filters

    def to_dict(self):
        dict_info = super(Switch, self).to_dict()
        dict_info['ip'] = self.ip
        dict_info['filters'] = self.format_filters(self._filters)
        return dict_info


class OSConfigMetadata(BASE, MetadataMixin):
    """OS config metadata."""
    __tablename__ = "os_config_metadata"

    id = Column(Integer, primary_key=True)
    os_id = Column(
        Integer,
        ForeignKey(
            'os.id', onupdate='CASCADE', ondelete='CASCADE'
        )
    )
    parent_id = Column(
        Integer,
        ForeignKey(
            'os_config_metadata.id', onupdate='CASCADE', ondelete='CASCADE'
        )
    )
    field_id = Column(
        Integer,
        ForeignKey(
            'os_config_field.id', onupdate='CASCADE', ondelete='CASCADE'
        )
    )
    children = relationship(
        'OSConfigMetadata',
        passive_deletes=True, passive_updates=True,
        backref=backref('parent', remote_side=id)
    )
    __table_args__ = (
        UniqueConstraint('path', 'os_id', name='constraint'),
    )

    def __init__(self, os_id, path, **kwargs):
        self.os_id = os_id
        self.path = path
        super(OSConfigMetadata, self).__init__(**kwargs)

    def validate(self):
        super(OSConfigMetadata, self).validate()
        if not self.os:
            raise exception.InvalidParameter(
                'os is not set in os metadata %s' % self.id
            )


class OSConfigField(BASE, FieldMixin):
    """OS config fields."""
    __tablename__ = 'os_config_field'

    metadatas = relationship(
        OSConfigMetadata,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('field'))

    def __init__(self, field, **kwargs):
        self.field = field
        super(OSConfigField, self).__init__(**kwargs)


class AdapterOS(BASE, HelperMixin):
    """Adapter OS table."""
    __tablename__ = 'adapter_os'

    adapter_os_id = Column('id', Integer, primary_key=True)
    os_id = Column(
        Integer,
        ForeignKey(
            'os.id',
            onupdate='CASCADE', ondelete='CASCADE'
        )
    )
    adapter_id = Column(
        Integer,
        ForeignKey(
            'adapter.id',
            onupdate='CASCADE', ondelete='CASCADE'
        )
    )

    def __init__(self, os_id, adapter_id, **kwargs):
        self.os_id = os_id
        self.adapter_id = adapter_id
        super(AdapterOS, self).__init__(**kwargs)

    def to_dict(self):
        dict_info = self.os.to_dict()
        dict_info.update(super(AdapterOS, self).to_dict())
        return dict_info


class OperatingSystem(BASE, HelperMixin):
    """OS table."""
    __tablename__ = 'os'

    id = Column(Integer, primary_key=True)
    parent_id = Column(
        Integer,
        ForeignKey('os.id', onupdate='CASCADE', ondelete='CASCADE'),
        nullable=True
    )
    name = Column(String(80), unique=True, nullable=False)
    deployable = Column(Boolean, default=False)

    metadatas = relationship(
        OSConfigMetadata,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('os')
    )
    clusters = relationship(
        Cluster,
        backref=backref('os')
    )
    hosts = relationship(
        Host,
        backref=backref('os')
    )
    children = relationship(
        'OperatingSystem',
        passive_deletes=True, passive_updates=True,
        backref=backref('parent', remote_side=id)
    )
    supported_adapters = relationship(
        AdapterOS,
        passive_deletes=True, passive_updates=True,
        backref=backref('os')
    )

    def __init__(self, name):
        self.name = name
        super(OperatingSystem, self).__init__()

    def __str__(self):
        return 'OperatingSystem[%s:%s]' % (self.id, self.name)

    @property
    def root_metadatas(self):
        return [
            metadata for metadata in self.metadatas
            if metadata.parent_id is None
        ]

    def metadata_dict(self):
        dict_info = {}
        if self.parent:
            dict_info.update(self.parent.metadata_dict())
        for metadata in self.root_metadatas:
            util.merge_dict(dict_info, metadata.to_dict())
        return dict_info

    @property
    def os_supported_adapters(self):
        supported_adapters = self.supported_adapters
        if supported_adapters:
            return supported_adapters
        parent = self.parent
        if parent:
            return parent.os_supported_adapters
        else:
            return []


class AdapterFlavorRole(BASE, HelperMixin):
    """Adapter flavor roles."""

    __tablename__ = 'adapter_flavor_role'

    flavor_id = Column(
        Integer,
        ForeignKey(
            'adapter_flavor.id',
            onupdate='CASCADE', ondelete='CASCADE'
        ),
        primary_key=True
    )
    role_id = Column(
        Integer,
        ForeignKey(
            'adapter_role.id',
            onupdate='CASCADE', ondelete='CASCADE'
        ),
        primary_key=True
    )

    def __init__(self, flavor_id, role_id):
        self.flavor_id = flavor_id
        self.role_id = role_id
        super(AdapterFlavorRole, self).__init__()

    def __str__(self):
        return 'AdapterFlavorRole[%s:%s]' % (self.flavor_id, self.role_id)

    def validate(self):
        super(AdapterFlavorRole, self).validate()
        flavor_adapter_id = self.flavor.adapter_id
        role_adapter_id = self.role.adapter_id
        if flavor_adapter_id != role_adapter_id:
            raise exception.InvalidParameter(
                'flavor adapter %s and role adapter %s does not match' % (
                    flavor_adapter_id, role_adapter_id
                )
            )

    def to_dict(self):
        dict_info = super(AdapterFlavorRole, self).to_dict()
        dict_info.update(
            self.role.to_dict()
        )
        return dict_info


class AdapterFlavor(BASE, HelperMixin):
    """Adapter's flavors."""

    __tablename__ = 'adapter_flavor'

    id = Column(Integer, primary_key=True)
    adapter_id = Column(
        Integer,
        ForeignKey('adapter.id', onupdate='CASCADE', ondelete='CASCADE')
    )
    name = Column(String(80), nullable=False)
    display_name = Column(String(80))
    template = Column(String(80))
    _ordered_flavor_roles = Column(
        'ordered_flavor_roles', JSONEncoded, default=[]
    )

    flavor_roles = relationship(
        AdapterFlavorRole,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('flavor')
    )
    clusters = relationship(
        Cluster,
        backref=backref('flavor')
    )

    __table_args__ = (
        UniqueConstraint('name', 'adapter_id', name='constraint'),
    )

    def __str__(self):
        return 'AdapterFlavor[%s:%s]' % (self.id, self.name)

    @property
    def ordered_flavor_roles(self):
        flavor_roles = dict([
            (flavor_role.role.name, flavor_role)
            for flavor_role in self.flavor_roles
        ])
        ordered_flavor_roles = []
        for flavor_role in list(self._ordered_flavor_roles):
            if flavor_role in flavor_roles:
                ordered_flavor_roles.append(flavor_roles[flavor_role])
        return ordered_flavor_roles

    @ordered_flavor_roles.setter
    def ordered_flavor_roles(self, value):
        self._ordered_flavor_roles = list(value)

    @property
    def patched_ordered_flavor_roles(self):
        return self.ordered_flavor_roles

    @patched_ordered_flavor_roles.setter
    def patched_ordered_flavor_roles(self, value):
        ordered_flavor_roles = list(self._ordered_flavor_roles)
        ordered_flavor_roles.extend(value)
        self._ordered_flavor_roles = ordered_flavor_roles

    def __init__(self, name, adapter_id, **kwargs):
        self.name = name
        self.adapter_id = adapter_id
        super(AdapterFlavor, self).__init__(**kwargs)

    def initialize(self):
        if not self.display_name:
            self.display_name = self.name
        super(AdapterFlavor, self).initialize()

    def validate(self):
        super(AdapterFlavor, self).validate()
        if not self.template:
            raise exception.InvalidParameter(
                'template is not set in adapter flavor %s' % self.id
            )

    def to_dict(self):
        dict_info = super(AdapterFlavor, self).to_dict()
        dict_info['roles'] = [
            flavor_role.to_dict()
            for flavor_role in self.ordered_flavor_roles
        ]
        return dict_info


class AdapterRole(BASE, HelperMixin):
    """Adapter's roles."""

    __tablename__ = "adapter_role"
    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    display_name = Column(String(80))
    description = Column(Text)
    optional = Column(Boolean, default=False)
    adapter_id = Column(
        Integer,
        ForeignKey(
            'adapter.id',
            onupdate='CASCADE',
            ondelete='CASCADE'
        )
    )

    flavor_roles = relationship(
        AdapterFlavorRole,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('role')
    )

    __table_args__ = (
        UniqueConstraint('name', 'adapter_id', name='constraint'),
    )

    def __init__(self, name, adapter_id, **kwargs):
        self.name = name
        self.adapter_id = adapter_id
        super(AdapterRole, self).__init__(**kwargs)

    def __str__(self):
        return 'AdapterRole[%s:%s]' % (self.id, self.name)

    def initialize(self):
        if not self.description:
            self.description = self.name
        if not self.display_name:
            self.display_name = self.name
        super(AdapterRole, self).initialize()


class PackageConfigMetadata(BASE, MetadataMixin):
    """package config metadata."""
    __tablename__ = "package_config_metadata"

    id = Column(Integer, primary_key=True)
    adapter_id = Column(
        Integer,
        ForeignKey(
            'adapter.id',
            onupdate='CASCADE', ondelete='CASCADE'
        )
    )
    parent_id = Column(
        Integer,
        ForeignKey(
            'package_config_metadata.id',
            onupdate='CASCADE', ondelete='CASCADE'
        )
    )
    field_id = Column(
        Integer,
        ForeignKey(
            'package_config_field.id',
            onupdate='CASCADE', ondelete='CASCADE'
        )
    )
    children = relationship(
        'PackageConfigMetadata',
        passive_deletes=True, passive_updates=True,
        backref=backref('parent', remote_side=id)
    )

    __table_args__ = (
        UniqueConstraint('path', 'adapter_id', name='constraint'),
    )

    def __init__(
        self, adapter_id, path, **kwargs
    ):
        self.adapter_id = adapter_id
        self.path = path
        super(PackageConfigMetadata, self).__init__(**kwargs)

    def validate(self):
        super(PackageConfigMetadata, self).validate()
        if not self.adapter:
            raise exception.InvalidParameter(
                'adapter is not set in package metadata %s' % self.id
            )


class PackageConfigField(BASE, FieldMixin):
    """Adapter cofig metadata fields."""
    __tablename__ = "package_config_field"

    metadatas = relationship(
        PackageConfigMetadata,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('field'))

    def __init__(self, field, **kwargs):
        self.field = field
        super(PackageConfigField, self).__init__(**kwargs)


class Adapter(BASE, HelperMixin):
    """Adapter table."""
    __tablename__ = 'adapter'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True, nullable=False)
    display_name = Column(String(80))
    parent_id = Column(
        Integer,
        ForeignKey(
            'adapter.id',
            onupdate='CASCADE', ondelete='CASCADE'
        ),
        nullable=True
    )
    distributed_system_id = Column(
        Integer,
        ForeignKey(
            'distributed_system.id',
            onupdate='CASCADE', ondelete='CASCADE'
        ),
        nullable=True
    )
    os_installer_id = Column(
        Integer,
        ForeignKey(
            'os_installer.id',
            onupdate='CASCADE', ondelete='CASCADE'
        ),
        nullable=True
    )
    package_installer_id = Column(
        Integer,
        ForeignKey(
            'package_installer.id',
            onupdate='CASCADE', ondelete='CASCADE'
        ),
        nullable=True
    )
    deployable = Column(
        Boolean, default=False
    )

    health_check_cmd = Column(String(80))

    supported_oses = relationship(
        AdapterOS,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('adapter')
    )

    roles = relationship(
        AdapterRole,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('adapter')
    )
    flavors = relationship(
        AdapterFlavor,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('adapter')
    )
    children = relationship(
        'Adapter',
        passive_deletes=True, passive_updates=True,
        backref=backref('parent', remote_side=id)
    )
    metadatas = relationship(
        PackageConfigMetadata,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('adapter')
    )
    clusters = relationship(
        Cluster,
        backref=backref('adapter')
    )

    __table_args__ = (
        UniqueConstraint(
            'distributed_system_id',
            'os_installer_id', 'package_installer_id', name='constraint'
        ),
    )

    def __init__(
        self, name, **kwargs
    ):
        self.name = name
        super(Adapter, self).__init__(**kwargs)

    def __str__(self):
        return 'Adapter[%s:%s]' % (self.id, self.name)

    def initialize(self):
        if not self.display_name:
            self.display_name = self.name
        super(Adapter, self).initialize()

    @property
    def root_metadatas(self):
        return [
            metadata for metadata in self.metadatas
            if metadata.parent_id is None
        ]

    def metadata_dict(self):
        dict_info = {}
        if self.parent:
            dict_info.update(self.parent.metadata_dict())
        for metadata in self.root_metadatas:
            util.merge_dict(dict_info, metadata.to_dict())
        return dict_info

    @property
    def adapter_package_installer(self):
        if self.package_installer:
            return self.package_installer
        elif self.parent:
            return self.parent.adapter_package_installer
        else:
            return None

    @property
    def adapter_os_installer(self):
        if self.os_installer:
            return self.os_installer
        elif self.parent:
            return self.parent.adapter_os_installer
        else:
            return None

    @property
    def adapter_distributed_system(self):
        distributed_system = self.distributed_system
        if distributed_system:
            return distributed_system
        parent = self.parent
        if parent:
            return parent.adapter_distributed_system
        else:
            return None

    @property
    def adapter_supported_oses(self):
        supported_oses = self.supported_oses
        if supported_oses:
            return supported_oses
        parent = self.parent
        if parent:
            return parent.adapter_supported_oses
        else:
            return []

    @property
    def adapter_roles(self):
        roles = self.roles
        if roles:
            return roles
        parent = self.parent
        if parent:
            return parent.adapter_roles
        else:
            return []

    @property
    def adapter_flavors(self):
        flavors = self.flavors
        if flavors:
            return flavors
        parent = self.parent
        if parent:
            return parent.adapter_flavors
        else:
            return []

    def to_dict(self):
        dict_info = super(Adapter, self).to_dict()
        dict_info.update({
            'supported_oses': [
                adapter_os.to_dict()
                for adapter_os in self.adapter_supported_oses
            ],
            'flavors': [
                flavor.to_dict() for flavor in self.adapter_flavors
            ]
        })
        distributed_system = self.adapter_distributed_system
        if distributed_system:
            dict_info['distributed_system_id'] = distributed_system.id
            dict_info['distributed_system_name'] = distributed_system.name
        os_installer = self.adapter_os_installer
        if os_installer:
            dict_info['os_installer'] = os_installer.to_dict()
        package_installer = self.adapter_package_installer
        if package_installer:
            dict_info['package_installer'] = package_installer.to_dict()
        return dict_info


class DistributedSystem(BASE, HelperMixin):
    """distributed system table."""
    __tablename__ = 'distributed_system'

    id = Column(Integer, primary_key=True)
    parent_id = Column(
        Integer,
        ForeignKey(
            'distributed_system.id',
            onupdate='CASCADE', ondelete='CASCADE'
        ),
        nullable=True
    )
    name = Column(String(80), unique=True, nullable=False)
    deployable = Column(Boolean, default=False)

    adapters = relationship(
        Adapter,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('distributed_system')
    )
    clusters = relationship(
        Cluster,
        backref=backref('distributed_system')
    )
    children = relationship(
        'DistributedSystem',
        passive_deletes=True, passive_updates=True,
        backref=backref('parent', remote_side=id)
    )

    def __init__(self, name):
        self.name = name
        super(DistributedSystem, self).__init__()

    def __str__(self):
        return 'DistributedSystem[%s:%s]' % (self.id, self.name)


class OSInstaller(BASE, InstallerMixin):
    """OS installer table."""
    __tablename__ = 'os_installer'
    id = Column(Integer, primary_key=True)
    adpaters = relationship(
        Adapter,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('os_installer')
    )
    hosts = relationship(
        Host,
        backref=backref('os_installer')
    )

    def __init__(self, alias, **kwargs):
        self.alias = alias
        super(OSInstaller, self).__init__(**kwargs)

    def __str__(self):
        return 'OSInstaller[%s:%s]' % (self.id, self.alias)


class PackageInstaller(BASE, InstallerMixin):
    """package installer table."""
    __tablename__ = 'package_installer'
    id = Column(Integer, primary_key=True)
    adapters = relationship(
        Adapter,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('package_installer')
    )

    def __init__(self, alias, **kwargs):
        self.alias = alias
        super(PackageInstaller, self).__init__(**kwargs)

    def __str__(self):
        return 'PackageInstaller[%s:%s]' % (self.id, self.alias)


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
