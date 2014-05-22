from functools import wraps


def wrap_to_dict(support_keys=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            obj = func(*args, **kwargs)
            obj_info = None
            if isinstance(obj, list):
                obj_info = [_wrapper_dict(o, support_keys) for o in obj]
            else:
                obj_info = _wrapper_dict(obj, support_keys)

            return obj_info
        return wrapper
    return decorator


def _wrapper_dict(data, support_keys=None):
    """Helper for warpping db object into dictionary"""
    if support_keys is None:
        return data

    info = {}
    for key in support_keys:
        if key in data:
            info[key] = data[key]

    return info
