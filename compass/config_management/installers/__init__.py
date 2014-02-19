"""modules to read/write cluster/host config from installers.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
__all__ = [
    'chefhandler', 'cobbler',
    'get_os_installer_by_name',
    'get_os_installer',
    'register_os_installer',
    'get_package_installer_by_name',
    'get_package_installer',
    'register_package_installer',
]


from compass.config_management.installers.os_installer import (
    get_installer_by_name as get_os_installer_by_name,
    get_installer as get_os_installer,
    register as register_os_installer)
from compass.config_management.installers.package_installer import (
    get_installer_by_name as get_package_installer_by_name,
    get_installer as get_package_installer,
    register as register_package_installer)
from compass.config_management.installers.plugins import chefhandler
from compass.config_management.installers.plugins import cobbler
