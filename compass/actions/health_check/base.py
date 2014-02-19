"""Base class for Compass Health Check"""
from compass.actions.health_check import utils as health_check_utils
from compass.utils import setting_wrapper as setting


class BaseCheck(object):
    """health check base class."""

    def __init__(self):
        self.config = setting
        self.code = 1
        self.messages = []
        self.dist, self.version, self.release = health_check_utils.get_dist()

    def _set_status(self, code, message):
        """set status"""
        self.code = code
        self.messages.append(message)

    def get_status(self):
        """get status"""
        return (self.code, self.messages)
