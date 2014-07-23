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
import datetime
import netaddr
import simplejson as json

from sqlalchemy import BigInteger
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.mutable import MutableDict
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
from compass.db import validator
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
        pass

    def validate(self):
        pass

    def to_dict(self):
        keys = self.__mapper__.columns.keys()
        dict_info = {}
        for key in keys:
            value = getattr(self, key)
            if value is not None:
                if isinstance(value, datetime.datetime):
                    value = util.format_datetime(value)
                dict_info[key] = value
        return dict_info


class MetadataMixin(HelperMixin):
    name = Column(String(80))
    display_name = Column(String(80))
    path = Column(String(256))
    description = Column(Text)
    is_required = Column(Boolean, default=False)
    required_in_whole_config = Column(Boolean, default=False)
    mapping_to = Column(JSONEncoded)
    validator_data = Column('validator', Text)
    js_validator = Column(Text)
    default_value = Column(JSONEncoded)
    options = Column(JSONEncoded, default=[])
    required_in_options = Column(Boolean, default=False)

    def initialize(self):
        if not self.display_name:
            self.display_name = self.name
        if self.parent:
            self.path = '%s/%s' % (self.parent.path, self.name)
        else:
            self.path = self.name
        super(MetadataMixin, self).initialize()

    def validate(self):
        if not self.adapter:
            raise exception.InvalidParameter(
                'adapter is not set in os metadata %s' % self.id
            )
        super(MetadataMixin, self).validate()

    @property
    def validator(self):
        if not self.validator_data:
            return None
        func = eval(
            self.validator_data,
            validator.VALIDATOR_GLOBALS,
            validator.VALIDATOR_LOCALS
        )
        if not callable(func):
            raise Exception(
                '%s is not callable' % self.validator_data
            )
        return func

    @validator.setter
    def validator(self, value):
        if not value:
            self.validator_data = None
        elif isinstance(value, basestring):
            self.validator_data = value
        elif callable(value):
            self.validator_data = value.func_name
        else:
            raise Exception(
                '%s is not callable' % value
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
            self_dict_info['validator_data'] = self.validator_data
            self_dict_info['validator'] = validator
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
    field = Column(String(80), unique=True)
    field_type_data = Column(
        'field_type',
        Enum('basestring', 'int', 'float', 'list', 'bool'),
        default='basestring'
    )
    display_type = Column(
        Enum(
            'checkbox', 'radio', 'select',
            'multiselect', 'combobox', 'text',
            'multitext', 'password'
        ),
        default='text'
    )
    validator_data = Column('validator', Text)
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
        if not self.validator_data:
            return None
        func = eval(
            self.validator_data,
            validator.VALIDATOR_GLOBALS,
            validator.VALIDATOR_LOCALS
        )
        if not callable(func):
            raise Exception(
                '%s is not callable' % self.validator_data
            )
        return func

    @validator.setter
    def validator(self, value):
        if not value:
            self.validator_data = None
        elif isinstance(value, basestring):
            self.validator_data = value
        elif callable(value):
            self.validator_data = value.func_name
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


class AdapterMixin(HelperMixin):
    name = Column(String(80), unique=True)

    @property
    def root_metadatas(self):
        return [
            metadata for metadata in self.metadatas
            if metadata.parent_id is None
        ]

    @property
    def adapter_installer(self):
        if self.installer:
            return self.installer
        elif self.parent:
            return self.parent.adapter_installer
        else:
            return None

    @property
    def installer_name(self):
        installer = self.adapter_installer
        if installer:
            return installer.name
        else:
            return ''

    @property
    def installer_type(self):
        installer = self.adapter_installer
        if installer:
            return installer.installer_type
        else:
            return None

    @property
    def installer_config(self):
        installer = self.adapter_installer
        if installer:
            return installer.config
        else:
            return None

    def metadata_dict(self):
        dict_info = {}
        if self.parent:
            dict_info.update(self.parent.metadata_dict())
        for metadata in self.root_metadatas:
            dict_info.update(metadata.to_dict())
        return dict_info

    def to_dict(self):
        dict_info = super(AdapterMixin, self).to_dict()
        dict_info.update({
            'installer_name': self.installer_name,
            'installer_type': self.installer_type,
            'installer_config': self.installer_config
        })
        return dict_info


class InstallerMixin(HelperMixin):
    name = Column(String(80), unique=True)
    installer_type = Column(String(80))
    config = Column(MutableDict.as_mutable(JSONEncoded), default={})

    def validate(self):
        if not self.installer_type:
            raise exception.InvalidParameter(
                'installer_type is not set in installer %s' % self.name
            )
        super(InstallerMixin, self).validate()


class StateMixin(TimestampMixin, HelperMixin):
    state = Column(
        Enum(
            'INITIALIZED', 'INSTALLING', 'SUCCESSFUL', 'ERROR'
        ),
        default='INITIALIZED'
    )
    progress = Column(Float, default=0.0)
    message = Column(Text, default='')
    severity = Column(
        Enum('INFO', 'WARNING', 'ERROR'),
        default='INFO'
    )

    def initialize(self):
        if self.severity == 'ERROR':
            self.state = 'ERROR'
        elif self.progress >= 1.0:
            self.state = 'SUCCESSFUL'
            self.progress = 1.0
        super(StateMixin, self).initialize()


class HostNetwork(BASE, TimestampMixin, HelperMixin):
    """Host network table."""
    __tablename__ = 'host_network'

    id = Column(Integer, primary_key=True)
    host_id = Column(
        Integer,
        ForeignKey('host.id', onupdate='CASCADE', ondelete='CASCADE')
    )
    interface = Column(
        String(80))
    subnet_id = Column(
        Integer,
        ForeignKey('network.id', onupdate='CASCADE', ondelete='CASCADE')
    )
    ip_int = Column(BigInteger, unique=True)
    is_mgmt = Column(Boolean, default=False)
    is_promiscuous = Column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint('host_id', 'interface', name='constraint'),
    )

    def __init__(self, host_id, **kwargs):
        self.host_id = host_id
        super(HostNetwork, self).__init__(**kwargs)

    @property
    def ip(self):
        return str(netaddr.IPAddress(self.ip_int))

    @ip.setter
    def ip(self, value):
        self.ip_int = int(netaddr.IPAddress(value))

    @hybrid_property
    def subnet(self):
        return self.network.subnet

    @property
    def netmask(self):
        return str(netaddr.IPNetwork(self.subnet).netmask)

    def validate(self):
        if not self.interface:
            raise exception.InvalidParameter(
                'interface is not set in host %s network' % self.host_id
            )
        if not self.network:
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
        try:
            netaddr.IPAddress(self.ip_int)
        except Exception:
            raise exception.InvalidParameter(
                'ip %s format is uncorrect in %s interface %s' % (
                    self.ip_int, self.host_id, self.interface
                )
            )
        ip = netaddr.IPAddress(self.ip_int)
        subnet = netaddr.IPNetwork(self.subnet)
        if ip not in subnet:
            raise exception.InvalidParameter(
                'ip %s is not in subnet %s' % (
                    str(ip), str(subnet)
                )
            )
        super(HostNetwork, self).validate()

    def to_dict(self):
        dict_info = super(HostNetwork, self).to_dict()
        dict_info['ip'] = self.ip
        dict_info['interface'] = self.interface
        dict_info['netmask'] = self.netmask
        return dict_info


class ClusterHostState(BASE, StateMixin):
    """ClusterHost state table."""
    __tablename__ = 'clusterhost_state'

    id = Column(
        Integer,
        ForeignKey('clusterhost.id', onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True
    )


class ClusterHost(BASE, TimestampMixin, HelperMixin):
    """ClusterHost table."""
    __tablename__ = 'clusterhost'

    id = Column(Integer, primary_key=True)
    cluster_id = Column(
        Integer,
        ForeignKey('cluster.id', onupdate='CASCADE', ondelete='CASCADE')
    )
    host_id = Column(
        Integer,
        ForeignKey('host.id', onupdate='CASCADE', ondelete='CASCADE')
    )
    config_step = Column(String(80), default='')
    package_config = Column(JSONEncoded, default={})
    config_validated = Column(Boolean, default=False)
    deployed_package_config = Column(JSONEncoded, default={})

    __table_args__ = (
        UniqueConstraint('cluster_id', 'host_id', name='constraint'),
    )

    state = relationship(
        ClusterHostState,
        uselist=False,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('host')
    )

    def __init__(self, cluster_id, host_id, **kwargs):
        self.cluster_id = cluster_id
        self.host_id = host_id
        self.state = ClusterHostState()
        super(ClusterHost, self).__init__(**kwargs)

    @property
    def name(self):
        return '%s.%s' % (self.host.name, self.cluster.name)

    @property
    def patched_package_config(self):
        return self.package_config

    @patched_package_config.setter
    def patched_package_config(self, value):
        self.package_config = util.merge_dict(dict(self.package_config), value)

    @property
    def put_package_config(self):
        return self.package_config

    @put_package_config.setter
    def put_package_config(self, value):
        package_config = dict(self.package_config)
        package_config.update(value)
        self.package_config = package_config

    @hybrid_property
    def distributed_system_name(self):
        cluster = self.cluster
        if cluster:
            return cluster.distributed_system_name
        else:
            return None

    @hybrid_property
    def os_name(self):
        host = self.host
        if host:
            return host.os_name
        else:
            return None

    @hybrid_property
    def clustername(self):
        cluster = self.cluster
        if cluster:
            return cluster.name
        else:
            return None

    @hybrid_property
    def hostname(self):
        host = self.host
        if host:
            return host.name
        else:
            return None

    @property
    def distributed_system_installed(self):
        state = self.state
        if state:
            return state.state == 'SUCCESSFUL'
        else:
            return False

    @property
    def os_installed(self):
        host = self.host
        if host:
            return host.os_installed
        else:
            return None

    @property
    def owner(self):
        cluster = self.cluster
        if cluster:
            return cluster.owner
        else:
            return None

    def state_dict(self):
        state = self.state
        if state.progress <= 0.0:
            host = self.host
            if host:
                dict_info = host.state_dict()
            else:
                dict_info = {}
            cluster = self.cluster
            if cluster and cluster.distributed_system:
                dict_info['state'] = state.state
        else:
            dict_info = state.to_dict()
        return dict_info

    def to_dict(self):
        dict_info = self.host.to_dict()
        dict_info.update(super(ClusterHost, self).to_dict())
        dict_info.update({
            'distributed_system_name': self.distributed_system_name,
            'distributed_system_installed': self.distributed_system_installed,
            'reinstall_distributed_system': (
                self.cluster.reinstall_distributed_system
            ),
            'owner': self.owner,
            'name': self.name
        })
        return dict_info


class HostState(BASE, StateMixin):
    """Host state table."""
    __tablename__ = 'host_state'

    id = Column(
        Integer,
        ForeignKey('host.id', onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True
    )

    def initialize(self):
        if self.state == 'INSTALLING':
            self.host.reinstall_os = False
        super(HostState, self).initialize()


class Host(BASE, TimestampMixin, HelperMixin):
    """Host table."""
    __tablename__ = 'host'

    name = Column(String(80), unique=True)
    adapter_id = Column(Integer, ForeignKey('os_adapter.id'))
    config_step = Column(String(80), default='')
    os_config = Column(JSONEncoded, default={})
    config_validated = Column(Boolean, default=False)
    deployed_os_config = Column(JSONEncoded, default={})
    os_id = Column(
        Integer,
        ForeignKey('os.id')
    )
    creator_id = Column(Integer, ForeignKey('user.id'))
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

    @hybrid_property
    def mac(self):
        machine = self.machine
        if machine:
            return machine.mac
        else:
            return None

    @property
    def patched_os_config(self):
        return self.os_config

    @patched_os_config.setter
    def patched_os_config(self, value):
        self.os_config = util.merge_dict(dict(self.os_config), value)

    @property
    def put_os_config(self):
        return self.os_config

    @put_os_config.setter
    def put_os_config(self, value):
        os_config = dict(self.os_config)
        os_config.update(value)
        self.os_config = os_config

    def __init__(self, id, **kwargs):
        self.id = id
        super(Host, self).__init__(**kwargs)

    def initialize(self):
        if not self.name:
            self.name = str(self.id)
        if not self.state or self.reinstall_os:
            self.state = HostState()
        super(Host, self).initialize()

    def validate(self):
        adapter = self.adapter
        if not adapter:
            raise exception.InvalidParameter(
                'adapter is not set in host %s' % self.id
            )
        if not self.os:
            if adapter:
                self.os = adapter.adapter_os
            else:
                raise exception.InvalidParameter(
                    'os is not set in host %s' % self.id
                )
        if not self.creator:
            raise exception.InvalidParameter(
                'creator is not set in host %s' % self.id
            )
        super(Host, self).validate()

    @hybrid_property
    def os_name(self):
        os = self.os
        if os:
            return os.name
        else:
            return None

    @hybrid_property
    def owner(self):
        creator = self.creator
        if creator:
            return creator.email
        else:
            return None

    @property
    def os_installed(self):
        state = self.state
        if state:
            return state.state == 'SUCCESSFUL'
        else:
            return False

    def state_dict(self):
        state = self.state
        if state:
            return state.to_dict()
        else:
            return {}

    def to_dict(self):
        dict_info = self.machine.to_dict()
        dict_info.update(super(Host, self).to_dict())
        dict_info.update({
            'os_name': self.os_name,
            'owner': self.owner,
            'os_installed': self.os_installed,
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

    def initialize(self):
        cluster = self.cluster
        if self.state == 'INSTALLING':
            cluster.reinstall_distributed_system = False
        clusterhosts = cluster.clusterhosts
        total_clusterhosts = 0
        failed_clusterhosts = 0
        installing_clusterhosts = 0
        finished_clusterhosts = 0
        progress = 0
        if not cluster.distributed_system:
            for clusterhost in clusterhosts:
                host = clusterhost.host
                host_state = host.state.state
                total_clusterhosts += 1
                progress += host.state.progress
                if host_state == 'SUCCESSFUL':
                    finished_clusterhosts += 1
                elif host_state == 'INSTALLING':
                    installing_clusterhosts += 1
                elif host_state == 'ERROR':
                    failed_clusterhosts += 1
        else:
            for clusterhost in clusterhosts:
                clusterhost_state = clusterhost.state.state
                total_clusterhosts += 1
                progress += clusterhost.state.progress
                if clusterhost_state == 'SUCCESSFUL':
                    finished_clusterhosts += 1
                elif clusterhost_state == 'INSTALLING':
                    installing_clusterhosts += 1
                elif clusterhost_state == 'ERROR':
                    failed_clusterhosts += 1
        self.progress = progress / total_clusterhosts
        self.message = (
            'toal %s, installing %s, finished %s, error $s'
        ) % (
            total_clusterhosts, installing_clusterhosts,
            finished_clusterhosts, failed_clusterhosts
        )
        if failed_clusterhosts:
            self.severity = 'ERROR'
        super(ClusterState, self).initialize()


class Cluster(BASE, TimestampMixin, HelperMixin):
    """Cluster table."""
    __tablename__ = 'cluster'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True)
    reinstall_distributed_system = Column(Boolean, default=True)
    config_step = Column(String(80), default='')
    os_id = Column(Integer, ForeignKey('os.id'), nullable=True)
    distributed_system_id = Column(
        Integer, ForeignKey('distributed_system.id'),
        nullable=True
    )
    os_config = Column(JSONEncoded, default={})
    package_config = Column(JSONEncoded, default={})
    config_validated = Column(Boolean, default=False)
    adapter_id = Column(Integer, ForeignKey('adapter.id'))
    creator_id = Column(Integer, ForeignKey('user.id'))
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
        super(Cluster, self).__init__(**kwargs)

    def initialize(self):
        if not self.state or self.reinstall_distributed_system:
            self.state = ClusterState()
        super(Cluster, self).initialize()

    def validate(self):
        adapter = self.adapter
        if not adapter:
            raise exception.InvalidParameter(
                'adapter is not set in cluster %s' % self.id
            )
        creator = self.creator
        if not creator:
            raise exception.InvalidParameter(
                'creator is not set in cluster %s' % self.id
            )
        os = self.os
        if not os:
            os_adapter = adapter.os_adapter
            if os_adapter:
                self.os = os_adapter.adapter_os
            else:
                self.os = None
        if not self.distributed_system:
            package_adapter = adapter.package_adapter
            if package_adapter:
                self.distributed_system = (
                    package_adapter.adapter_distributed_system
                )
            else:
                self.distributed_system = None
        super(Cluster, self).validate()

    @property
    def patched_os_config(self):
        return self.os_config

    @patched_os_config.setter
    def patched_os_config(self, value):
        self.os_config = util.merge_dict(dict(self.os_config), value)

    @property
    def put_os_config(self):
        return self.os_config

    @put_os_config.setter
    def put_os_config(self, value):
        os_config = dict(self.os_config)
        os_config.update(value)
        self.os_config = os_config

    @property
    def patched_package_config(self):
        return self.package_config

    @patched_package_config.setter
    def patched_package_config(self, value):
        self.package_config = util.merge_dict(dict(self.package_config), value)

    @property
    def put_package_config(self):
        return self.package_config

    @put_package_config.setter
    def put_package_config(self, value):
        package_config = dict(self.package_config)
        package_config.update(value)
        self.package_config = package_config

    @hybrid_property
    def owner(self):
        creator = self.creator
        if creator:
            return creator.email
        else:
            return None

    @hybrid_property
    def os_name(self):
        os = self.os
        if os:
            return os.name
        else:
            return None

    @hybrid_property
    def distributed_system_name(self):
        distributed_system = self.distributed_system
        if distributed_system:
            return distributed_system.name
        else:
            return None

    @property
    def distributed_system_installed(self):
        state = self.state
        if state:
            return self.state.state == 'SUCCESSFUL'
        else:
            return False

    def state_dict(self):
        state = self.state
        if state:
            return self.state.to_dict()
        else:
            return {}

    def to_dict(self):
        dict_info = super(Cluster, self).to_dict()
        dict_info.update({
            'os_name': self.os_name,
            'distributed_system_name': self.distributed_system_name,
            'distributed_system_installed': self.distributed_system_installed,
            'owner': self.owner,
        })
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
    name = Column(String(80), unique=True)
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


class UserToken(BASE, HelperMixin):
    """user token table."""
    __tablename__ = 'user_token'

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey('user.id', onupdate='CASCADE', ondelete='CASCADE')
    )
    token = Column(String(256), unique=True)
    expire_timestamp = Column(
        DateTime, default=lambda: datetime.datetime.now()
    )

    def __init__(self, token, **kwargs):
        self.token = token
        super(UserToken, self).__init__(**kwargs)

    def validate(self):
        if not self.user:
            raise exception.InvalidParameter(
                'user is not set in token: %s' % self.token
            )
        super(UserToken, self).validate()


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
        if not self.user:
            raise exception.InvalidParameter(
                'user is not set in user log: %s' % self.id
            )
        super(UserLog, self).validate()


class User(BASE, HelperMixin, TimestampMixin):
    """User table."""
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    email = Column(String(80), unique=True)
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

    def validate(self):
        if not self.crypted_password:
            raise exception.InvalidParameter(
                'password is not set in user : %s' % self.email
            )
        super(User, self).validate()

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

    def __str__(self):
        return '%s[email:%s,is_admin:%s,active:%s]' % (
            self.__class__.__name__,
            self.email, self.is_admin, self.active
        )


class SwitchMachine(BASE, HelperMixin, TimestampMixin):
    """Switch Machine table."""
    __tablename__ = 'switch_machine'
    id = Column(
        Integer, primary_key=True
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

    def validate(self):
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

    @hybrid_property
    def switch_vendor(self):
        return self.switch.vendor

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

    def to_dict(self):
        dict_info = self.machine.to_dict()
        dict_info.update(super(SwitchMachine, self).to_dict())
        return dict_info


class Machine(BASE, HelperMixin, TimestampMixin):
    """Machine table."""
    __tablename__ = 'machine'
    id = Column(Integer, primary_key=True)
    mac = Column(String(24), unique=True)
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

    def validate(self):
        try:
            netaddr.EUI(self.mac)
        except Exception:
            raise exception.InvalidParameter(
                'mac address %s format uncorrect' % self.mac
            )
        super(Machine, self).validate()

    @property
    def patched_ipmi_credentials(self):
        return self.ipmi_credentials

    @patched_ipmi_credentials.setter
    def patched_ipmi_credentials(self, value):
        self.ipmi_credentials = (
            util.merge_dict(dict(self.ipmi_credentials), value)
        )

    @property
    def patched_tag(self):
        return self.tag

    @patched_tag.setter
    def patched_tag(self, value):
        tag = dict(self.tag)
        tag.update(value)
        self.tag = value

    @property
    def patched_location(self):
        return self.location

    @patched_location.setter
    def patched_location(self, value):
        location = dict(self.location)
        location.update(value)
        self.location = location


class Switch(BASE, HelperMixin, TimestampMixin):
    """Switch table."""
    __tablename__ = 'switch'
    id = Column(Integer, primary_key=True)
    ip_int = Column('ip', BigInteger, unique=True)
    credentials = Column(JSONEncoded, default={})
    vendor = Column(String(256), nullable=True)
    state = Column(Enum('initialized', 'unreachable', 'notsupported',
                        'repolling', 'error', 'under_monitoring',
                        name='switch_state'),
                   default='initialized')
    filters = Column(JSONEncoded, default=[])
    switch_machines = relationship(
        SwitchMachine,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('switch')
    )

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
        self.credentials = util.merge_dict(dict(self.credentials), value)

    @property
    def patched_filters(self):
        return self.filters

    @patched_filters.setter
    def patched_filters(self, value):
        if not value:
            return
        filters = list(self.filters)
        for item in value:
            found_filter = False
            for switch_filter in filters:
                if switch_filter['filter_name'] == item['filter_name']:
                    switch_filter.update(item)
                    found_filter = True
                    break
            if not found_filter:
                filters.append(item)
        self.filters = filters

    def to_dict(self):
        dict_info = super(Switch, self).to_dict()
        dict_info['ip'] = self.ip
        return dict_info


class Adapter(BASE, HelperMixin):
    """Adpater table."""
    __tablename__ = 'adapter'

    id = Column(Integer, primary_key=True)
    package_adapter_id = Column(
        Integer,
        ForeignKey(
            'package_adapter.id', onupdate='CASCADE', ondelete='CASCADE'
        ),
        nullable=True
    )
    os_adapter_id = Column(
        Integer,
        ForeignKey(
            'os_adapter.id', onupdate='CASCADE', ondelete='CASCADE'
        ),
        nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            'package_adapter_id', 'os_adapter_id', name='constraint'
        ),
    )

    clusters = relationship(
        Cluster,
        backref=backref('adapter')
    )

    def __init__(self, os_adapter_id, package_adapter_id, **kwargs):
        self.os_adapter_id = os_adapter_id
        self.package_adapter_id = package_adapter_id
        super(Adapter, self).__init__(**kwargs)

    def metadata_dict(self):
        dict_info = {}
        if self.os_adapter:
            dict_info['os_config'] = self.os_adapter.metadata_dict()
        if self.package_adapter:
            dict_info['package_config'] = self.package_adapter.metadata_dict()
        return dict_info

    def to_dict(self):
        dict_info = super(Adapter, self).to_dict()
        os_adapter = self.os_adapter
        if os_adapter:
            dict_info['os_adapter'] = os_adapter.to_dict()
        package_adapter = self.package_adapter
        if package_adapter:
            dict_info['package_adapter'] = package_adapter.to_dict()
        return dict_info


class OSConfigMetadata(BASE, MetadataMixin):
    """OS config metadata."""
    __tablename__ = "os_config_metadata"

    id = Column(Integer, primary_key=True)
    adapter_id = Column(
        Integer,
        ForeignKey(
            'os_adapter.id', onupdate='CASCADE', ondelete='CASCADE'
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
        UniqueConstraint('path', 'adapter_id', name='constraint'),
    )

    def __init__(self, name, **kwargs):
        self.name = name
        super(OSConfigMetadata, self).__init__(**kwargs)


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


class OSAdapter(BASE, AdapterMixin):
    """OS adpater table."""
    __tablename__ = 'os_adapter'

    id = Column(Integer, primary_key=True)
    parent_id = Column(
        Integer,
        ForeignKey('os_adapter.id', onupdate='CASCADE', ondelete='CASCADE'),
        nullable=True
    )
    os_id = Column(
        Integer,
        ForeignKey('os.id', onupdate='CASCADE', ondelete='CASCADE'),
        nullable=True
    )
    installer_id = Column(
        Integer,
        ForeignKey('os_installer.id', onupdate='CASCADE', ondelete='CASCADE'),
        nullable=True
    )
    children = relationship(
        'OSAdapter',
        passive_deletes=True, passive_updates=True,
        backref=backref('parent', remote_side=id)
    )
    adapters = relationship(
        Adapter,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('os_adapter')
    )
    metadatas = relationship(
        OSConfigMetadata,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('adapter')
    )
    hosts = relationship(
        Host,
        backref=backref('adapter')
    )

    __table_args__ = (
        UniqueConstraint('os_id', 'installer_id', name='constraint'),
    )

    def __init__(self, name, **kwargs):
        self.name = name
        super(OSAdapter, self).__init__(**kwargs)

    @property
    def deployable(self):
        os = self.adapter_os
        installer = self.adapter_installer
        if (
            os and os.deployable and installer
        ):
            return True
        else:
            return False

    @property
    def adapter_os(self):
        os = self.os
        if os:
            return os
        parent = self.parent
        if parent:
            return parent.adapter_os
        else:
            return None

    @property
    def os_name(self):
        os = self.adapter_os
        if os:
            return os.name
        else:
            return ''

    def to_dict(self):
        dict_info = super(OSAdapter, self).to_dict()
        dict_info['os_name'] = self.os_name
        return dict_info


class OSInstaller(BASE, InstallerMixin):
    """OS installer table."""
    __tablename__ = 'os_installer'
    id = Column(Integer, primary_key=True)
    adpaters = relationship(
        OSAdapter,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('installer')
    )

    def __init__(self, name, **kwargs):
        self.name = name
        super(OSInstaller, self).__init__(**kwargs)


class OperatingSystem(BASE, HelperMixin):
    """OS table."""
    __tablename__ = 'os'

    id = Column(Integer, primary_key=True)
    parent_id = Column(
        Integer,
        ForeignKey('os.id', onupdate='CASCADE', ondelete='CASCADE'),
        nullable=True
    )
    name = Column(String(80), unique=True)
    deployable = Column(Boolean, default=False)
    adapters = relationship(
        OSAdapter,
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

    def __init__(self, name):
        self.name = name
        super(OperatingSystem, self).__init__()


class PackageAdapterRole(BASE, HelperMixin):
    """Adapter's roles."""

    __tablename__ = "package_adapter_role"
    id = Column(Integer, primary_key=True)
    name = Column(String(80))
    description = Column(Text)
    optional = Column(Boolean)
    adapter_id = Column(
        Integer,
        ForeignKey(
            'package_adapter.id',
            onupdate='CASCADE',
            ondelete='CASCADE'
        )
    )

    __table_args__ = (
        UniqueConstraint('name', 'adapter_id', name='constraint'),
    )

    def __init__(self, name, adapter_id, **kwargs):
        self.name = name
        self.adapter_id = adapter_id
        super(PackageAdapterRole, self).__init__(**kwargs)


class PackageConfigMetadata(BASE, MetadataMixin):
    """package config metadata."""
    __tablename__ = "package_config_metadata"

    id = Column(Integer, primary_key=True)
    adapter_id = Column(
        Integer,
        ForeignKey(
            'package_adapter.id',
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
        self, name, **kwargs
    ):
        self.name = name
        super(PackageConfigMetadata, self).__init__(**kwargs)


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


class PackageAdapter(BASE, AdapterMixin):
    """Adapter table."""
    __tablename__ = 'package_adapter'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True)
    parent_id = Column(
        Integer,
        ForeignKey(
            'package_adapter.id',
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
    installer_id = Column(
        Integer,
        ForeignKey(
            'package_installer.id',
            onupdate='CASCADE', ondelete='CASCADE'
        ),
        nullable=True
    )
    supported_os_patterns = Column(JSONEncoded, nullable=True)

    roles = relationship(
        PackageAdapterRole,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('adapter')
    )
    children = relationship(
        'PackageAdapter',
        passive_deletes=True, passive_updates=True,
        backref=backref('parent', remote_side=id)
    )
    adapters = relationship(
        Adapter,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('package_adapter')
    )
    metadatas = relationship(
        PackageConfigMetadata,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('adapter')
    )
    __table_args__ = (
        UniqueConstraint(
            'distributed_system_id',
            'installer_id', name='constraint'
        ),
    )

    def __init__(
        self, name, **kwargs
    ):
        self.name = name
        super(PackageAdapter, self).__init__(**kwargs)

    @property
    def deployable(self):
        distributed_system = self.adapter_distributed_system
        installer = self.adapter_installer
        if (
            distributed_system and distributed_system.deployable and
            installer
        ):
            return True
        else:
            return False

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
    def distributed_system_name(self):
        distributed_system = self.adapter_distributed_system
        if distributed_system:
            return distributed_system.name
        else:
            return ''

    @property
    def adapter_supported_os_patterns(self):
        supported_os_patterns = self.supported_os_patterns
        if supported_os_patterns:
            return supported_os_patterns
        parent = self.parent
        if parent:
            return parent.adapter_supported_os_patterns
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

    def to_dict(self):
        dict_info = super(PackageAdapter, self).to_dict()
        roles = []
        for role in self.adapter_roles:
            roles.append(role.to_dict())
        dict_info['roles'] = roles
        dict_info['supported_os_patterns'] = self.adapter_supported_os_patterns
        dict_info['distributed_system'] = self.distributed_system_name
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
    name = Column(String(80), unique=True)
    deployable = Column(Boolean, default=False)
    adapters = relationship(
        PackageAdapter,
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


class PackageInstaller(BASE, InstallerMixin):
    """package installer table."""
    __tablename__ = 'package_installer'
    id = Column(Integer, primary_key=True)
    adapters = relationship(
        PackageAdapter,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('installer')
    )

    def __init__(self, name, **kwargs):
        self.name = name
        super(PackageInstaller, self).__init__(**kwargs)


class Network(BASE, TimestampMixin, HelperMixin):
    """network table."""
    __tablename__ = 'network'

    id = Column(Integer, primary_key=True)
    subnet = Column(String(80), unique=True)

    host_networks = relationship(
        HostNetwork,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('network')
    )

    def __init__(self, subnet, **kwargs):
        self.subnet = subnet
        super(Network, self).__init__(**kwargs)

    def intialize(self):
        try:
            netaddr.IPNetwork(self.subnet)
        except Exception:
            raise exception.InvalidParameter(
                'subnet %s format is uncorrect' % self.subnet
            )
        super(Network, self).intialize()
