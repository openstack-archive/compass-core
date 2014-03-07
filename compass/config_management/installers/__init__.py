# Copyright 2014 Openstack Foundation
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
    get_installer as get_os_installer)
from compass.config_management.installers.os_installer import (
    get_installer_by_name as get_os_installer_by_name)
from compass.config_management.installers.os_installer import (
    register as register_os_installer)
from compass.config_management.installers.package_installer import (
    get_installer as get_package_installer)
from compass.config_management.installers.package_installer import (
    get_installer_by_name as get_package_installer_by_name)
from compass.config_management.installers.package_installer import (
    register as register_package_installer)
from compass.config_management.installers.plugins import chefhandler
from compass.config_management.installers.plugins import cobbler
