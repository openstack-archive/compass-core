"""Custom exception"""


class RecordNotExists(Exception):
    """Define the exception for referring non-existing object in DB."""
    def __init__(self, message):
        super(RecordNotExists, self).__init__(message)
        self.message = message


class DuplicatedRecord(Exception):
    """Define the exception for trying to insert an existing object in DB."""
    def __init__(self, message):
        super(DuplicatedRecord, self).__init__(message)
        self.message = message


class Forbidden(Exception):
    """Define the exception that a user is trying to make some action
       without the right permission.
    """
    def __init__(self, message):
        super(Forbidden, self).__init__(message)
        self.message = message


class InvalidParameter(Exception):
    """Define the exception that the request has invalid or missing parameters.
    """
    def __init__(self, message):
        super(InvalidParameter, self).__init__(message)
        self.message = message
