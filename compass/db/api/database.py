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
import functools
import logging
import netaddr

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.pool import QueuePool
from sqlalchemy.pool import SingletonThreadPool
from sqlalchemy.pool import StaticPool
from threading import local

from compass.db import exception
from compass.db import models
from compass.utils import logsetting
from compass.utils import setting_wrapper as setting


ENGINE = None
SESSION = sessionmaker(autocommit=False, autoflush=False)
SCOPED_SESSION = None
SESSION_HOLDER = local()

POOL_MAPPING = {
    'instant': NullPool,
    'static': StaticPool,
    'queued': QueuePool,
    'thread_single': SingletonThreadPool
}


def init(database_url=None):
    """Initialize database.

    Adjust sqlalchemy logging if necessary.

    :param database_url: string, database url.
    """
    global ENGINE
    global SCOPED_SESSION
    if not database_url:
        database_url = setting.SQLALCHEMY_DATABASE_URI
    logging.info('init database %s', database_url)
    root_logger = logging.getLogger()
    fine_debug = root_logger.isEnabledFor(logsetting.LOGLEVEL_MAPPING['fine'])
    if fine_debug:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    finest_debug = root_logger.isEnabledFor(
        logsetting.LOGLEVEL_MAPPING['finest']
    )
    if finest_debug:
        logging.getLogger('sqlalchemy.dialects').setLevel(logging.INFO)
        logging.getLogger('sqlalchemy.pool').setLevel(logging.INFO)
        logging.getLogger('sqlalchemy.orm').setLevel(logging.INFO)
    poolclass = POOL_MAPPING[setting.SQLALCHEMY_DATABASE_POOL_TYPE]
    ENGINE = create_engine(
        database_url, convert_unicode=True,
        poolclass=poolclass
    )
    SESSION.configure(bind=ENGINE)
    SCOPED_SESSION = scoped_session(SESSION)
    models.BASE.query = SCOPED_SESSION.query_property()


def in_session():
    """check if in database session scope."""
    bool(hasattr(SESSION_HOLDER, 'session'))


@contextmanager
def session(exception_when_in_session=True):
    """database session scope.

    To operate database, it should be called in database session.
    If not exception_when_in_session, the with session statement support
    nested session and only the out most session commit/rollback the
    transaction.
    """
    if not ENGINE:
        init()

    nested_session = False
    if hasattr(SESSION_HOLDER, 'session'):
        if exception_when_in_session:
            logging.error('we are already in session')
            raise exception.DatabaseException('session already exist')
        else:
            new_session = SESSION_HOLDER.session
            nested_session = True
            logging.log(
                logsetting.getLevelByName('fine'),
                'reuse session %s', nested_session
            )
    else:
        new_session = SCOPED_SESSION()
        setattr(SESSION_HOLDER, 'session', new_session)
        logging.log(
            logsetting.getLevelByName('fine'),
            'enter session %s', new_session
        )
    try:
        yield new_session
        if not nested_session:
            new_session.commit()
    except Exception as error:
        if not nested_session:
            new_session.rollback()
            logging.error('failed to commit session')
        logging.exception(error)
        if isinstance(error, IntegrityError):
            for item in error.statement.split():
                if item.islower():
                    object = item
                    break
            raise exception.DuplicatedRecord(
                '%s in %s' % (error.orig, object)
            )
        elif isinstance(error, OperationalError):
            raise exception.DatabaseException(
                'operation error in database'
            )
        elif isinstance(error, exception.DatabaseException):
            raise error
        else:
            raise exception.DatabaseException(str(error))
    finally:
        if not nested_session:
            new_session.close()
            SCOPED_SESSION.remove()
            delattr(SESSION_HOLDER, 'session')
        logging.log(
            logsetting.getLevelByName('fine'),
            'exit session %s', new_session
        )


def current_session():
    """Get the current session scope when it is called.

       :return: database session.
       :raises: DatabaseException when it is not in session.
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


def run_in_session(exception_when_in_session=True):
    """Decorator to make sure the decorated function run in session.

    When not exception_when_in_session, the run_in_session can be
    decorated several times.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                my_session = kwargs.get('session')
                if my_session is not None:
                    return func(*args, **kwargs)
                else:
                    with session(
                        exception_when_in_session=exception_when_in_session
                    ) as my_session:
                        kwargs['session'] = my_session
                        return func(*args, **kwargs)
            except Exception as error:
                logging.error(
                    'got exception with func %s args %s kwargs %s',
                    func, args, kwargs
                )
                logging.exception(error)
                raise error
        return wrapper
    return decorator


def _setup_user_table(user_session):
    """Initialize user table with default user."""
    logging.info('setup user table')
    from compass.db.api import user
    user.add_user(
        session=user_session,
        email=setting.COMPASS_ADMIN_EMAIL,
        password=setting.COMPASS_ADMIN_PASSWORD,
        is_admin=True
    )


def _setup_permission_table(permission_session):
    """Initialize permission table."""
    logging.info('setup permission table.')
    from compass.db.api import permission
    permission.add_permissions_internal(
        session=permission_session
    )


def _setup_switch_table(switch_session):
    """Initialize switch table."""
    # TODO(xicheng): deprecate setup default switch.
    logging.info('setup switch table')
    from compass.db.api import switch
    switch.add_switch(
        True, setting.DEFAULT_SWITCH_IP,
        session=switch_session,
        machine_filters=['allow ports all']
    )


def _update_others(other_session):
    """Update other tables."""
    logging.info('update other tables')
    from compass.db.api import utils
    from compass.db import models
    utils.update_db_objects(
        other_session, models.Cluster
    )
    utils.update_db_objects(
        other_session, models.Host
    )
    utils.update_db_objects(
        other_session, models.ClusterHost
    )


@run_in_session()
def create_db(session=None):
    """Create database."""
    models.BASE.metadata.create_all(bind=ENGINE)
    _setup_permission_table(session)
    _setup_user_table(session)
    _setup_switch_table(session)
    _update_others(session)


def drop_db():
    """Drop database."""
    models.BASE.metadata.drop_all(bind=ENGINE)
