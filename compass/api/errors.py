"""Exception and its handler"""
from compass.api import app
from compass.api import util


class ObjectDoesNotExist(Exception):
    """Define the exception for referring non-existing object"""
    def __init__(self, message):
        super(ObjectDoesNotExist, self).__init__(message)
        self.message = message

    def __str__(self):
        return repr(self.message)


class UserInvalidUsage(Exception):
    """Define the exception for fault usage of users"""
    def __init__(self, message):
        super(UserInvalidUsage, self).__init__(message)
        self.message = message

    def __str__(self):
        return repr(self.message)


class ObjectDuplicateError(Exception):
    """Define the duplicated object exception"""
    def __init__(self, message):
        super(ObjectDuplicateError, self).__init__(message)
        self.message = message

    def __str__(self):
        return repr(self.message)


class InputMissingError(Exception):
    """Define the insufficient input exception"""
    def __init__(self, message):
        super(InputMissingError, self).__init__(message)
        self.message = message

    def __str__(self):
        return repr(self.message)


class MethodNotAllowed(Exception):
    """Define the exception which invalid method is called"""
    def __init__(self, message):
        super(MethodNotAllowed, self).__init__(message)
        self.message = message

    def __str__(self):
        return repr(self.message)


@app.errorhandler(ObjectDoesNotExist)
def handle_not_exist(error, failed_objs=None):
    """Handler of ObjectDoesNotExist Exception"""

    message = {'status': 'Not Found',
               'message': error.message}

    if failed_objs and isinstance(failed_objs, dict):
        message.update(failed_objs)

    return util.make_json_response(404, message)


@app.errorhandler(UserInvalidUsage)
def handle_invalid_usage(error):
    """Handler of UserInvalidUsage Exception"""

    message = {'status': 'Invalid parameters',
               'message': error.message}

    return util.make_json_response(400, message)


@app.errorhandler(InputMissingError)
def handle_mssing_input(error):
    """Handler of InputMissingError Exception"""

    message = {'status': 'Insufficient data',
               'message': error.message}

    return util.make_json_response(400, message)


@app.errorhandler(ObjectDuplicateError)
def handle_duplicate_object(error, failed_objs=None):
    """Handler of ObjectDuplicateError Exception"""

    message = {'status': 'Conflict Error',
               'message': error.message}

    if failed_objs and isinstance(failed_objs, dict):
        message.update(failed_objs)

    return util.make_json_response(409, message)


@app.errorhandler(MethodNotAllowed)
def handle_not_allowed_method(error):
    """Handler of MethodNotAllowed Exception"""

    message = {"status": "Method Not Allowed",
               "message": "The method is not allowed to use"}
    return util.make_json_response(405, message)
