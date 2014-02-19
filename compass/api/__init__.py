__all__ = ['Flask', 'SQLAlchemy', 'compass_api']

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.debug = True

from compass.api import api as compass_api
