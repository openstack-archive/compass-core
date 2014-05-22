class ItemNotFound(Exception):
    """Define the exception for referring non-existing object."""
    def __init__(self, message):
        super(ItemNotFound, self).__init__(message)
        self.message = message

    def __str__(self):
        return repr(self.message)


class BadRequest(Exception):
    """Define the exception for invalid/missing parameters or a user makes
       a request in invalid state and cannot be processed at this moment.
    """
    def __init__(self, message):
        super(BadRequest, self).__init__(message)
        self.message = message

    def __str__(self):
        return repr(self.message)


class Unauthorized(Exception):
    """Define the exception for invalid user login."""
    def __init__(self, message):
        super(Unauthorized, self).__init__(message)
        self.message = message

    def __str__(self):
        return repr(self.message)


class UserDisabled(Exception):
    """Define the exception that a disabled user tries to do some operations.
    """
    def __init__(self, message):
        super(UserDisabled, self).__init__(message)
        self.message = message

    def __str__(self):
        return repr(self.message)


class Forbidden(Exception):
    """Define the exception that a user tries to do some operations without
       valid permissions.
    """
    def __init__(self, message):
        super(Forbidden, self).__init__(message)
        self.message = message

    def __str__(self):
        return repr(self.message)


class BadMethod(Exception):
    """Define the exception for invoking unsupprted or unimplemented methods.
    """
    def __init__(self, message):
        super(BadMethod, self).__init__(message)
        self.message = message

    def __str__(self):
        return repr(self.message)


class ConflictObject(Exception):
    """Define the exception for creating an existing object."""
    def __init__(self, message):
        super(ConflictObject, self).__init__(message)
        self.message = message

    def __str__(self):
        return repr(self.message)
