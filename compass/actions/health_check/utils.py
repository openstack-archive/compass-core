"""Compass Health Check heavy-lifting utilities"""

import os
import platform
import commands


def validate_setting(module, setting, param):
    """
    Checks if a Compass setting exists in the config file.

    :param module   : module name to be checked
    :type module    : string
    :param setting  : compass setting wrapper
    :type setting   : python module
    :param param    : settings defined in compass config file
    :type param     : string

    """
    if hasattr(setting, param):
        return True
    else:
        err_msg = "[%s]Error: no %s defined" % (module, param)
        return err_msg


def get_dist():
    """Returns the operating system related information"""

    os_version, version, release = platform.linux_distribution()
    return (os_version.lower().strip(), version, release.lower().strip())


def check_path(module_name, path):
    """
    Checks if a directory or file exisits.

    :param module_name   : module name to be checked
    :type module_name    : string
    :param path          : path of the directory of file
    :type path           : string

    """
    err_msg = ""
    if not os.path.exists(path):
        err_msg = (
            "[%s]Error: %s does not exsit, "
            "please check your configurations.") % (module_name, path)
    return err_msg


def check_service_running(module_name, service_name):
    """
    Checks if a certain service is running.

    :param module_name  : module name to be checked
    :type module_name   : string
    :param service_name : service name to be checked
    :type service_name  : string

    """
    err_msg = ""
    if not service_name in commands.getoutput('ps -ef'):
        err_msg = "[%s]Error: %s is not running." % (
            module_name, service_name)

    return err_msg


def check_chkconfig(service_name):
    """
    Checks if a service is enabled at the start up.

    :param service_name  : service name to be checked
    :type service_name   : string

    """
    chk_on = False
    for service in os.listdir('/etc/rc3.d/'):
        if service_name in service and 'S' in service:
            chk_on = True
            break

    return chk_on
