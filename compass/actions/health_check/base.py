import compass.utils.setting_wrapper as setting
import utils as health_check_utils

class BaseCheck:

    def __init__(self):
        self.config=setting
        self.code = 1
        self.messages = []
        self.dist, self.version, self.release = health_check_utils.check_dist()

    def set_status(self, code, message):
        self.code = code
        self.messages.append(message)

    def get_status(self):
        return (self.code, self.messages)

