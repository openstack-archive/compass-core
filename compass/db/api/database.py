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

"""Provider interface to manipulate database."""
import logging
import netaddr

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from threading import local

from compass.db import exception
from compass.db import models
from compass.utils import setting_wrapper as setting


ENGINE = None
SESSION = sessionmaker(autocommit=False, autoflush=False)
SCOPED_SESSION = None
SESSION_HOLDER = local()

def init(database_url):
    """Initialize database.

    :param database_url: string, database url.
    """
    global ENGINE
    global SCOPED_SESSION
    ENGINE = create_engine(database_url, convert_unicode=True)
    SESSION.configure(bind=ENGINE)
    SCOPED_SESSION = scoped_session(SESSION)
    models.BASE.query = SCOPED_SESSION.query_property()


init(setting.SQLALCHEMY_DATABASE_URI)


def in_session():
    """check if in database session scope."""
    if hasattr(SESSION_HOLDER, 'session'):
        return True
    else:
        return False


@contextmanager
def session():
    """database session scope.

       .. note::
       To operate database, it should be called in database session.
    """
    import traceback
    if hasattr(SESSION_HOLDER, 'session'):
        logging.error('we are already in session')
        raise exception.DatabaseException('session already exist')
    else:
        new_session = SCOPED_SESSION()
        setattr(SESSION_HOLDER, 'session', new_session)

    try:
        yield new_session
        new_session.commit()
    except Exception as error:
        new_session.rollback()
        logging.error('failed to commit session')
        logging.exception(error)
        if isinstance(error, exception.DatabaseException):
            raise error
        else:
            raise exception.DatabaseException(str(error))
    finally:
        new_session.close()
        SCOPED_SESSION.remove()
        delattr(SESSION_HOLDER, 'session')


def current_session():
    """Get the current session scope when it is called.

       :return: database session.
    """
    try:
        return SESSION_HOLDER.session
    except Exception as error:
        logging.error('It is not in the session scope')
        logging.exception(error)
        if isinstance(error, exception.DatabaseException):
            raise error
        else:
            raise exception.DatabaseException(str(error))


def _setup_user_table(user_session):
    """Initialize default user."""
    logging.info('setup user table')
    from compass.db.api import user
    user.add_user_internal(
        user_session,
        setting.COMPASS_ADMIN_EMAIL,
        setting.COMPASS_ADMIN_PASSWORD,
        is_admin=True
    )
       

def _setup_permission_table(permission_session):
    """Initialize permission table."""
    logging.info('setup permission table.')
    from compass.db.api import permission
    permission.add_permissions_internal(
        permission_session
    )


def _setup_switch_table(switch_session):
    """Initialize switch table."""
    logging.info('setup switch table')
    from compass.db.api import switch
    switch.add_switch_internal(
        switch_session, long(netaddr.IPAddress(setting.DEFAULT_SWITCH_IP))
    )


def _setup_os_installers(installer_session):
    """Initialize os_installer table."""
    logging.info('setup os installer table')
    from compass.db.api import installer
    installer.add_os_installers_internal(
        installer_session
    ) 


def _setup_package_installers(installer_session):
    """Initialize package_installer table."""
    logging.info('setup package installer table')
    from compass.db.api import installer
    installer.add_package_installers_internal(
        installer_session
    )


def _setup_oses(os_session):
    """Initialize os table."""
    logging.info('setup os table')
    from compass.db.api import adapter
    adapter.add_oses_internal(
        os_session
    )


def _setup_distributed_systems(distributed_system_session):
    """Initialize distributed system table."""
    logging.info('setup distributed system table')
    from compass.db.api import adapter
    adapter.add_distributed_systems_internal(
        distributed_system_session
    )


def _setup_os_adapters(adapter_session):
    """Initialize os adapter table."""
    logging.info('setup os adapter table')
    from compass.db.api import adapter
    adapter.add_os_adapters_internal(
        adapter_session)


def _setup_package_adapters(adapter_session):
    """Initialize package adapter table."""
    logging.info('setup package adapter table')
    from compass.db.api import adapter
    adapter.add_package_adapters_internal(
        adapter_session)


def _setup_adapters(adapter_session):
    """Initialize adapter table."""
    logging.info('setup adapter table')
    from compass.db.api import adapter
    adapter.add_adapters_internal(adapter_session)


def _setup_os_fields(field_session):
    """Initialize os field table."""
    logging.info('setup os field table')
    from compass.db.api import metadata
    metadata.add_os_field_internal(field_session)


def _setup_package_fields(field_session):
    """Initialize package field table."""
    logging.info('setup package field table')
    from compass.db.api import metadata
    metadata.add_package_field_internal(field_session)


def _setup_os_metadatas(metadata_session):
    """Initialize os metadata table."""
    logging.info('setup os metadata table')
    from compass.db.api import metadata
    metadata.add_os_metadata_internal(metadata_session)


def _setup_package_metadatas(metadata_session):
    """Initialize package metadata table."""
    logging.info('setup package metadata table')
    from compass.db.api import metadata
    metadata.add_package_metadata_internal(metadata_session)

def _setup_package_adapter_roles(role_session):
    """Initialize package adapter role table."""
    logging.info('setup package adapter role table')
    from compass.db.api import adapter
    adapter.add_roles_internal(role_session)


def create_db():
    """Create database."""
    models.BASE.metadata.create_all(bind=ENGINE)
    with session() as my_session:
        _setup_permission_table(my_session)
        _setup_user_table(my_session)
        _setup_switch_table(my_session)
        _setup_os_installers(my_session)
        _setup_package_installers(my_session)
        _setup_oses(my_session)
        _setup_distributed_systems(my_session)
        _setup_os_adapters(my_session)
        _setup_package_adapters(my_session)
        _setup_package_adapter_roles(my_session)
        _setup_adapters(my_session)
        _setup_os_fields(my_session)
        _setup_package_fields(my_session)
        _setup_os_metadatas(my_session)
        _setup_package_metadatas(my_session)


def drop_db():
    """Drop database."""
    models.BASE.metadata.drop_all(bind=ENGINE)


def create_table(table):
    """Create table.

    :param table: Class of the Table defined in the model.
    """
    table.__table__.create(bind=ENGINE, checkfirst=True)
    with session() as my_session:
        if table == models.User:
            _setup_user_table(my_session)    
        elif table == models.Permission:
            _setup_permission_table(my_session)
        elif table == models.Switch:
            _setup_switch_table(my_session)
        elif table in [
            models.OSInstaller,
            models.PackageInstaller,
            models.OperatingSystem,
            models.DistributedSystems,
            models.OSAdapter,
            models.PackageAdapter,
            models.Adapter
        ]:
            _setup_os_installers(my_session)
            _setup_package_installers(my_session)
            _setup_os_adapters(my_session)
            _setup_package_adapters(my_session)
            _setup_package_adapter_roles(my_session)
            _setup_adapters(my_session)
            _setup_os_fields(my_session)
            _setup_os_metadata(my_session)
            _setup_package_fields(my_session)
            _setup_package_metadata(my_session)
        elif table == models.PackageAdapterRole:
            _setup_package_adapter_roles(my_session)
        elif table in [
            models.OSConfigField,
            models.PackageConfigField,
            models.OSConfigMetadata,
            models.PackageConfigMetadata
        ]:
            _setup_os_fields(my_session)
            _setup_os_metadata(my_session)
            _setup_package_fields(my_session)
            _setup_package_metadata(my_session)


def drop_table(table):
    """Drop table.

    :param table: Class of the Table defined in the model.
    """
    table.__table__.drop(bind=ENGINE, checkfirst=True)
