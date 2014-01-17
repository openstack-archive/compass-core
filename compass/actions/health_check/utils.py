import os
import platform
import commands

def validate_setting(module, setting, param):
    if hasattr(setting, param):
       return True
    else:
       return "[%s]Error: no %s defined in /etc/compass/setting" % (module, param)

def check_dist():
    os, version, release = platform.linux_distribution()
    return (os.lower().strip(), version, release.lower().strip())
 
def check_path(module_name, dir):
    err_msg = ""
    if not os.path.exists(dir):
        err_msg = "[%s]Error: %s does not exsit, please check your configurations." %(module_name, dir)
    return err_msg

def check_service_running(module_name, service_name):
    err_msg = ""
    if not service_name in commands.getoutput('ps -ef'):
        err_msg = "[%s]Error: %s is not running." % (module_name, service_name)
    return err_msg

def check_chkconfig(service_name):
    on = False
    for service in os.listdir('/etc/rc3.d/'):
        if service_name in service and 'S' in service:
            on = True
            break
    return on
