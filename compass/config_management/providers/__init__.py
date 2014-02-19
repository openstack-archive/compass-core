"""modules to provider providers to read/write cluster/host config

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
__all__ = [
    'db_config_provider', 'file_config_provider', 'mix_config_provider',
    'get_provider', 'get_provider_by_name', 'register_provider',
]


from compass.config_management.providers.config_provider import (
    get_provider, get_provider_by_name, register_provider)
from compass.config_management.providers.plugins import db_config_provider
from compass.config_management.providers.plugins import file_config_provider
from compass.config_management.providers.plugins import mix_config_provider
