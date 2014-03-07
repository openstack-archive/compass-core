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

"""modules to provider providers to read/write cluster/host config

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
__all__ = [
    'db_config_provider', 'file_config_provider', 'mix_config_provider',
    'get_provider', 'get_provider_by_name', 'register_provider',
]


from compass.config_management.providers.config_provider import (
    get_provider)
from compass.config_management.providers.config_provider import (
    get_provider_by_name)
from compass.config_management.providers.config_provider import (
    register_provider)
from compass.config_management.providers.plugins import db_config_provider
from compass.config_management.providers.plugins import file_config_provider
from compass.config_management.providers.plugins import mix_config_provider
