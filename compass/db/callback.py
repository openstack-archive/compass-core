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

"""Metadata Callback methods."""
import logging
import netaddr
import random
import re
import socket

from compass.db import exception
from compass.utils import setting_wrapper as setting
from compass.utils import util


CALLBACK_GLOBALS = globals()
CALLBACK_LOCALS = locals()
CALLBACK_CONFIGS = util.load_configs(
    setting.CALLBACK_DIR,
    config_name_suffix='.py',
    env_globals=CALLBACK_GLOBALS,
    env_locals=CALLBACK_LOCALS
)
for callback_config in CALLBACK_CONFIGS:
    CALLBACK_LOCALS.update(callback_config)


def default_proxy(name, **kwargs):
    return setting.COMPASS_SUPPORTED_PROXY


def proxy_options(name, **kwargs):
    return [setting.COMPASS_SUPPORTED_PROXY]


def default_noproxy(name, **kwargs):
    return setting.COMPASS_SUPPORTED_DEFAULT_NOPROXY


def noproxy_options(name, **kwargs):
    return setting.COMPASS_SUPPORTED_DEFAULT_NOPROXY


def default_ntp_server(name, **kwargs):
    return setting.COMPASS_SUPPORTED_NTP_SERVER


def ntp_server_options(name, **kwargs):
    return setting.COMPASS_SUPPORTED_NTP_SERVER


def default_dns_servers(name, **kwargs):
    return setting.COMPASS_SUPPORTED_DNS_SERVERS


def dns_servers_options(name, **kwargs):
    return setting.COMPASS_SUPPORTED_DNS_SERVERS


def default_domain(name, **kwargs):
    if setting.COMPASS_SUPPORTED_DOMAINS:
        return setting.COMPASS_SUPPORTED_DOMAINS[0]
    else:
        return None


def domain_options(name, **kwargs):
    return setting.COMPASS_SUPPORTED_DOMAINS


def default_search_path(name, **kwargs):
    return setting.COMPASS_SUPPORTED_DOMAINS


def search_path_options(name, **kwargs):
    return setting.COMPASS_SUPPORTED_DOMAINS


def default_gateway(name, **kwargs):
    return setting.COMPASS_SUPPORTED_DEFAULT_GATEWAY


def default_gateway_options(name, **kwargs):
    return [setting.COMPASS_SUPPORTED_DEFAULT_GATEWAY]


def default_localrepo(name, **kwargs):
    return setting.COMPASS_SUPPORTED_LOCAL_REPO


def default_localrepo_options(name, **kwargs):
    return [setting.COMPASS_SUPPORTED_LOCAL_REPO]


def autofill_callback_default(name, config, **kwargs):
    if config is None:
        if (
            'autofill_types' not in kwargs or
            not (set(kwargs['autofill_types']) & set(kwargs))
        ):
            return None
        if 'default_value' not in kwargs:
            return None
        return kwargs['default_value']
    return config


def autofill_callback_random_option(name, config, **kwargs):
    if config is None:
        if (
            'autofill_types' not in kwargs or
            not (set(kwargs['autofill_types']) & set(kwargs))
        ):
            return None
        if 'options' not in kwargs or not kwargs['options']:
            return None
        return random.choice(kwargs['options'])
    return config


def autofill_no_proxy(name, config, **kwargs):
    logging.debug(
        'autofill %s config %s by params %s',
        name, config, kwargs
    )
    if 'cluster' in kwargs:
        if config is None:
            config = []
        if 'default_value' in kwargs:
            for default_no_proxy in kwargs['default_value']:
                if default_no_proxy and default_no_proxy not in config:
                    config.append(default_no_proxy)
        cluster = kwargs['cluster']
        for clusterhost in cluster.clusterhosts:
            host = clusterhost.host
            hostname = host.name
            if hostname not in config:
                config.append(hostname)
            for host_network in host.host_networks:
                if host_network.is_mgmt:
                    ip = host_network.ip
                    if ip not in config:
                        config.append(ip)
    if not config:
        return config
    return [no_proxy for no_proxy in config if no_proxy]


def autofill_network_mapping(name, config, **kwargs):
    logging.debug(
        'autofill %s config %s by params %s',
        name, config, kwargs
    )
    if not config:
        return config
    if isinstance(config, basestring):
        config = {
            'interface': config,
            'subnet': None
        }
    if not isinstance(config, dict):
        return config
    if 'interface' not in config:
        return config
    subnet = None
    interface = config['interface']
    if 'cluster' in kwargs:
        cluster = kwargs['cluster']
        for clusterhost in cluster.clusterhosts:
            host = clusterhost.host
            for host_network in host.host_networks:
                if host_network.interface == interface:
                    subnet = host_network.subnet.subnet
    elif 'clusterhost' in kwargs:
        clusterhost = kwargs['clusterhost']
        host = clusterhost.host
        for host_network in host.host_networks:
            if host_network.interface == interface:
                subnet = host_network.subnet.subnet
    if not subnet:
        raise exception.InvalidParameter(
            'interface %s not found in host(s)' % interface
        )
    if 'subnet' not in config or not config['subnet']:
        config['subnet'] = subnet
    else:
        if config['subnet'] != subnet:
            raise exception.InvalidParameter(
                'subnet %s in config is not equal to subnet %s in hosts' % (
                    config['subnet'], subnet
                )
            )
    return config
