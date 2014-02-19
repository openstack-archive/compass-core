"""hdsdiscovery module errors"""


class TimeoutError(Exception):
    """Timeout error."""

    def __init__(self, message):
        super(TimeoutError, self).__init__(message)
        self.message = message

    def __str__(self):
        return repr(self.message)
