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

from sqlalchemy import Table
from sqlalchemy import Column, Integer, BigInteger, String
from sqlalchemy import Enum, DateTime, ForeignKey, Text, Boolean
from sqlalchemy import UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import TypeDecorator

from compass.utils import util


BASE = declarative_base()


class JSONEncodedDict(TypeDecorator):
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


class MutationDict(Mutable, dict):
    @classmethod
    def coerce(cls, key, value):
        """Convert plain dictionaries to MutationDict."""

        if not isinstance(value, MutationDict):
            if isinstance(value, dict):
                return MutationDict(value)

            # this call will raise ValueError
            return Mutable.coerce(key, value)
        else:
            return value

    def __setitem__(self, key, value):
        """Detect dictionary set events and emit change events."""

        dict.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        """Detect dictionary del events and emit change events."""

        dict.__delitem__(self, key)
        self.changed()


class TimestampMixin(object):
    created_at = Column(DateTime, default=lambda: datetime.datetime.now())
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(),
                        onupdate=lambda: datetime.datetime.now())


class MetadataMixin(object):
    name = Column(String(80), unique=True)
    description = Column(String(200))


class MetadataFieldMixin(object):
    field = Column(String(80), unique=True)
    ftype = Column(Enum('str', 'int', 'float', 'list', 'dict', 'bool'))
    validator = Column(String(80))
    is_required = Column(Boolean, default=True)
    description = Column(String(200))


class HelperMixin(object):
    def to_dict(self):
        keys = self.__mapper__.columns.keys()
        dict_info = {}
        for key in keys:
            value = getattr(self, key)
            if isinstance(value, datetime.datetime):
                value = util.format_datetime(value)

            dict_info[key] = value

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
        ForeignKey('permission.id', onupdate='CASCADE', ondelete='CASCADE'),
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

    def __init__(self, email, **kwargs):
        self.email = email
        super(User, self).__init__(**kwargs)

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
    switch_id = Column(
        Integer,
        ForeignKey('switch.id', onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True)
    machine_id = Column(
        Integer,
        ForeignKey('machine.id', onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True
    )
    port = Column(String(80))
    vlans_data = Column('vlans', Text)

    def __init__(self, switch_id, machine_id, **kwargs):
        self.switch_id = switch_id
        self.machine_id = machine_id
        super(SwitchMachine, self).__init__(**kwargs)

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

    def _get_vlans(self):
        if self.vlans_data:
            return json.loads(self.vlans_data)
        else:
            return []

    def _set_vlans(self, value):
        if value is not None:
            self.vlans_data = json.dumps(value)
        else:
            self.vlans_data = None

    @property
    def vlans(self):
        return self._get_vlans()

    @vlans.setter
    def vlans(self, value):
        return self._set_vlans(value)

    @property
    def patched_vlan(self):
        return None

    @patched_vlan.setter
    def patched_vlan(self, value):
        vlans = self._get_vlans()
        if value not in vlans:
            vlans.append(value)
        self._set_vlans(vlans)         

    def to_dict(self):
        dict_info = self.machine.to_dict()
        dict_info.update(super(SwitchMachine, self).to_dict())
        dict_info['vlans'] = self.vlans
        return dict_info


class Machine(BASE, HelperMixin, TimestampMixin):
    """Machine table."""
    __tablename__ = 'machine'
    id = Column(Integer, primary_key=True)
    mac = Column(String(24), unique=True)
    ipmi_credentials_data = Column('ipmi_credentials', Text)
    tag = Column(Text)
    switch_machines = relationship(
        SwitchMachine,
        passive_deletes=True, passive_updates=True,
        cascade='all, delete-orphan',
        backref=backref('machine')
    )

    def __init__(self, mac, **kwargs):
        self.mac = mac
        super(Machine, self).__init__(**kwargs)

    def _get_ipmi_credentials(self):
        if self.ipmi_credentials_data:
            return json.loads(self.ipmi_credentials_data)
        else:
            return {}

    def _set_ipmi_credentials(self, value):
        if value is not None:
            self.ipmi_credentials_data = json.dumps(value)
        else:
            self.ipmi_credentials_data = None

    @property
    def ipmi_credentials(self):
        return self._get_ipmi_credentials()

    @ipmi_credentials.setter
    def ipmi_credentials(self, value):
        self._set_ipmi_credentials(value)

    @property
    def patched_ipmi_credentials(self):
        return self._get_ipmi_credentials()

    @patched_ipmi_credentials.setter
    def patched_ipmi_credentials(self, value):
        ipmi_credentials = self._get_ipmi_credentials()
        util.merge_dict(ipmi_credentials, value)
        self._set_ipmi_credentials(ipmi_credentials)


    def to_dict(self):
        dict_info = super(Machine, self).to_dict()
        dict_info['ipmi_credentials'] = self.ipmi_credentials
        return dict_info


class Switch(BASE, HelperMixin, TimestampMixin):
    """Switch table."""
    __tablename__ = 'switch'
    id = Column(Integer, primary_key=True)
    ip_int = Column('ip', BigInteger, unique=True)
    credentials_data = Column('credentials', Text)
    vendor = Column(String(256), nullable=True)
    state = Column(Enum('initialized', 'unreachable', 'notsupported',
                        'repolling', 'error', 'under_monitoring',
                        name='switch_state'),
                   default='initialized')
    filters_data = Column('filters', Text)
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

    def _get_credentials(self):
        if self.credentials_data:
            return json.loads(self.credentials_data)
        else:
            return {}

    def _set_credentials(self, value):
        if value is not None:
            self.credentials_data = json.dumps(value)
        else:
            self.credentials_data = None

    @property
    def credentials(self):
        return self._get_credentials()

    @credentials.setter
    def credentials(self, value):
        self._set_credentials(value)

    @property
    def patched_credentials(self):
        return None

    @patched_credentials.setter
    def patched_credentials(self, value):
        credentials = self._get_credentials()
        util.merge_dict(credentials, value)
        self._set_credentials(credentials)

    def _get_filters(self):
        if self.filters_data:
            return json.loads(self.filters_data)
        else:
            return []

    def _set_filters(self, value):
        if value is not None:
            self.filters_data = json.dumps(value)
        else:
            self.filters_data = None

    @property
    def filters(self):
        return self._get_filters()

    @filters.setter
    def filters(self, value):
        self._set_filters(value)

    @property
    def patched_filter(self):
        return None

    @patched_filter.setter
    def patched_filter(self, value):
        filters = self._get_filters()
        found_filter = False
        for switch_filter in filters:
            if switch_filter['filter_name'] == value['filter_name']:
                switch_filter.update(value)
        if not found_filter:
            filters.append(value)
        self._set_filters(filters)

    def to_dict(self):
        dict_info = super(Switch, self).to_dict()
        dict_info['ip'] = self.ip
        dict_info['credentials'] = self.credentials
        dict_info['filters'] = self.filters
        dict_info['machines'] = [
            switch_machine.machine.to_dict()
            for switch_machine in self.switch_machines
        ]
        return dict_info


adapter_os = Table('adapter_os', BASE.metadata,
                   Column('adapter_id', Integer, ForeignKey('adapter.id')),
                   Column('os_id', Integer, ForeignKey('os.id')))


class OperatingSystem(BASE):
    """OS table."""
    __tablename__ = 'os'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True)


class Adapter(BASE, HelperMixin):
    """Adapter table."""
    __tablename__ = "adapter"

    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True)

    roles = relationship("AdapterRole")
    support_os = relationship("OperatingSystem", secondary=adapter_os)
    # package_config = xxxx

    def to_dict(self):
        oses = []
        for os in self.support_os:
            oses.append({"name": os.name, "os_id": os.id})

        extra_dict = {
            "compatible_os": oses
        }
        dict_info = self.__dict__.copy()
        del dict_info['support_os']

        return self._to_dict(dict_info, extra_dict)


class AdapterRole(BASE):
    """Adapter's roles."""

    __tablename__ = "adapter_role"
    id = Column(Integer, primary_key=True)
    name = Column(String(80))
    adapter_id = Column(Integer, ForeignKey('adapter.id'))


package_config_metatdata_field = \
    Table('package_config_metadata_field',
          BASE.metadata,
          Column('package_config_metadata_id',
                 Integer,
                 ForeignKey('package_config_metadata.id')),
          Column('package_config_field_id',
                 Integer,
                 ForeignKey('package_config_field.id')))


class PackageConfigMetadata(BASE, MetadataMixin):
    """Adapter config metadata."""

    __tablename__ = "package_config_metadata"

    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey(id))
    adapter_id = Column(Integer, ForeignKey('adapter.id'))
    children = relationship("PackageConfigMetadata",
                            backref=backref('parent', remote_side=id))
    fields = relationship("PackageConfigField",
                          secondary=package_config_metatdata_field)

    def __init__(self, name, adapter_id, parent=None):
        self.name = name
        self.adapter_id = adapter_id
        self.parent = parent


class PackageConfigField(BASE, MetadataFieldMixin):
    """Adapter cofig metadata fields."""

    __tablename__ = "package_config_field"
    id = Column(Integer, primary_key=True)


os_config_metadata_field = Table('os_config_metadata_field', BASE.metadata,
                                 Column('os_config_metadata_id',
                                        Integer,
                                        ForeignKey('os_config_metadata.id')),
                                 Column('os_config_field_id',
                                        Integer,
                                        ForeignKey('os_config_field.id')))


class OSConfigMetadata(BASE, MetadataMixin):
    """OS config metadata."""

    __tablename__ = "os_config_metadata"

    id = Column(Integer, primary_key=True)
    os_id = Column(Integer, ForeignKey('os.id'))
    parent_id = Column(Integer, ForeignKey(id))
    children = relationship("OSConfigMetadata",
                            backref=backref("parent", remote_side=id))
    fields = relationship('OSConfigField',
                          secondary=os_config_metadata_field)

    def __init__(self, name, os_id, parent=None):
        self.name = name
        self.os_id = os_id
        self.parent = parent


class OSConfigField(BASE, MetadataFieldMixin, HelperMixin):
    """OS config metadata fields."""

    __tablename__ = 'os_config_field'
    id = Column(Integer, primary_key=True)


class Cluster(BASE, TimestampMixin, HelperMixin):
    """Cluster table."""

    __tablename__ = "cluster"

    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True)
    editable = Column(Boolean, default=True)
    os_global_config = Column(MutationDict.as_mutable(JSONEncodedDict),
                              default={})
    package_global_config = Column(MutationDict.as_mutable(JSONEncodedDict),
                                   default={})
    adapter_id = Column(Integer, ForeignKey('adapter.id'))
    os_id = Column(Integer, ForeignKey('os.id'))
    created_by = Column(Integer, ForeignKey('user.id'))

    owner = relationship('User')
    # hosts = relationship('Host', secondary=cluster_host)

    def __init__(self, name, adapter_id, os_id, created_by):
        self.name = name
        self.adapter_id = adapter_id
        self.os_id = os_id
        self.created_by = created_by

    @property
    def config(self):
        config = {}
        config.update(self.os_global_config)
        config.update(self.package_global_config)

        return config

    def to_dict(self):
        extra_info = {
            'created_by': self.owner.email,
            'hosts': []
        }
        dict_info = self.__dict__.copy()
        del dict_info['owner']

        return self._to_dict(dict_info, extra_info)
