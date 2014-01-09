"""Utility functions
   Including functions of get/getbulk/walk/set of snmp for three versions
"""
import imp
import re
import logging


def load_module(mod_name, path, host=None, credential=None):
    """ Load a module instance.

    :param str mod_name: module name
    :param str path: directory of the module
    :param str host: switch ip address
    :param str credential: credential used to access switch
    """
    instance = None
    try:
        file, path, descr = imp.find_module(mod_name, [path])
        if file:
            mod = imp.load_module(mod_name, file, path, descr)
            if host and credential:
                instance = getattr(mod, mod.CLASS_NAME)(host, credential)
            else:
                instance = getattr(mod, mod.CLASS_NAME)()

    except ImportError as exc:
        logging.error('No such plugin : %s', mod_name)
        logging.exception(exc)

    finally:
        return instance


def ssh_remote_execute(host, username, password, cmd, *args):
    """SSH to execute script on remote machine

    :param host: ip of the remote machine
    :param username: username to access the remote machine
    :param password: password to access the remote machine
    :param cmd: command to execute
    """
    try:
        import paramiko
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=username, password=password)
        stdin, stdout, stderr = client.exec_command(cmd)
        return stdout.readlines()

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
        client.close()


def valid_ip_format(ip_address):
    """Valid the format of an Ip address"""

    if not re.match(r'^((([0-2]?\d{0,2}\.){3}([0-2]?\d{0,2}))'
                    '|(([\da-fA-F]{1,4}:){7}([\da-fA-F]{1,4})))$',
                    ip_address):
        # check IP's format is match ipv4 or ipv6 by regex
        return False

    return True

#################################################################
# Implement snmpwalk and snmpget funtionality
# The structure of returned dictionary will by tag/iid/value/type
#################################################################
AUTH_VERSIONS = {'v1': 1,
                 'v2c': 2,
                 'v3': 3}


def snmp_walk(host, credential, *args):
    """Impelmentation of snmpwalk functionality

    :param host: switch ip
    :param credential: credential to access switch
    :param args: OIDs
    """
    try:
        import netsnmp

    except ImportError:
        logging.error("Module 'netsnmp' do not exist! Please install it first")
        return None

    if 'Version' not in credential or 'Community' not in credential:
        logging.error("[utils] missing 'Version' and 'Community' in %s",
                      credential)
        return None

    if credential['Version'] in AUTH_VERSIONS:
        version = AUTH_VERSIONS[credential['Version']]
        credential['Version'] = version

    varbind_list = []
    for arg in args:
        varbind = netsnmp.Varbind(arg)
        varbind_list.append(varbind)

    var_list = netsnmp.VarList(*varbind_list)

    res = netsnmp.snmpwalk(var_list, DestHost=host, **credential)

    result = []
    for var in var_list:
        response = {}
        response['elem_name'] = var.tag
        response['iid'] = var.iid
        response['value'] = var.val
        response['type'] = var.type
        result.append(response)

    return result


def snmp_get(host, credential, object_type):
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

    if 'Version' not in credential or 'Community' not in credential:
        logging.error('[uitls][snmp_get] missing keywords in %s for %s',
                      credential, host)
        return None

    if credential['Version'] in AUTH_VERSIONS:
        version = AUTH_VERSIONS[credential['Version']]
        credential['Version'] = version

    varbind = netsnmp.Varbind(object_type)
    res = netsnmp.snmpget(varbind, DestHost=host, **credential)
    if not res:
        logging.error('no result found for %s %s', host, credential)
        return None

    return res[0]
