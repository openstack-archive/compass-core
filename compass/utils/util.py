# Copyright 2014 Huawei Technologies Co. Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module to provider util functions in all compass code

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""

import crypt
import datetime
import logging
import os
import os.path
import re
import setting_wrapper as setting
import sys
import warnings


def deprecated(func):
    """This is a decorator which can be used to mark functions as deprecated.

    It will result in a warning being emitted when the function is used.
    """
    def new_func(*args, **kwargs):
        warnings.warn(
            "Call to deprecated function %s." % func.__name__,
            category=DeprecationWarning
        )
        return func(*args, **kwargs)

    new_func.__name__ = func.__name__
    new_func.__doc__ = func.__doc__
    new_func.__dict__.update(func.__dict__)
    return new_func


def parse_datetime(date_time, exception_class=Exception):
    """Parse datetime str to get datetime object.

    The date time format is %Y-%m-%d %H:%M:%S
    """
    try:
        return datetime.datetime.strptime(
            date_time, '%Y-%m-%d %H:%M:%S'
        )
    except Exception as error:
        logging.exception(error)
        raise exception_class(
            'date time %s format is invalid' % date_time
        )


def parse_datetime_range(date_time_range, exception_class=Exception):
    """parse datetime range str to pair of datetime objects.

    The date time range format is %Y-%m-%d %H:%M:%S,%Y-%m-%d %H:%M:%S
    """
    try:
        start, end = date_time_range.split(',')
    except Exception as error:
        logging.exception(error)
        raise exception_class(
            'there is no `,` in date time range %s' % date_time_range
        )
    if start:
        start_datetime = parse_datetime(start, exception_class)
    else:
        start_datetime = None
    if end:
        end_datetime = parse_datetime(end, exception_class)
    else:
        end_datetime = None
    return start_datetime, end_datetime


def parse_request_arg_dict(arg, exception_class=Exception):
    """parse string to dict.

    The str is formatted like a=b;c=d and parsed to
    {'a': 'b', 'c': 'd'}
    """
    arg_dict = {}
    arg_pairs = arg.split(';')
    for arg_pair in arg_pairs:
        try:
            arg_name, arg_value = arg_pair.split('=', 1)
        except Exception as error:
            logging.exception(error)
            raise exception_class(
                'there is no `=` in %s' % arg_pair
            )
        arg_dict[arg_name] = arg_value
    return arg_dict


def format_datetime(date_time):
    """Generate string from datetime object."""
    return date_time.strftime("%Y-%m-%d %H:%M:%S")


def merge_dict(lhs, rhs, override=True):
    """Merge nested right dict into left nested dict recursively.

    :param lhs: dict to be merged into.
    :type lhs: dict
    :param rhs: dict to merge from.
    :type rhs: dict
    :param override: the value in rhs overide the value in left if True.
    :type override: boolean
    """
    if not isinstance(lhs, dict) or not isinstance(rhs, dict):
        if override:
            return rhs
        else:
            return lhs

    for key, value in rhs.items():
        if key not in lhs:
            lhs[key] = rhs[key]
        else:
            lhs[key] = merge_dict(lhs[key], value, override)

    return lhs


def recursive_merge_dict(name, all_dicts, parents):
    """Recursively merge parent dict into base dict."""
    parent_name = parents.get(name, None)
    base_dict = all_dicts.get(name, {})
    if not parent_name:
        return base_dict
    merged = recursive_merge_dict(parent_name, all_dicts, parents)
    return merge_dict(base_dict, merged, override=False)


def encrypt(value, crypt_method=None):
    """Get encrypted value."""
    if not crypt_method:
        if hasattr(crypt, 'METHOD_MD5'):
            crypt_method = crypt.METHOD_MD5
        else:
            # for python2.7, copy python2.6 METHOD_MD5 logic here.
            from random import choice
            import string

            _saltchars = string.ascii_letters + string.digits + './'

            def _mksalt():
                """generate salt."""
                salt = '$1$'
                salt += ''.join(choice(_saltchars) for _ in range(8))
                return salt

            crypt_method = _mksalt()

    return crypt.crypt(value, crypt_method)


def parse_time_interval(time_interval_str):
    """parse string of time interval to time interval.

    supported time interval unit: ['d', 'w', 'h', 'm', 's']
    Examples:
       time_interval_str: '3d 2h' time interval to 3 days and 2 hours.
    """
    if not time_interval_str:
        return 0

    time_interval_tuple = [
        time_interval_element
        for time_interval_element in time_interval_str.split(' ')
        if time_interval_element
    ]
    time_interval_dict = {}
    time_interval_unit_mapping = {
        'd': 'days',
        'w': 'weeks',
        'h': 'hours',
        'm': 'minutes',
        's': 'seconds'
    }
    for time_interval_element in time_interval_tuple:
        mat = re.match(r'^([+-]?\d+)(w|d|h|m|s).*', time_interval_element)
        if not mat:
            continue

        time_interval_value = int(mat.group(1))
        time_interval_unit = time_interval_unit_mapping[mat.group(2)]
        time_interval_dict[time_interval_unit] = (
            time_interval_dict.get(time_interval_unit, 0) + time_interval_value
        )

    time_interval = datetime.timedelta(**time_interval_dict)
    if sys.version_info[0:2] > (2, 6):
        return time_interval.total_seconds()
    else:
        return (
            time_interval.microseconds + (
                time_interval.seconds + time_interval.days * 24 * 3600
            ) * 1e6
        ) / 1e6


def get_plugins_config_files(name, suffix=".conf"):
    """walk through each of plugin to find all the config files in the"""
    """name directory"""

    plugins_path = setting.PLUGINS_DIR
    files = []
    if os.path.exists(plugins_path):
        for plugin in os.listdir(plugins_path):
            plugin_path = os.path.join(plugins_path, plugin)
            plugin_config = os.path.join(plugin_path, name)
            if os.path.exists(plugin_config):
                for component in os.listdir(plugin_config):
                    if not component.endswith(suffix):
                        continue
                    files.append(os.path.join(plugin_config, component))
    return files


def load_configs(
    config_dir, config_name_suffix='.conf',
    env_globals={}, env_locals={}
):
    """Load configurations from config dir."""
    """The config file could be in the config_dir or in plugins config_dir"""
    """The plugins config_dir is formed as, for example /etc/compass/adapter"""
    """Then the plugins config_dir is /etc/compass/plugins/xxx/adapter"""

    # TODO(Carl) instead of using config_dir, it should use a name such as
    # adapter etc, however, doing it requires a lot client sites changes,
    # will do it later.

    configs = []
    config_files = []
    config_dir = str(config_dir)

    """search for config_dir"""
    if os.path.exists(config_dir):
        for component in os.listdir(config_dir):
            if not component.endswith(config_name_suffix):
                continue
            config_files.append(os.path.join(config_dir, component))

    """search for plugins config_dir"""
    index = config_dir.rfind("/")

    config_files.extend(get_plugins_config_files(config_dir[index + 1:],
                                                 config_name_suffix))

    if not config_files:
        logging.error('path %s and plugins does not exist', config_dir)
    for path in config_files:
        logging.debug('load config from %s', path)
        config_globals = {}
        config_globals.update(env_globals)
        config_locals = {}
        config_locals.update(env_locals)
        try:
            execfile(path, config_globals, config_locals)
        except Exception as error:
            logging.exception(error)
            raise error
        configs.append(config_locals)
    return configs


def pretty_print(*contents):
    """pretty print contents."""
    if len(contents) == 0:
        print ""
    else:
        print "\n".join(content for content in contents)


def get_switch_machines_from_file(filename):
    """get switch machines from file."""
    switches = []
    switch_machines = {}
    with open(filename) as switch_file:
        for line in switch_file:
            line = line.strip()
            if not line:
                # ignore empty line
                continue

            if line.startswith('#'):
                # ignore comments
                continue

            columns = [column for column in line.split(',')]
            if not columns:
                # ignore empty line
                continue

            if columns[0] == 'switch':
                (switch_ip, switch_vendor, switch_version,
                 switch_community, switch_state) = columns[1:]
                switches.append({
                    'ip': switch_ip,
                    'vendor': switch_vendor,
                    'credentials': {
                        'version': switch_version,
                        'community': switch_community,
                    },
                    'state': switch_state,
                })
            elif columns[0] == 'machine':
                switch_ip, switch_port, mac = columns[1:]
                switch_machines.setdefault(switch_ip, []).append({
                    'mac': mac,
                    'port': switch_port,
                })

    return (switches, switch_machines)


def execute_cli_by_ssh(cmd, host, username, password=None,
                       keyfile='/root/.ssh/id_rsa', nowait=False):
    """SSH to execute script on remote machine

    :param host: ip of the remote machine
    :param username: username to access the remote machine
    :param password: password to access the remote machine
    :param cmd: command to execute

    """
    if not cmd:
        logging.error("No command found!")
        raise Exception('No command found!')

    if nowait:
        cmd = "nohup %s >/dev/null 2>&1 &" % cmd

    stdin = None
    stdout = None
    stderr = None
    try:
        import paramiko
        from paramiko import ssh_exception

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if password:
            client.connect(host, username=username, password=password)
        else:
            client.load_system_host_keys()
            client.connect(
                host, username=username,
                key_filename=keyfile, look_for_keys=True
            )
        stdin, stdout, stderr = client.exec_command(cmd)
        result = stdout.readlines()
        logging.info("result of command '%s' is '%s'!" % (cmd, result))
        return result

    except ImportError:
        err_msg = "Cannot find Paramiko package!"
        logging.error(err_msg)
        raise ImportError(err_msg)

    except (ssh_exception.BadHostKeyException,
            ssh_exception.AuthenticationException,
            ssh_exception.SSHException):

        err_msg = 'SSH connection error or command execution failed!'
        logging.error(err_msg)
        raise Exception(err_msg)

    except Exception as exc:
        logging.error(
            'Failed to execute command "%s", exception is %s' % (cmd, exc)
        )
        raise Exception(exc)

    finally:
        for resource in [stdin, stdout, stderr]:
            if resource:
                resource.close()

        client.close()
