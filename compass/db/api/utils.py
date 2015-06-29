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


def _model_condition_func(
    col_attr, value,
    item_condition_func,
    list_condition_func=_default_list_condition_func
):
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
    if value[0] is not None and value[1] is not None:
        return col_attr.between(value[0], value[1])
    if value[0] is not None:
        return col_attr >= value[0]
    if value[1] is not None:
        return col_attr <= value[1]
    return None


def model_order_by(query, model, order_by):
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
    if isinstance(value, list):
        basetype_values = []
        composite_values = []
        for item in value:
            if util.is_instance(item, [list, dict]):
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
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return _replace_output(
                func(*args, **kwargs), **output_mapping
            )
        return wrapper
    return decorator


def _replace_output(data, **output_mapping):
    """Helper to replace output data."""
    if isinstance(data, list):
        return [
            _replace_output(item, **output_mapping)
            for item in data
        ]
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
    """Get wrapped function instance."""
    if func.func_closure:
        for closure in func.func_closure:
            if isfunction(closure.cell_contents):
                return get_wrapped_func(closure.cell_contents)
        return func
    else:
        return func


def wrap_to_dict(support_keys=[], **filters):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return _wrapper_dict(
                func(*args, **kwargs), support_keys, **filters
            )
        return wrapper
    return decorator


def _wrapper_dict(data, support_keys, **filters):
    """Helper for warpping db object into dictionary."""
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
    for key in support_keys:
        if key in data:
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


def replace_input_types(**kwarg_mapping):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            replaced_kwargs = {}
            for key, value in kwargs.items():
                if key in kwarg_mapping:
                    replaced_kwargs[key] = kwarg_mapping[key](value)
                else:
                    replaced_kwargs[key] = value
            return func(*args, **replaced_kwargs)
        return wrapper
    return decorator


def replace_filters(**filter_mapping):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **filters):
            replaced_filters = {}
            for key, value in filters.items():
                if key in filter_mapping:
                    replaced_filters[filter_mapping[key]] = value
                else:
                    replaced_filters[key] = value
            return func(*args, **replaced_filters)
        return wrapper
    return decorator


def supported_filters(
    support_keys=[],
    optional_support_keys=[],
    ignore_support_keys=[],
):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **filters):
            wrapped_func = get_wrapped_func(func)
            argspec = inspect.getargspec(wrapped_func)
            wrapped_args = argspec.args
            must_support_keys = set(support_keys)
            all_support_keys = must_support_keys | set(optional_support_keys)
            filter_keys = set(filters) - set(wrapped_args)
            wrapped_support_keys = set(filters) | set(wrapped_args)
            unsupported_keys = (
                filter_keys - all_support_keys - set(ignore_support_keys)
            )
            if unsupported_keys:
                raise exception.InvalidParameter(
                    'filter keys %s are not supported' % str(
                        list(unsupported_keys)
                    )
                )
            missing_keys = must_support_keys - wrapped_support_keys
            if missing_keys:
                raise exception.InvalidParameter(
                    'filter keys %s not found' % str(
                        list(missing_keys)
                    )
                )
            filtered_filters = dict([
                (key, value)
                for key, value in filters.items()
                if key not in ignore_support_keys
            ])
            return func(*args, **filtered_filters)
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


def filter_output(filter_callbacks, filters, obj, missing_ok=False):
    for callback_key, callback_value in filter_callbacks.items():
        if callback_key not in filters:
            continue
        if callback_key not in obj:
            if missing_ok:
                continue
            else:
                raise exception.InvalidResponse(
                    '%s is not in %s' % (callback_key, obj)
                )
        if not callback_value(
            filters[callback_key], obj[callback_key]
        ):
            return False
    return True


def output_filters(missing_ok=False, **filter_callbacks):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **filters):
            filtered_obj_list = []
            obj_list = func(*args, **filters)
            for obj in obj_list:
                if filter_output(
                    filter_callbacks, filters, obj, missing_ok
                ):
                    filtered_obj_list.append(obj)
            return filtered_obj_list
        return wrapper
    return decorator


def _input_validates(args_validators, kwargs_validators, *args, **kwargs):
    for i, value in enumerate(args):
        if i < len(args_validators) and args_validators[i]:
            args_validators[i](value)
    for key, value in kwargs.items():
        if kwargs_validators.get(key):
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
    for key, value in obj.items():
        if key in kwargs_validators:
            kwargs_validators[key](value)


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
            return obj
        return wrapper
    return decorator


def get_db_object(session, table, exception_when_missing=True, **kwargs):
    """Get db object."""
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
    """Create db object."""
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
    """List db objects."""
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


def update_db_objects(session, table, **filters):
    """Update db objects."""
    with session.begin(subtransactions=True):
        logging.debug(
            'session %s update db objects by filters %s in table %s',
            id(session), filters, table.__name__)
        db_objects = model_filter(
            model_query(session, table), table, **filters
        ).all()
        for db_object in db_objects:
            logging.debug('update db object %s', db_object)
            session.flush()
            db_object.update()
            db_object.validate()
        logging.debug(
            'session %s db objects %s updated',
            id(session), db_objects
        )
        return db_objects


def update_db_object(session, db_object, **kwargs):
    """Update db object."""
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


NAME_PATTERN = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9_-]*')


def check_name(name):
    if not NAME_PATTERN.match(name):
        raise exception.InvalidParameter(
            'name %s does not match the pattern %s' % (
                name, NAME_PATTERN.pattern
            )
        )


def _check_ipmi_credentials_ip(ip):
    check_ip(ip)


def check_ipmi_credentials(ipmi_credentials):
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


def export_database(session, table=None):
    """Export user related tables to csv."""

    def _get_attribute(object, attribute_list, result):
            if len(attribute_list) == 1:
                return result.append(getattr(object, attribute_list[0]))
            else:
                for item in attribute_list:
                    sub_object = getattr(object, item)
                    attribute_list.pop(0)
                    _get_attribute(sub_object, attribute_list, result)

    if table is not None:
        logging.info('get info from table %s', table)
        rm_column = ['created_at', 'updated_at', 'id']
        header = []
        if table.__tablename__ is not 'host':
            headers = []
            for column in table.__mapper__.columns:
                if column.name not in rm_column:
                    headers.append(column.name)
            header.append(headers)
        else:
            headers = []
            for column in table.__mapper__.columns:
                if column.name not in ['created_at', 'updated_at']:
                    headers.append(column.name)
            header.append(headers)
        if hasattr(table, 'foreign_table_keys'):
            for i in range(len(header[0])):
                for key, value in table.foreign_table_keys.items():
                    if header[0][i] == key:
                        header[0][i] = value

        data = []
        records = list_db_objects(session, table)
        for record in records:
            data_line = []
            for table_header in header[0]:
                if '.' in table_header:
                    object_names = table_header.split('.')
                    object_names.pop(0)
                    _get_attribute(record, object_names, data_line)
                else:
                    data_line.append(getattr(record, table_header))
            data.append(data_line)
        export_datas = header + data
        logging.info('final export data: %s', export_datas)
        return export_datas

    else:
        all_tables = []
        export_datas = []
        for table in dir(models):
            table_object = getattr(models, table)
            if hasattr(table_object, 'able_to_export') and (
                table_object.able_to_export is True
            ):
                all_tables.append(table_object)
        for table in all_tables:
            table_name = [[table.__table__.name]]
            rm_column = ['created_at', 'updated_at', 'id']
            header = []
            if table.__tablename__ is not 'host':
                headers = []
                for column in table.__mapper__.columns:
                    if column.name not in rm_column:
                        headers.append(column.name)
                header.append(headers)
            else:
                headers = []
                for column in table.__mapper__.columns:
                    if column.name not in rm_column:
                        headers.append(column.name)
                header.append(headers)
            if hasattr(table, 'foreign_table_keys'):
                for i in range(len(header[0])):
                    for key, value in table.foreign_table_keys.items():
                        if header[0][i] == key:
                            header[0][i] = value
            data = []
            records = list_db_objects(session, table)
            for record in records:
                data_line = []
                for table_header in header[0]:
                    if '.' in table_header:
                        object_names = table_header.split('.')
                        object_names.pop(0)
                        _get_attribute(record, object_names, data_line)
                    else:
                        data_line.append(getattr(record, table_header))
                data.append(data_line)
            export_datas += [[]] + table_name + header + data
        logging.info('final export data None: %s', export_datas)
        return export_datas


def import_database(session, import_data):
    logging.info('import_data: %s', import_data)
    desire_table = []
    foreign_tables = []
    foreign_objects = []
    second_tables = ['clusterhost', 'host_network']
    second_objects = [models.ClusterHost, models.HostNetwork]
    for table in dir(models):
        table_object = getattr(models, table)
        if hasattr(table_object, 'able_to_export') and (
            table_object.able_to_export is True
        ):
            desire_table.append(table_object.__table__.name)
        if hasattr(table_object, 'foreign_table_keys'):
            foreign_objects.append(table_object)
            foreign_tables.append(table_object.__table__.name)
    missing_table = set(desire_table) - set(import_data.keys())
    if missing_table:
        logging.error('missing tables: %s', missing_table)
        raise exception.DatabaseException(
            'missing tables %s' % missing_table
        )
    for raw_name, datas in import_data.items():
        table_name = ''.join(name.capitalize() for name in raw_name.split('_'))
        if raw_name not in foreign_tables:
            if raw_name == 'switch':
                for data in datas:
                    for key, value in data.items():
                        if key == 'ip':
                            data['ip_int'] = value
                            data.pop('ip')
                            break
            for data in datas:
                table_obj = getattr(models, table_name)
                logging.info('add %s to table %s', data, table_name)
                db_object = table_obj(**data)
                session.add(db_object)
                session.flush()
            import_data.pop(raw_name)

    for raw_name, datas in import_data.items():
        table_name = ''.join(name.capitalize() for name in raw_name.split('_'))
        if raw_name in (set(foreign_tables) - set(second_tables)):
            for foreign_object in foreign_objects:
                foreign_keys = foreign_object.foreign_table_keys
                for data in datas:
                    for key, value in data.items():
                        if '.' in key:
                            foreign_data = key.split('.')
                            foreign_data.pop(0)
                            if foreign_data[0] == 'creator':
                                user = get_db_object(
                                    session,
                                    models.User,
                                    email=value
                                )
                                data['creator_id'] = user.id
                                data.pop(key)
                                break
                            elif foreign_data[0] == 'switch':
                                switch = get_db_object(
                                    session,
                                    models.Switch,
                                    ip_int=value
                                )
                                data['switch_id'] = switch.id
                                data.pop(key)
                                break
                            elif foreign_data[0] == 'machine':
                                machine = get_db_object(
                                    session,
                                    models.Machine,
                                    mac=value
                                )
                                for k, v in foreign_keys.items():
                                    if v == key:
                                        data[k] = machine.id
                                        data.pop(key)
                            elif foreign_data[0] == 'subnet':
                                subnet = get_db_object(
                                    session,
                                    models.Subnet,
                                    subnet=value
                                )
                                data['subnet_id'] = subnet.id
                                data.pop(key)
                                break
                            else:
                                model_name = ''.join(
                                    name.capitalize() for name in (
                                        foreign_data[0].split('_')
                                    )
                                )
                                if model_name == 'Os':
                                    model_name = 'OperatingSystem'
                                elif model_name == 'Flavor':
                                    model_name = 'AdapterFlavor'
                                elif model_name == 'OsInstaller':
                                    model_name = 'OSInstaller'
                                object = get_db_object(
                                    session,
                                    getattr(models, model_name),
                                    name=value
                                )
                                for k, v in foreign_keys.items():
                                    if key == v:
                                        data[k] = object.id
                                        data.pop(key)
            for data in datas:
                table_obj = getattr(models, table_name)
                logging.info('add %s to table %s', data, table_name)
                db_object = table_obj(**data)
                session.add(db_object)
                session.flush()
            import_data.pop(raw_name)

    for raw_name, datas in import_data.items():
        table_name = ''.join(name.capitalize() for name in raw_name.split('_'))
        for second_object in second_objects:
            foreign_keys = second_object.foreign_table_keys
            for data in datas:
                for key, value in data.items():
                    if '.' in key:
                        foreign_data = key.split('.')
                        foreign_data.pop(0)
                        if foreign_data[0] == 'subnet':
                            subnet = get_db_object(
                                session,
                                models.Subnet,
                                subnet=value
                            )
                            data['subnet_id'] = subnet.id
                            data.pop(key)
                        else:
                            model_name = ''.join(
                                name.capitalize() for name in (
                                    foreign_data[0].split('_')
                                )
                            )
                            object = get_db_object(
                                session,
                                getattr(models, model_name),
                                name=value
                            )
                            for k, v in foreign_keys.items():
                                if v == key:
                                    data[k] = object.id
                                    data.pop(key)
        for data in datas:
            if raw_name == 'clusterhost':
                table_obj = models.ClusterHost
            else:
                table_obj = getattr(models, table_name)
            logging.info('add %s to table %s', data, table_name)
            db_object = table_obj(**data)
            session.add(db_object)
            session.flush()
    return 'Data has been import into database.'
