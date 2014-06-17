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

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from threading import local

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
    if hasattr(SESSION_HOLDER, 'session'):
        logging.error('we are already in session')
        raise Exception('session already exist')
    else:
        new_session = SCOPED_SESSION()
        SESSION_HOLDER.session = new_session

    try:
        yield new_session
        new_session.commit()
    except Exception as error:
        new_session.rollback()
        logging.error('failed to commit session')
        logging.exception(error)
        raise error
    finally:
        new_session.close()
        SCOPED_SESSION.remove()
        del SESSION_HOLDER.session


def current_session():
    """Get the current session scope when it is called.

       :return: database session.
    """
    try:
        return SESSION_HOLDER.session
    except Exception as error:
        logging.error('It is not in the session scope')
        logging.exception(error)
        raise error


def _setup_user_table(user_session):
    """Initialize default user."""
    from compass.db.api import user
    user.add_user_internal(
        user_session,
        email=setting.COMPASS_ADMIN_EMAIL,
        password=setting.COMPASS_ADMIN_PASSWORD,
        is_admin=True
    )
       

def _setup_permission_table(permission_session):
    """Initialize permission table."""
    from compass.db.api import permission
    permission.add_permissions_internal(
        permission_session
    )


def create_db():
    """Create database."""
    models.BASE.metadata.create_all(bind=ENGINE)
    with session() as my_session:
        _setup_permission_table(my_session)
        _setup_user_table(my_session)


def drop_db():
    """Drop database."""
    models.BASE.metadata.drop_all(bind=ENGINE)


def create_table(table):
    """Create table.

    :param table: Class of the Table defined in the model.
    """
    table.__table__.create(bind=ENGINE, checkfirst=True)
    if table == models.User:
        with session() as my_session:
            _setup_user_table(my_session)    

    if table == models.Permission:
        with session as my_session:
             _setup_permission_table(my_session)


def drop_table(table):
    """Drop table.

    :param table: Class of the Table defined in the model.
    """
    table.__table__.drop(bind=ENGINE, checkfirst=True)
