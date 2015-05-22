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

"""Utility functions
   Including functions of get/getbulk/walk/set of snmp for three versions
"""
import imp
import logging
import re
import subprocess

from compass.hdsdiscovery.error import TimeoutError


def load_module(mod_name, path, host=None, credential=None):
    """Load a module instance.

    :param str mod_name: module name
    :param str path: directory of the module
    :param str host: switch ip address
    :param str credential: credential used to access switch
    """
    try:
        mod_file, path, descr = imp.find_module(mod_name, [path])
        if mod_file:
            mod = imp.load_module(mod_name, mod_file, path, descr)
            if host and credential:
                instance = getattr(mod, mod.CLASS_NAME)(host, credential)
            else:
                instance = getattr(mod, mod.CLASS_NAME)()

        return instance
    except ImportError as exc:
        logging.error('No such module found: %s', mod_name)
        logging.exception(exc)
        return None


def ssh_remote_execute(host, username, password, cmd):
    """SSH to execute script on remote machine

    :param host: ip of the remote machine
    :param username: username to access the remote machine
    :param password: password to access the remote machine
    :param cmd: command to execute
    """
    try:
        import paramiko
        if not cmd:
            logging.error("[hdsdiscovery][utils][ssh_remote_execute] command"
                          "is None! Failed!")
            return None

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=username, password=password, timeout=15)
        stdin, stdout, stderr = client.exec_command(cmd)
        result = stdout.readlines()
        return result

    except ImportError as exc:
        logging.error("[hdsdiscovery][utils][ssh_remote_execute] failed to"
                      "load module 'paramiko', donnot exist!")
        logging.exception(exc)
        return None

    except Exception as exc:
        logging.error("[hdsdiscovery][utils][ssh_remote_execute] failed: %s",
                      cmd)
        logging.exception(exc)
        return None

    finally:
        stdin.close()
        stdout.close()
        stderr.close()
        client.close()


def valid_ip_format(ip_address):
    """Valid the format of an Ip address."""

    if not re.match(r'^((([0-2]?\d{0,2}\.){3}([0-2]?\d{0,2}))'
                    r'|(([\da-fA-F]{1,4}:){7}([\da-fA-F]{1,4})))$',
                    ip_address):
        # check IP's format is match ipv4 or ipv6 by regex
        return False

    return True

#################################################################
# Implement snmpwalk and snmpget funtionality
# The structure of returned dictionary will by tag/iid/value/type
#################################################################
AUTH_VERSIONS = {
    '1': 1,
    '2c': 2,
    '3': 3
}


def snmp_walk(host, credential, *args, **kwargs):
    """Impelmentation of snmpwalk functionality

    :param host: switch ip
    :param credential: credential to access switch
    :param args: OIDs
    :param kwargs: key-value pairs
    """
    try:
        import netsnmp

    except ImportError:
        logging.error("Module 'netsnmp' do not exist! Please install it first")
        return None

    if 'version' not in credential or 'community' not in credential:
        logging.error("[utils] missing 'version' and 'community' in %s",
                      credential)
        return None

    version = None
    if credential['version'] in AUTH_VERSIONS:
        version = AUTH_VERSIONS[credential['version']]

    varbind_list = []
    for arg in args:
        varbind = netsnmp.Varbind(arg)
        varbind_list.append(varbind)

    var_list = netsnmp.VarList(*varbind_list)

    netsnmp.snmpwalk(var_list,
                     DestHost=host,
                     Version=version,
                     Community=credential['community'],
                     **kwargs)

    result = []
    if not var_list:
        logging.error("[hsdiscovery][utils][snmp_walk] retrived no record!")
        return result

    for var in var_list:
        response = {}
        response['elem_name'] = var.tag
        response['iid'] = var.iid
        response['value'] = var.val
        response['type'] = var.type
        result.append(response)

    return result


def snmp_get(host, credential, object_type, **kwargs):
    """Impelmentation of snmp get functionality

    :param object_type: mib object
    :param host: switch ip
    :param credential: the dict of credential to access switch
    """
    try:
        import netsnmp

    except ImportError:
        logging.error("Module 'netsnmp' do not exist! Please install it first")
        return None

    if 'version' not in credential or 'community' not in credential:
        logging.error('[uitls][snmp_get] missing keywords in %s for %s',
                      credential, host)
        return None

    version = None
    if credential['version'] in AUTH_VERSIONS:
        version = AUTH_VERSIONS[credential['version']]

    varbind = netsnmp.Varbind(object_type)
    res = netsnmp.snmpget(varbind,
                          DestHost=host,
                          Version=version,
                          Community=credential['community'],
                          **kwargs)
    if res and res[0]:
        return res[0]

    logging.info('no result found for %s %s', host, credential)
    return None


SSH_CREDENTIALS = {"username": "", "password": ""}
SNMP_V2_CREDENTIALS = {"version": "", "community": ""}


def is_valid_snmp_v2_credential(credential):
    """check if credential is valid snmp v2 credential."""
    if credential.keys() != SNMP_V2_CREDENTIALS.keys():
        return False
    if credential['version'] != '2c':
        logging.error("The value of version in credential is not '2c'!")
        return False
    return True


def is_valid_ssh_credential(credential):
    """check if credential is valid ssh credential."""
    if credential.keys() != SSH_CREDENTIALS.keys():
        return False
    return True


def snmpget_by_cl(host, credential, oid, timeout=8, retries=3):
    """snmpget by credential."""
    if not is_valid_snmp_v2_credential(credential):
        logging.error("[utils][snmpget_by_cl] Credential %s cannot be used "
                      "for SNMP request!", credential)
        return None

    version = credential['version']
    community = credential['community']
    cmd = "snmpget -v %s -c %s -Ob -r %s -t %s %s %s" % (
        version, community, retries, timeout, host, oid)

    returncode, output, err = exec_command(cmd)

    if returncode and err:
        logging.error("[snmpget_by_cl] %s", err)
        raise TimeoutError(err.strip('\n'))

    return output.strip('\n')


def snmpwalk_by_cl(host, credential, oid, timeout=5, retries=3):
    """snmpwalk by credential."""
    if not is_valid_snmp_v2_credential(credential):
        logging.error("[utils][snmpwalk_by_cl] Credential %s cannot be used "
                      "for SNMP request!", credential)
        return None

    version = credential['version']
    community = credential['community']
    cmd = "snmpwalk -v %s -c %s -Cc -r %s -t %s -Ob %s %s" % (
        version, community, retries, timeout, host, oid)

    returncode, output, err = exec_command(cmd)

    if returncode and err:
        logging.debug("[snmpwalk_by_cl] %s ", err)
        raise TimeoutError(err)

    result = []
    if not output:
        return result

    output = output.split('\n')
    for line in output:
        if not line:
            continue
        temp = {}
        arr = line.split(" ")
        temp['iid'] = arr[0].split('.', 1)[-1]
        temp['value'] = arr[-1]
        result.append(temp)

    return result


def exec_command(command):
    """Execute command.

    Return a tuple: returncode, output and error message(None if no error).
    """
    sub_p = subprocess.Popen(command,
                             shell=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    output, err_msg = sub_p.communicate()
    return (sub_p.returncode, output, err_msg)
