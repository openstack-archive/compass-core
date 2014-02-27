"""Provider interface to manipulate database."""
import logging
from threading import local

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from compass.utils import setting_wrapper as setting
from compass.db import model


ENGINE = create_engine(setting.SQLALCHEMY_DATABASE_URI, convert_unicode=True)
SESSION = sessionmaker(autocommit=False, autoflush=False)
SESSION.configure(bind=ENGINE)
SCOPED_SESSION = scoped_session(SESSION)
SESSION_HOLDER = local()

model.BASE.query = SCOPED_SESSION.query_property()


def init(database_url):
    """Initialize database.

    :param database_url: string, database url.
    """
    global ENGINE
    global SCOPED_SESSION
    ENGINE = create_engine(database_url, convert_unicode=True)
    SESSION.configure(bind=ENGINE)
    SCOPED_SESSION = scoped_session(SESSION)
    model.BASE.query = SCOPED_SESSION.query_property()


def in_session():
    """check if in database session scope."""
    if hasattr(SESSION_HOLDER, 'session'):
        return True
    else:
        return False


@contextmanager
def session():
    """
    database session scope. To operate database, it should be called in
    database session.
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


def create_db():
    """Create database"""
    model.BASE.metadata.create_all(bind=ENGINE)


def drop_db():
    """Drop database."""
    model.BASE.metadata.drop_all(bind=ENGINE)


def create_table(table):
    """Create table.

    :param table: Class of the Table defined in the model.
    """
    table.__table__.create(bind=ENGINE, checkfirst=True)


def drop_table(table):
    """Drop table.

    :param table: Class of the Table defined in the model.
    """
    table.__table__.drop(bind=ENGINE, checkfirst=True)
