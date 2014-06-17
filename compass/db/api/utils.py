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
import copy
import functools
import inspect
import logging
import netaddr
import re

from sqlalchemy import and_
from sqlalchemy import or_

from compass.db import exception
from compass.db import models


def model_query(session, model):
    """model query."""
    if not issubclass(model, models.BASE):
        raise exception.DatabaseException("model should be sublass of BASE!")

    return session.query(model)


def _default_list_condition_func(col_attr, value, condition_func):
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
    if value:
        return condition_func(col_attr, value[0])
    else:
        return None


def _model_filter_by_condition(
    query, col_attr, value, condition_func,
    list_condition_func=_default_list_condition_func
):
    if isinstance(value, list):
        condition = list_condition_func(
            col_attr, value, condition_func
        )
    else:
        condition = condition_func(col_attr, value)
    if condition is not None:
        query = query.filter(condition)
    return query


def _between_condition(col_attr, value):
    if value[0] is not None and value[1] is not None:
        col_attr.between(value[0], value[1])
    if value[0] is not None:
        return col_attr >= value[0]
    if value[1] is not None:
        return col_attr <= value[1]
    return None


def model_filter(query, model, **filters):
    print 'model query %s: filter %s' % (query, filters)
    for key, value in filters.items():
        col_attr = getattr(model, key)
        if isinstance(value, list):
            query = query.filter(col_attr.in_(value))
        elif isinstance(value, dict):
            if 'eq' in value:
                query = _model_filter_by_condition(
                    query, col_attr, value['eq'],
                    lambda attr, data: attr == data,
                    lambda attr, data, condition_func: attr.in_(data)
                )
            if 'lt' in value:
                query = _model_filter_by_condition(
                    query, col_attr, value['lt'],
                    lambda attr, data: attr < data,
                    _one_item_list_condition_func
                )
            if 'gt' in value:
                query = _model_filter_by_condition(
                    query, col_attr, value['gt'],
                    lambda attr, data: attr > data,
                    _one_item_list_condition_func
                )
            if 'le' in value:
                query = _model_filter_by_condition(
                    query, col_attr, value['le'],
                    lambda attr, data: attr <= data,
                    _one_item_list_condition_func
                )
            if 'ge' in value:
                query = _model_filter_by_condition(
                    query, col_attr, value['ge'],
                    lambda attr, data: attr >= data,
                    _one_item_list_condition_func
                )
            if 'ne' in value:
                query = _model_filter_by_condition(
                    query, col_attr, value['eq'], None,
                    lambda attr, data, condition_func: ~attr.in_(data)
                )
            if 'in' in value:
                query = query.filter(col_attr.in_(value['in']))
            if 'startswith' in value:
                query = _model_filter_by_condition(
                    query, col_attr, value['startswitch'],
                    lambda attr, data: attr.like('%s%%' % data)
                )
            if 'endswith' in value:
                query = _model_filter_by_condition(
                    query, col_attr, value['endswitch'],
                    lambda attr, data: attr.like('%%%s' % data)
                )
            if 'like' in value:
                query = _model_filter_by_condition(
                    query, col_attr, value['like'],
                    lambda attr, data: attr.like('%%%s%%' % data)
                )
            if 'between' in value:
                query = _model_filter_by_condition(
                    query, col_attr, value['between'],
                    _between_condition
                )
        else:
            query = query.filter(col_attr == value)

    return query


def wrap_to_dict(support_keys=[]):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            obj = func(*args, **kwargs)
            if isinstance(obj, list):
                obj = [_wrapper_dict(o, support_keys) for o in obj]
            else:
                obj = _wrapper_dict(obj, support_keys)
            return obj
        return wrapper
    return decorator


def _wrapper_dict(data, support_keys):
    """Helper for warpping db object into dictionary."""
    info = {}
    if not isinstance(data, dict):
        data = data.to_dict()
    for key in support_keys:
        if key in data:
            info[key] = data[key]
    return info


def supported_filters(support_keys=[], optional_support_keys=[]):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **filters):
            print 'filter %s %s' % (args, filters)
            must_support_keys = set(support_keys)
            all_support_keys = must_support_keys | set(optional_support_keys)
            supports = {}
            for filter_key, filter_value in filters.items():
                if filter_key not in all_support_keys:
                    raise exception.InvalidParameter(
                        'filter key %s is not supported' % filter_key
                    )

                if filter_key in must_support_keys:
                    must_support_keys.remove(filter_key)

                supports[filter_key] = filter_value

            if must_support_keys:
                raise exception.InvalidParameter(
                    'filter keys %s not found' % list(must_support_keys)
                )
            return func(*args, **supports)
        return wrapper
    return decorator


def _obj_equal(check, obj):
    if check == obj:
        return True
    if not issubclass(obj.__class__, check.__class__):
        return False
    if isinstance(obj, dict):
        return _dict_equal(check, obj)
    elif isinstance(obj, list):
        return _list_equal(check, obj)
    else:
        return False


def _list_equal(check_list, obj_list):
    return set(check_list).issubset(set(obj_list))


def _dict_equal(check_dict, obj_dict):
    for key, value in check_dict.items():
        if (
            key not in obj_dict or
            not _obj_equal(check_dict[key], obj_dict[key])
        ):
            return False
    return True


def general_filter_callback(general_filter, obj):
    if 'resp_eq' in general_filter:
        return _obj_equal(general_filter['resp_eq'], obj)
    elif 'resp_in' in general_filter:
        in_filters = general_filter['resp_in']
        if not in_filters:
            return True
        for in_filer in in_filters:
            if _obj_equal(in_filer, obj):
                return True
        return False
    elif 'resp_lt' in general_filter:
        return obj < general_filter['resp_lt']
    elif 'resp_le' in general_filter:
        return obj <= general_filter['resp_le']
    elif 'resp_gt' in general_filter:
        return obj > general_filter['resp_gt']
    elif 'resp_ge' in general_filter:
        return obj >= general_filter['resp_gt']
    elif 'resp_match' in general_filter:
        return bool(re.match(general_filter['resp_match'], obj))
    else:
        return True


def filter_output(filter_callbacks, filters, obj):
    for callback_key, callback_value in filter_callbacks.items():
        if callback_key not in filters:
            continue
        if callback_key not in obj:
            raise exception.InvalidResponse(
                '%s is not in %s' % (callback_key, obj)
            )
        if not callback_value(
            filters[callback_key], obj[callback_key]
        ):
            return False
    return True


def output_filters(**filter_callbacks):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **filters):
            filtered_obj_list = []
            obj_list = func(*args, **filters)
            for obj in obj_list:
                if filter_output(filter_callbacks, filters, obj):
                    filtered_obj_list.append(obj)
            return filtered_obj_list
        return wrapper
    return decorator


def _input_validates(args_validators, kwargs_validators, *args, **kwargs):
    for i, value in enumerate(args):
        if i < len(args_validators) and args_validators[i]:
            if isinstance(value, list):
                for sub_value in value:
                    args_validators[i](sub_value)
            else:
                args_validators[i](value)
    for key, value in kwargs.items():
        if kwargs_validators.get(key):
            if isinstance(value, list):
                for sub_value in value:
                    kwargs_validators[key](sub_value)
            else:
                kwargs_validators[key](value)


def input_validates(*args_validators, **kwargs_validators):
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


def _output_validates(kwargs_validators, obj):
    if not isinstance(obj, dict):
        obj = obj.to_dict()
    for key, value in obj.items():
        if kwargs_validators.get(key):
            kwargs_validators[key](value)


def validate_outputs(kwargs_validators, obj):
    return _output_validates(kwargs_validators, obj)


def output_validates(**kwargs_validators):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            obj = func(*args, **kwargs)
            if isinstance(obj, list):
                for obj_item in obj:
                    _output_validates(kwargs_validators, obj_item)
            else:
                _output_validates(kwargs_validators, obj)
        return wrapper
    return decorator


def get_db_object(session, table, exception_when_missing=True, **kwargs):
    """Get db object."""
    with session.begin(subtransactions=True):
        logging.debug('get db object %s from table %s',
                      kwargs, table.__name__)
        db_object = model_filter(
            model_query(session, table), table, **kwargs
        ).first()
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
    """Create db object."""
    with session.begin(subtransactions=True):
        logging.debug('add object %s atributes %s to table %s',
                      args, kwargs, table.__name__)
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
        db_object.initialize()
        session.flush()
        db_object.validate()
        return db_object


def list_db_objects(session, table, **filters):
    """List db objects."""
    with session.begin(subtransactions=True):
        logging.debug('list db objects by filters %s in table %s',
                      filters, table.__name__)
        return model_filter(
            model_query(session, table), table, **filters
        ).all()


def del_db_objects(session, table, **filters):
    """delete db objects."""
    with session.begin(subtransactions=True):
        logging.debug('delete db objects by filters %s in table %s',
                      filters, table.__name__)
        query = model_filter(
            model_query(session, table), table, **filters
        )
        db_objects = query.all()
        query.delete()
        return db_objects


def update_db_object(session, db_object, **kwargs):
    """Update db object."""
    with session.begin(subtransactions=True):
        logging.debug('update db object %s by value %s',
                      db_object, kwargs)
        for key, value in kwargs.items():
            setattr(db_object, key, value)
        db_object.initialize()
        session.flush()
        db_object.validate()


def del_db_object(session, db_object):
    """Delete db object."""
    with session.begin(subtransactions=True):
        logging.debug('delete db object %s', db_object)
        session.delete(db_object)


def check_ip(ip):
    try:
        netaddr.IPAddress(ip)
    except Exception as error:
        logging.exception(error)
        raise exception.InvalidParameter(
            'ip address %s format uncorrect' % ip
        )


def check_mac(mac):
    try:
        netaddr.EUI(mac)
    except Exception as error:
        logging.exception(error)
        raise exception.InvalidParameter(
            'invalid mac address %s' % mac
        )
