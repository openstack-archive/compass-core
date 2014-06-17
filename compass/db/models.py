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
from datetime import datetime
import simplejson as json

from sqlalchemy import Table
from sqlalchemy import Column, Integer, String
from sqlalchemy import Enum, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import TypeDecorator


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
    created_at = Column(DateTime, default=lambda: datetime.now())
    updated_at = Column(DateTime, default=lambda: datetime.now(),
                        onupdate=lambda: datetime.now())


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
            if isinstance(value, datetime):
                value = str(value)

            dict_info[key] = value

        return dict_info


# User, Permission relation table
user_permission = Table('user_permission', BASE.metadata,
                        Column('user_id', Integer, ForeignKey('user.id')),
                        Column('permission_id', Integer,
                               ForeignKey('permission.id')))


class User(BASE, HelperMixin, TimestampMixin):
    """User table."""
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    email = Column(String(80), unique=True)
    password = Column(String(225))
    firstname = Column(String(80))
    lastname = Column(String(80))
    is_admin = Column(Boolean, default=False)
    active = Column(Boolean, default=True)
    permissions = relationship("Permission", secondary=user_permission)

    def __init__(self, email, password, **kwargs):
        self.email = email
        self.set_password(password)
        super(User, self).__init__(**kwargs)

    def set_password(self, password):
        self.password = util.encrypt(password)

    def get_masked_password(self):
        return '**********'

    def get_permissions(self):
        permissions = []
        for permission in self.permissions:
            permissions.append(permission)

        return permissions

    def set_permissions(self, permissions):
        self.permissions = permissions

    def check_permission(self, permission_name):
        for permission in self.permissions:
            if permission.name == permission_name:
                return True

        return False

    def to_dict(self):
        dict_info = super(User, self).to_dict()
        dict_info['permissions'] = [
            permission.to_dict() for permission in self.get_permissions()
        ]
        return dict_info

    def __str__(self):
        return '%s[email:%s,is_admin:%s,active:%s]' % (
            self.__class__.__name__,
            self.email, self.is_admin, self.active
        )


class Permission(Base, HelperMixin, TimestampMixin):
    """Permission table."""
    __tablename__ = 'permission'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), unique=True)
    alias = Column(String(100))
    description = Column(Text)

    def __init__(self, name, alias, description):
        self.name = name
        self.alias = alias
        self.description
        super(Permission, self___init__()


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
