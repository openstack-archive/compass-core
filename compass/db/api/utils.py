# Copyright 2014 Huawei Technologies Co. Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utils for database usage."""

import functools
import inspect
import logging
import netaddr
import re

from inspect import isfunction
from sqlalchemy import and_
from sqlalchemy import or_

from compass.db import exception
from compass.db import models
from compass.utils import util


def model_query(session, model):
    """model query.

    Return sqlalchemy query object.
    """
    if not issubclass(model, models.BASE):
        raise exception.DatabaseException("model should be sublass of BASE!")

    return session.query(model)


def _default_list_condition_func(col_attr, value, condition_func):
    """The default condition func for a list of data.

    Given the condition func for single item of data, this function
    wrap the condition_func and return another condition func using
    or_ to merge the conditions of each single item to deal with a
    list of data item.

    Args:
       col_attr: the colomn name
       value: the column value need to be compared.
       condition_func: the sqlalchemy condition object like ==

    Examples:
       col_attr is name, value is ['a', 'b', 'c'] and
       condition_func is ==, the returned condition is
       name == 'a' or name == 'b' or name == 'c'
    """
    conditions = []
    for sub_value in value:
        condition = condition_func(col_attr, sub_value)
        if condition is not None:
            conditions.append(condition)
    if conditions:
        return or_(*conditions)
    else:
        return None


def _one_item_list_condition_func(col_attr, value, condition_func):
    """The wrapper condition func to deal with one item data list.

    For simplification, it is used to reduce generating too complex
    sql conditions.
    """
    if value:
        return condition_func(col_attr, value[0])
    else:
        return None


def _model_condition_func(
    col_attr, value,
    item_condition_func,
    list_condition_func=_default_list_condition_func
):
    """Return sql condition based on value type."""
    if isinstance(value, list):
        if not value:
            return None
        if len(value) == 1:
            return item_condition_func(col_attr, value)
        return list_condition_func(
            col_attr, value, item_condition_func
        )
    else:
        return item_condition_func(col_attr, value)


def _between_condition(col_attr, value):
    """Return sql range condition."""
    if value[0] is not None and value[1] is not None:
        return col_attr.between(value[0], value[1])
    if value[0] is not None:
        return col_attr >= value[0]
    if value[1] is not None:
        return col_attr <= value[1]
    return None


def model_order_by(query, model, order_by):
    """append order by into sql query model."""
    if not order_by:
        return query
    order_by_cols = []
    for key in order_by:
        if isinstance(key, tuple):
            key, is_desc = key
        else:
            is_desc = False
        if isinstance(key, basestring):
            if hasattr(model, key):
                col_attr = getattr(model, key)
            else:
                continue
        else:
            col_attr = key
        if is_desc:
            order_by_cols.append(col_attr.desc())
        else:
            order_by_cols.append(col_attr)
    return query.order_by(*order_by_cols)


def _model_condition(col_attr, value):
    """Generate condition for one column.

    Example for col_attr is name:
        value is 'a': name == 'a'
        value is ['a']: name == 'a'
        value is ['a', 'b']: name == 'a' or name == 'b'
        value is {'eq': 'a'}: name == 'a'
        value is {'lt': 'a'}: name < 'a'
        value is {'le': 'a'}: name <= 'a'
        value is {'gt': 'a'}: name > 'a'
        value is {'ge': 'a'}: name >= 'a'
        value is {'ne': 'a'}: name != 'a'
        value is {'in': ['a', 'b']}: name in ['a', 'b']
        value is {'notin': ['a', 'b']}: name not in ['a', 'b']
        value is {'startswith': 'abc'}: name like 'abc%'
        value is {'endswith': 'abc'}: name like '%abc'
        value is {'like': 'abc'}: name like '%abc%'
        value is {'between': ('a', 'c')}: name >= 'a' and name <= 'c'
        value is [{'lt': 'a'}]: name < 'a'
        value is [{'lt': 'a'}, {'gt': c'}]: name < 'a' or name > 'c'
        value is {'lt': 'c', 'gt': 'a'}: name > 'a' and name < 'c'

    If value is a list, the condition is the or relationship among
    conditions of each item.
    If value is dict and there are multi keys in the dict, the relationship
    is and conditions of each key.
    Otherwise the condition is to compare the column with the value.
    """
    if isinstance(value, list):
        basetype_values = []
        composite_values = []
        for item in value:
            if isinstance(item, (list, dict)):
                composite_values.append(item)
            else:
                basetype_values.append(item)
        conditions = []
        if basetype_values:
            if len(basetype_values) == 1:
                condition = (col_attr == basetype_values[0])
            else:
                condition = col_attr.in_(basetype_values)
            conditions.append(condition)
        for composite_value in composite_values:
            condition = _model_condition(col_attr, composite_value)
            if condition is not None:
                conditions.append(condition)
        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return or_(*conditions)
    elif isinstance(value, dict):
        conditions = []
        if 'eq' in value:
            conditions.append(_model_condition_func(
                col_attr, value['eq'],
                lambda attr, data: attr == data,
                lambda attr, data, item_condition_func: attr.in_(data)
            ))
        if 'lt' in value:
            conditions.append(_model_condition_func(
                col_attr, value['lt'],
                lambda attr, data: attr < data,
                _one_item_list_condition_func
            ))
        if 'gt' in value:
            conditions.append(_model_condition_func(
                col_attr, value['gt'],
                lambda attr, data: attr > data,
                _one_item_list_condition_func
            ))
        if 'le' in value:
            conditions.append(_model_condition_func(
                col_attr, value['le'],
                lambda attr, data: attr <= data,
                _one_item_list_condition_func
            ))
        if 'ge' in value:
            conditions.append(_model_condition_func(
                col_attr, value['ge'],
                lambda attr, data: attr >= data,
                _one_item_list_condition_func
            ))
        if 'ne' in value:
            conditions.append(_model_condition_func(
                col_attr, value['ne'],
                lambda attr, data: attr != data,
                lambda attr, data, item_condition_func: attr.notin_(data)
            ))
        if 'in' in value:
            conditions.append(col_attr.in_(value['in']))
        if 'notin' in value:
            conditions.append(col_attr.notin_(value['notin']))
        if 'startswith' in value:
            conditions.append(_model_condition_func(
                col_attr, value['startswith'],
                lambda attr, data: attr.like('%s%%' % data)
            ))
        if 'endswith' in value:
            conditions.append(_model_condition_func(
                col_attr, value['endswith'],
                lambda attr, data: attr.like('%%%s' % data)
            ))
        if 'like' in value:
            conditions.append(_model_condition_func(
                col_attr, value['like'],
                lambda attr, data: attr.like('%%%s%%' % data)
            ))
        if 'between' in value:
            conditions.append(_model_condition_func(
                col_attr, value['between'],
                _between_condition
            ))
        conditions = [
            condition
            for condition in conditions
            if condition is not None
        ]
        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return and_(conditions)
    else:
        condition = (col_attr == value)
        return condition


def model_filter(query, model, **filters):
    """Append conditons to query for each possible column."""
    for key, value in filters.items():
        if isinstance(key, basestring):
            if hasattr(model, key):
                col_attr = getattr(model, key)
            else:
                continue
        else:
            col_attr = key
        condition = _model_condition(col_attr, value)
        if condition is not None:
            query = query.filter(condition)
    return query


def replace_output(**output_mapping):
    """Decorator to recursively relace output by output mapping.

    The replacement detail is described in _replace_output.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return _replace_output(
                func(*args, **kwargs), **output_mapping
            )
        return wrapper
    return decorator


def _replace_output(data, **output_mapping):
    """Helper to replace output data.

    Example:
       data = {'a': 'hello'}
       output_mapping = {'a': 'b'}
       returns: {'b': 'hello'}

       data = {'a': {'b': 'hello'}}
       output_mapping =  {'a': 'b'}
       returns: {'b': {'b': 'hello'}}

       data = {'a': {'b': 'hello'}}
       output_mapping =  {'a': {'b': 'c'}}
       returns: {'a': {'c': 'hello'}}

       data = [{'a': 'hello'}, {'a': 'hi'}]
       output_mapping = {'a': 'b'}
       returns: [{'b': 'hello'}, {'b': 'hi'}]
    """
    if isinstance(data, list):
        return [
            _replace_output(item, **output_mapping)
            for item in data
        ]
    if not isinstance(data, dict):
        raise exception.InvalidResponse(
            '%s type is not dict' % data
        )
    info = {}
    for key, value in data.items():
        if key in output_mapping:
            output_key = output_mapping[key]
            if isinstance(output_key, basestring):
                info[output_key] = value
            else:
                info[key] = (
                    _replace_output(value, **output_key)
                )
        else:
            info[key] = value
    return info


def get_wrapped_func(func):
    """Get wrapped function instance.

    Example:
       @dec1
       @dec2
       myfunc(*args, **kwargs)

       get_wrapped_func(myfunc) returns function object with
       following attributes:
          __name__: 'myfunc'
          args: args
          kwargs: kwargs
       otherwise myfunc is function  object with following attributes:
          __name__: partial object ...
          args: ...
          kwargs: ...
    """
    if func.func_closure:
        for closure in func.func_closure:
            if isfunction(closure.cell_contents):
                return get_wrapped_func(closure.cell_contents)
        return func
    else:
        return func


def wrap_to_dict(support_keys=[], **filters):
    """Decrator to convert returned object to dict.

    The details is decribed in _wrapper_dict.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return _wrapper_dict(
                func(*args, **kwargs), support_keys, **filters
            )
        return wrapper
    return decorator


def _wrapper_dict(data, support_keys, **filters):
    """Helper for warpping db object into dictionary.

    If data is list, convert it to a list of dict
    If data is Base model, convert it to dict
    for the data as a dict, filter it with the supported keys.
    For each filter_key, filter_value  in filters, also filter
    data[filter_key] by filter_value recursively if it exists.

    Example:
       data is models.Switch, it will be converted to
       {
           'id': 1, 'ip': '10.0.0.1', 'ip_int': 123456,
           'credentials': {'version': 2, 'password': 'abc'}
       }
       Then if support_keys are ['id', 'ip', 'credentials'],
       it will be filtered to {
           'id': 1, 'ip': '10.0.0.1',
           'credentials': {'version': 2, 'password': 'abc'}
       }
       Then if filters is {'credentials': ['version']},
       it will be filtered to {
           'id': 1, 'ip': '10.0.0.1',
           'credentials': {'version': 2}
       }
    """
    logging.debug(
        'wrap dict %s by support_keys=%s filters=%s',
        data, support_keys, filters
    )
    if isinstance(data, list):
        return [
            _wrapper_dict(item, support_keys, **filters)
            for item in data
        ]
    if isinstance(data, models.HelperMixin):
        data = data.to_dict()
    if not isinstance(data, dict):
        raise exception.InvalidResponse(
            'response %s type is not dict' % data
        )
    info = {}
    try:
        for key in support_keys:
            if key in data and data[key] is not None:
                if key in filters:
                    filter_keys = filters[key]
                    if isinstance(filter_keys, dict):
                        info[key] = _wrapper_dict(
                            data[key], filter_keys.keys(),
                            **filter_keys
                        )
                    else:
                        info[key] = _wrapper_dict(
                            data[key], filter_keys
                        )
                else:
                    info[key] = data[key]
        return info
    except Exception as error:
        logging.exception(error)
        raise error


def replace_filters(**kwarg_mapping):
    """Decorator to replace kwargs.

    Examples:
       kwargs: {'a': 'b'}, kwarg_mapping: {'a': 'c'}
       replaced kwargs to decorated func:
          {'c': 'b'}

    replace_filters is used to replace caller's input
    to make it understandable by models.py.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            replaced_kwargs = {}
            for key, value in kwargs.items():
                if key in kwarg_mapping:
                    replaced_kwargs[kwarg_mapping[key]] = value
                else:
                    replaced_kwargs[key] = value
            return func(*args, **replaced_kwargs)
        return wrapper
    return decorator


def supported_filters(
    support_keys=[],
    optional_support_keys=[],
    ignore_support_keys=[],
):
    """Decorator to check kwargs keys.

    keys in kwargs and in ignore_support_keys will be removed.
    If any unsupported keys found, a InvalidParameter
    exception raises.

    Args:
       support_keys: keys that must exist.
       optional_support_keys: keys that may exist.
       ignore_support_keys: keys should be ignored.

    Assumption: args without default value is supposed to exist.
    You can add them in support_keys or not but we will make sure
    it appears when we call the decorated function.
    We do best match on both args and kwargs to make sure if the
    key appears or not.

    Examples:
        decorated func: func(a, b, c=3, d=4, **kwargs)

        support_keys=['e'] and call func(e=5):
           raises: InvalidParameter: missing declared arg
        support_keys=['e'] and call func(1,2,3,4,5,e=6):
           raises: InvalidParameter: caller sending more args
        support_keys=['e'] and call func(1,2):
           raises: InvalidParameter: supported keys ['e'] missing
        support_keys=['d', 'e'] and call func(1,2,e=3):
           raises: InvalidParameter: supported keys ['d'] missing
        support_keys=['d', 'e'] and call func(1,2,d=4, e=3):
           passed
        support_keys=['d'], optional_support_keys=['e']
        and call func(1,2, d=3):
           passed
        support_keys=['d'], optional_support_keys=['e']
        and call func(1,2, d=3, e=4, f=5):
           raises: InvalidParameter: unsupported keys ['f']
        support_keys=['d'], optional_support_keys=['e'],
        ignore_support_keys=['f']
        and call func(1,2, d=3, e=4, f=5):
           passed to decorated keys: func(1,2, d=3, e=4)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **filters):
            wrapped_func = get_wrapped_func(func)
            argspec = inspect.getargspec(wrapped_func)
            wrapped_args = argspec.args
            args_defaults = argspec.defaults
            # wrapped_must_args are positional args caller must pass in.
            if args_defaults:
                wrapped_must_args = wrapped_args[:-len(args_defaults)]
            else:
                wrapped_must_args = wrapped_args[:]
            # make sure any positional args without default value in
            # decorated function should appear in args or filters.
            if len(args) < len(wrapped_must_args):
                remain_args = wrapped_must_args[len(args):]
                for remain_arg in remain_args:
                    if remain_arg not in filters:
                        raise exception.InvalidParameter(
                            'function missing declared arg %s '
                            'while caller sends args %s' % (
                                remain_arg, args
                            )
                        )
            # make sure args should be no more than positional args
            # declared in decorated function.
            if len(args) > len(wrapped_args):
                raise exception.InvalidParameter(
                    'function definition args %s while the caller '
                    'sends args %s' % (
                        wrapped_args, args
                    )
                )
            # exist_args are positional args caller has given.
            exist_args = dict(zip(wrapped_args, args)).keys()
            must_support_keys = set(support_keys)
            all_support_keys = must_support_keys | set(optional_support_keys)
            wrapped_supported_keys = set(filters) | set(exist_args)
            unsupported_keys = (
                set(filters) - set(wrapped_args) -
                all_support_keys - set(ignore_support_keys)
            )
            # unsupported_keys are the keys that are not in support_keys,
            # optional_support_keys, ignore_support_keys and are not passed in
            # by positional args. It means the decorated function may
            # not understand these parameters.
            if unsupported_keys:
                raise exception.InvalidParameter(
                    'filter keys %s are not supported for %s' % (
                        list(unsupported_keys), wrapped_func
                    )
                )
            # missing_keys are the keys that must exist but missing in
            # both positional args or kwargs.
            missing_keys = must_support_keys - wrapped_supported_keys
            if missing_keys:
                raise exception.InvalidParameter(
                    'filter keys %s not found for %s' % (
                        list(missing_keys), wrapped_func
                    )
                )
            # We filter kwargs to eliminate ignore_support_keys in kwargs
            # passed to decorated function.
            filtered_filters = dict([
                (key, value)
                for key, value in filters.items()
                if key not in ignore_support_keys
            ])
            return func(*args, **filtered_filters)
        return wrapper
    return decorator


def input_filters(
    **filters
):
    """Decorator to filter kwargs.

    For key in kwargs, if the key exists and filters
    and the return of call filters[key] is False, the key
    will be removed from kwargs.

    The function definition of filters[key] is
    func(value, *args, **kwargs) compared with decorated
    function func(*args, **kwargs)

    The function is used to filter kwargs in case some
    kwargs should be removed conditionally depends on the
    related filters.

    Examples:
       filters={'a': func(value, *args, **kwargs)}
       @input_filters(**filters)
       decorated_func(*args, **kwargs)
       func returns False.
       Then when call decorated_func(a=1, b=2)
       it will be actually called the decorated func with
       b=2. a=1 will be removed since it does not pass filtering.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            filtered_kwargs = {}
            for key, value in kwargs.items():
                if key in filters:
                    if filters[key](value, *args, **kwargs):
                        filtered_kwargs[key] = value
                    else:
                        logging.debug(
                            'ignore filtered input key %s' % key
                        )
                else:
                    filtered_kwargs[key] = value
            return func(*args, **filtered_kwargs)
        return wrapper
    return decorator


def _obj_equal_or_subset(check, obj):
    """Used by output filter to check if obj is in check."""
    if check == obj:
        return True
    if not issubclass(obj.__class__, check.__class__):
        return False
    if isinstance(obj, dict):
        return _dict_equal_or_subset(check, obj)
    elif isinstance(obj, list):
        return _list_equal_or_subset(check, obj)
    else:
        return False


def _list_equal_or_subset(check_list, obj_list):
    """Used by output filter to check if obj_list is in check_list"""
    if not isinstance(check_list, list):
        return False
    return set(check_list).issubset(set(obj_list))


def _dict_equal_or_subset(check_dict, obj_dict):
    """Used by output filter to check if obj_dict in check_dict."""
    if not isinstance(check_dict, dict):
        return False
    for key, value in check_dict.items():
        if (
            key not in obj_dict or
            not _obj_equal_or_subset(check_dict[key], obj_dict[key])
        ):
            return False
    return True


def general_filter_callback(general_filter, obj):
    """General filter function to filter output.

    Since some fields stored in database is json encoded and
    we want to do the deep match for the json encoded field to
    do the filtering in some cases, we introduces the output_filters
    and general_filter_callback to deal with this kind of cases.

    We do special treatment for key 'resp_eq' to check if
    obj is the recursively subset of general_filter['resp_eq']


    Example:
       obj: 'b'
       general_filter: {}
       returns: True

       obj: 'b'
       general_filter: {'resp_in': ['a', 'b']}
       returns: True

       obj: 'b'
       general_filter: {'resp_in': ['a']}
       returns: False

       obj: 'b'
       general_filter: {'resp_eq': 'b'}
       returns: True

       obj: 'b'
       general_filter: {'resp_eq': 'a'}
       returns: False

       obj: 'b'
       general_filter: {'resp_range': ('a', 'c')}
       returns: True

       obj: 'd'
       general_filter: {'resp_range': ('a', 'c')}
       returns: False

    If there are multi keys in dict, the output is filtered
    by and relationship.

    If the general_filter is a list, the output is filtered
    by or relationship.

    Supported general filters: [
        'resp_eq', 'resp_in', 'resp_lt',
        'resp_le', 'resp_gt', 'resp_ge',
        'resp_match', 'resp_range'
    ]
    """
    if isinstance(general_filter, list):
        if not general_filter:
            return True
        return any([
            general_filter_callback(item, obj)
            for item in general_filter
        ])
    elif isinstance(general_filter, dict):
        if 'resp_eq' in general_filter:
            if not _obj_equal_or_subset(
                general_filter['resp_eq'], obj
            ):
                return False
        if 'resp_in' in general_filter:
            in_filters = general_filter['resp_in']
            if not any([
                _obj_equal_or_subset(in_filer, obj)
                for in_filer in in_filters
            ]):
                return False
        if 'resp_lt' in general_filter:
            if obj >= general_filter['resp_lt']:
                return False
        if 'resp_le' in general_filter:
            if obj > general_filter['resp_le']:
                return False
        if 'resp_gt' in general_filter:
            if obj <= general_filter['resp_gt']:
                return False
        if 'resp_ge' in general_filter:
            if obj < general_filter['resp_gt']:
                return False
        if 'resp_match' in general_filter:
            if not re.match(general_filter['resp_match'], obj):
                return False
        if 'resp_range' in general_filter:
            resp_range = general_filter['resp_range']
            if not isinstance(resp_range, list):
                resp_range = [resp_range]
            in_range = False
            for range_start, range_end in resp_range:
                if range_start <= obj <= range_end:
                    in_range = True
            if not in_range:
                return False
        return True
    else:
        return True


def filter_output(filter_callbacks, kwargs, obj, missing_ok=False):
    """Filter ouput.

    For each key in filter_callbacks, if it exists in kwargs,
    kwargs[key] tells what we need to filter. If the call of
    filter_callbacks[key] returns False, it tells the obj should be
    filtered out of output.
    """
    for callback_key, callback_value in filter_callbacks.items():
        if callback_key not in kwargs:
            continue
        if callback_key not in obj:
            if missing_ok:
                continue
            else:
                raise exception.InvalidResponse(
                    '%s is not in %s' % (callback_key, obj)
                )
        if not callback_value(
            kwargs[callback_key], obj[callback_key]
        ):
            return False
    return True


def output_filters(missing_ok=False, **filter_callbacks):
    """Decorator to filter output list.

    Each filter_callback should have the definition like:
       func({'resp_eq': 'a'}, 'a')
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            filtered_obj_list = []
            obj_list = func(*args, **kwargs)
            for obj in obj_list:
                if filter_output(
                    filter_callbacks, kwargs, obj, missing_ok
                ):
                    filtered_obj_list.append(obj)
            return filtered_obj_list
        return wrapper
    return decorator


def _input_validates(args_validators, kwargs_validators, *args, **kwargs):
    """Used by input_validators to validate inputs."""
    for i, value in enumerate(args):
        if i < len(args_validators) and args_validators[i]:
            args_validators[i](value)
    for key, value in kwargs.items():
        if kwargs_validators.get(key):
            kwargs_validators[key](value)


def input_validates(*args_validators, **kwargs_validators):
    """Decorator to validate input.

    Each validator should have definition like:
       func('00:01:02:03:04:05')
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _input_validates(
                args_validators, kwargs_validators,
                *args, **kwargs
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator


def _input_validates_with_args(
    args_validators, kwargs_validators, *args, **kwargs
):
    """Validate input with validators.

    Each validator takes the arguments of the decorated function
    as its arguments. The function definition is like:
       func(value, *args, **kwargs) compared with the decorated
       function func(*args, **kwargs).
    """
    for i, value in enumerate(args):
        if i < len(args_validators) and args_validators[i]:
            args_validators[i](value, *args, **kwargs)
    for key, value in kwargs.items():
        if kwargs_validators.get(key):
            kwargs_validators[key](value, *args, **kwargs)


def input_validates_with_args(
    *args_validators, **kwargs_validators
):
    """Decorator to validate input."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _input_validates_with_args(
                args_validators, kwargs_validators,
                *args, **kwargs
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator


def _output_validates_with_args(
    kwargs_validators, obj, *args, **kwargs
):
    """Validate output with validators.

    Each validator takes the arguments of the decorated function
    as its arguments. The function definition is like:
       func(value, *args, **kwargs) compared with the decorated
       function func(*args, **kwargs).
    """
    if isinstance(obj, list):
        for item in obj:
            _output_validates_with_args(
                kwargs_validators, item, *args, **kwargs
            )
        return
    if isinstance(obj, models.HelperMixin):
        obj = obj.to_dict()
    if not isinstance(obj, dict):
        raise exception.InvalidResponse(
            'response %s type is not dict' % str(obj)
        )
    try:
        for key, value in obj.items():
            if key in kwargs_validators:
                kwargs_validators[key](value, *args, **kwargs)
    except Exception as error:
        logging.exception(error)
        raise error


def output_validates_with_args(**kwargs_validators):
    """Decorator to validate output.

    The validator can take the arguments of the decorated
    function as its arguments.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            obj = func(*args, **kwargs)
            if isinstance(obj, list):
                for obj_item in obj:
                    _output_validates_with_args(
                        kwargs_validators, obj_item,
                        *args, **kwargs
                    )
            else:
                _output_validates_with_args(
                    kwargs_validators, obj,
                    *args, **kwargs
                )
            return obj
        return wrapper
    return decorator


def _output_validates(kwargs_validators, obj):
    """Validate output.

    Each validator has following signature:
       func(value)
    """
    if isinstance(obj, list):
        for item in obj:
            _output_validates(kwargs_validators, item)
        return
    if isinstance(obj, models.HelperMixin):
        obj = obj.to_dict()
    if not isinstance(obj, dict):
        raise exception.InvalidResponse(
            'response %s type is not dict' % str(obj)
        )
    try:
        for key, value in obj.items():
            if key in kwargs_validators:
                kwargs_validators[key](value)
    except Exception as error:
        logging.exception(error)
        raise error


def output_validates(**kwargs_validators):
    """Decorator to validate output."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            obj = func(*args, **kwargs)
            if isinstance(obj, list):
                for obj_item in obj:
                    _output_validates(kwargs_validators, obj_item)
            else:
                _output_validates(kwargs_validators, obj)
            return obj
        return wrapper
    return decorator


def get_db_object(session, table, exception_when_missing=True, **kwargs):
    """Get db object.

    If not exception_when_missing and the db object can not be found,
    return None instead of raising exception.
    """
    if not session:
        raise exception.DatabaseException('session param is None')
    with session.begin(subtransactions=True):
        logging.debug(
            'session %s get db object %s from table %s',
            id(session), kwargs, table.__name__)
        db_object = model_filter(
            model_query(session, table), table, **kwargs
        ).first()
        logging.debug(
            'session %s got db object %s', id(session), db_object
        )
        if db_object:
            return db_object

        if not exception_when_missing:
            return None

        raise exception.RecordNotExists(
            'Cannot find the record in table %s: %s' % (
                table.__name__, kwargs
            )
        )


def add_db_object(session, table, exception_when_existing=True,
                  *args, **kwargs):
    """Create db object.

    If not exception_when_existing and the db object exists,
    Instead of raising exception, updating the existing db object.
    """
    if not session:
        raise exception.DatabaseException('session param is None')
    with session.begin(subtransactions=True):
        logging.debug(
            'session %s add object %s atributes %s to table %s',
            id(session), args, kwargs, table.__name__)
        argspec = inspect.getargspec(table.__init__)
        arg_names = argspec.args[1:]
        arg_defaults = argspec.defaults
        if not arg_defaults:
            arg_defaults = []
        if not (
            len(arg_names) - len(arg_defaults) <= len(args) <= len(arg_names)
        ):
            raise exception.InvalidParameter(
                'arg names %s does not match arg values %s' % (
                    arg_names, args)
            )
        db_keys = dict(zip(arg_names, args))
        if db_keys:
            db_object = session.query(table).filter_by(**db_keys).first()
        else:
            db_object = None

        new_object = False
        if db_object:
            logging.debug(
                'got db object %s: %s', db_keys, db_object
            )
            if exception_when_existing:
                raise exception.DuplicatedRecord(
                    '%s exists in table %s' % (db_keys, table.__name__)
                )
        else:
            db_object = table(**db_keys)
            new_object = True

        for key, value in kwargs.items():
            setattr(db_object, key, value)

        if new_object:
            session.add(db_object)
        session.flush()
        db_object.initialize()
        db_object.validate()
        logging.debug(
            'session %s db object %s added', id(session), db_object
        )
        return db_object


def list_db_objects(session, table, order_by=[], **filters):
    """List db objects.

    If order by given, the db objects should be sorted by the ordered keys.
    """
    if not session:
        raise exception.DatabaseException('session param is None')
    with session.begin(subtransactions=True):
        logging.debug(
            'session %s list db objects by filters %s in table %s',
            id(session), filters, table.__name__
        )
        db_objects = model_order_by(
            model_filter(
                model_query(session, table),
                table,
                **filters
            ),
            table,
            order_by
        ).all()
        logging.debug(
            'session %s got listed db objects: %s',
            id(session), db_objects
        )
        return db_objects


def del_db_objects(session, table, **filters):
    """delete db objects."""
    if not session:
        raise exception.DatabaseException('session param is None')
    with session.begin(subtransactions=True):
        logging.debug(
            'session %s delete db objects by filters %s in table %s',
            id(session), filters, table.__name__
        )
        query = model_filter(
            model_query(session, table), table, **filters
        )
        db_objects = query.all()
        query.delete(synchronize_session=False)
        logging.debug(
            'session %s db objects %s deleted', id(session), db_objects
        )
        return db_objects


def update_db_objects(session, table, updates={}, **filters):
    """Update db objects."""
    if not session:
        raise exception.DatabaseException('session param is None')
    with session.begin(subtransactions=True):
        logging.debug(
            'session %s update db objects by filters %s in table %s',
            id(session), filters, table.__name__)
        db_objects = model_filter(
            model_query(session, table), table, **filters
        ).all()
        for db_object in db_objects:
            logging.debug('update db object %s: %s', db_object, updates)
            update_db_object(session, db_object, **updates)
        logging.debug(
            'session %s db objects %s updated',
            id(session), db_objects
        )
        return db_objects


def update_db_object(session, db_object, **kwargs):
    """Update db object."""
    if not session:
        raise exception.DatabaseException('session param is None')
    with session.begin(subtransactions=True):
        logging.debug(
            'session %s update db object %s by value %s',
            id(session), db_object, kwargs
        )
        for key, value in kwargs.items():
            setattr(db_object, key, value)
        session.flush()
        db_object.update()
        db_object.validate()
        logging.debug(
            'session %s db object %s updated',
            id(session), db_object
        )
        return db_object


def del_db_object(session, db_object):
    """Delete db object."""
    if not session:
        raise exception.DatabaseException('session param is None')
    with session.begin(subtransactions=True):
        logging.debug(
            'session %s delete db object %s',
            id(session), db_object
        )
        session.delete(db_object)
        logging.debug(
            'session %s db object %s deleted',
            id(session), db_object
        )
        return db_object


def check_ip(ip):
    """Check ip is ip address formatted."""
    try:
        netaddr.IPAddress(ip)
    except Exception as error:
        logging.exception(error)
        raise exception.InvalidParameter(
            'ip address %s format uncorrect' % ip
        )


def check_mac(mac):
    """Check mac is mac address formatted."""
    try:
        netaddr.EUI(mac)
    except Exception as error:
        logging.exception(error)
        raise exception.InvalidParameter(
            'invalid mac address %s' % mac
        )


NAME_PATTERN = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9_-]*')


def check_name(name):
    """Check name meeting name format requirement."""
    if not NAME_PATTERN.match(name):
        raise exception.InvalidParameter(
            'name %s does not match the pattern %s' % (
                name, NAME_PATTERN.pattern
            )
        )


def _check_ipmi_credentials_ip(ip):
    check_ip(ip)


def check_ipmi_credentials(ipmi_credentials):
    """Check ipmi credentials format is correct."""
    if not ipmi_credentials:
        return
    if not isinstance(ipmi_credentials, dict):
        raise exception.InvalidParameter(
            'invalid ipmi credentials %s' % ipmi_credentials

        )
    for key in ipmi_credentials:
        if key not in ['ip', 'username', 'password']:
            raise exception.InvalidParameter(
                'unrecognized field %s in ipmi credentials %s' % (
                    key, ipmi_credentials
                )
            )
    for key in ['ip', 'username', 'password']:
        if key not in ipmi_credentials:
            raise exception.InvalidParameter(
                'no field %s in ipmi credentials %s' % (
                    key, ipmi_credentials
                )
            )
        check_ipmi_credential_field = '_check_ipmi_credentials_%s' % key
        this_module = globals()
        if check_ipmi_credential_field in this_module:
            this_module[check_ipmi_credential_field](
                ipmi_credentials[key]
            )
        else:
            logging.debug(
                'function %s is not defined', check_ipmi_credential_field
            )


def _check_switch_credentials_version(version):
    if version not in ['1', '2c', '3']:
        raise exception.InvalidParameter(
            'unknown snmp version %s' % version
        )


def check_switch_credentials(credentials):
    """Check switch credentials format is correct."""
    if not credentials:
        return
    if not isinstance(credentials, dict):
        raise exception.InvalidParameter(
            'credentials %s is not dict' % credentials
        )
    for key in credentials:
        if key not in ['version', 'community']:
            raise exception.InvalidParameter(
                'unrecognized key %s in credentials %s' % (key, credentials)
            )
    for key in ['version', 'community']:
        if key not in credentials:
            raise exception.InvalidParameter(
                'there is no %s field in credentials %s' % (key, credentials)
            )

        key_check_func_name = '_check_switch_credentials_%s' % key
        this_module = globals()
        if key_check_func_name in this_module:
            this_module[key_check_func_name](
                credentials[key]
            )
        else:
            logging.debug(
                'function %s is not defined',
                key_check_func_name
            )
