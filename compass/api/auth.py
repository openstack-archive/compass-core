from itsdangerous import BadData
import logging

from compass.db.model import User
from compass.db.model import login_serializer


def get_user_info_from_token(token, max_age):
    """Return user's ID and hased password from token"""

    user_id = None
    password = None
    try:
        user_id, password = login_serializer.loads(token, max_age=max_age)

    except BadData as err:
        logging.error("[auth][get_user_info_from_token] Exception: %s", err)
        return None

    return user_id, password


def authenticate_user(user_id=None, email=None, pwd=None, pwd_hashed=True):
    """Authenticate a use by validing ID or email and password"""

    fliter_clause = ""
    if user_id:
        fliter_clause = "id=%s" % user_id
    elif email:
        fliter_clause = "email='%s'" % email
    else:
        raise Exception("No user's ID or email provided!")

    if not pwd:
        raise Exception("No password!")

    try:
        user = User.query.filter(fliter_clause).first()
        if user and user.valid_password(pwd, is_hashed=pwd_hashed):
            return user
    except Exception as err:
        print '[auth][authenticate_user]Exception: %s' % err
        logging.info('[auth][authenticate_user]Exception: %s', err)

    return None

