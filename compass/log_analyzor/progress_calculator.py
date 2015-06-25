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

"""module to provide updating installing process function.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import logging

from compass.log_analyzor.adapter_matcher import OSMatcher
from compass.log_analyzor.adapter_matcher import PackageMatcher
from compass.log_analyzor.environment import ENV_GLOBALS
from compass.log_analyzor.environment import ENV_LOCALS
from compass.log_analyzor.file_matcher import FileReaderFactory

from compass.utils import setting_wrapper as setting
from compass.utils import util

OS_ADAPTER_CONFIGURATIONS = None
PACKAGE_ADAPTER_CONFIGURATIONS = None
PROGRESS_CALCULATOR_CONFIGURATIONS = None


def _load_calculator_configurations(force=False):
    global PROGRESS_CALCULATOR_CONFIGURATIONS
    if force or PROGRESS_CALCULATOR_CONFIGURATIONS is None:
        env_locals = {}
        env_locals.update(ENV_GLOBALS)
        env_locals.update(ENV_LOCALS)
        PROGRESS_CALCULATOR_CONFIGURATIONS = util.load_configs(
            setting.PROGRESS_CALCULATOR_DIR,
            env_locals=env_locals
        )
        if not PROGRESS_CALCULATOR_CONFIGURATIONS:
            logging.info('No configuration found for progress calculator.')

    global OS_ADAPTER_CONFIGURATIONS
    if force or OS_ADAPTER_CONFIGURATIONS is None:
        OS_ADAPTER_CONFIGURATIONS = []
        for progress_calculator_configuration in (
            PROGRESS_CALCULATOR_CONFIGURATIONS
        ):
            if 'OS_LOG_CONFIGURATIONS' in (
                progress_calculator_configuration
            ):
                os_installer_configurations = (
                    progress_calculator_configuration['OS_LOG_CONFIGURATIONS']
                )
                for os_installer_configuration in os_installer_configurations:
                    OS_ADAPTER_CONFIGURATIONS.append(OSMatcher(
                        os_installer_name=(
                            os_installer_configuration['os_installer_name']
                        ),
                        os_pattern=os_installer_configuration['os_pattern'],
                        item_matcher=(
                            os_installer_configuration['item_matcher']
                        ),
                        file_reader_factory=FileReaderFactory(
                            os_installer_configuration['logdir']
                        )
                    ))
        if not OS_ADAPTER_CONFIGURATIONS:
            logging.info(
                'no OS_LOG_CONFIGURATIONS section found '
                'in progress calculator.'
            )
        else:
            logging.debug(
                'OS_ADAPTER_CONFIGURATIONS is\n%s',
                OS_ADAPTER_CONFIGURATIONS
            )

    global PACKAGE_ADAPTER_CONFIGURATIONS
    if force or PACKAGE_ADAPTER_CONFIGURATIONS is None:
        PACKAGE_ADAPTER_CONFIGURATIONS = []
        for progress_calculator_configuration in (
            PROGRESS_CALCULATOR_CONFIGURATIONS
        ):
            if 'ADAPTER_LOG_CONFIGURATIONS' in (
                progress_calculator_configuration
            ):
                package_installer_configurations = (
                    progress_calculator_configuration[
                        'ADAPTER_LOG_CONFIGURATIONS'
                    ]
                )
                for package_installer_configuration in (
                    package_installer_configurations
                ):
                    PACKAGE_ADAPTER_CONFIGURATIONS.append(PackageMatcher(
                        package_installer_name=(
                            package_installer_configuration[
                                'package_installer_name'
                            ]
                        ),
                        adapter_pattern=(
                            package_installer_configuration['adapter_pattern']
                        ),
                        item_matcher=(
                            package_installer_configuration['item_matcher']
                        ),
                        file_reader_factory=FileReaderFactory(
                            package_installer_configuration['logdir']
                        )
                    ))
        if not PACKAGE_ADAPTER_CONFIGURATIONS:
            logging.info(
                'no PACKAGE_LOG_CONFIGURATIONS section found '
                'in progress calculator.'
            )
        else:
            logging.debug(
                'PACKAGE_ADAPTER_CONFIGURATIONS is\n%s',
                PACKAGE_ADAPTER_CONFIGURATIONS
            )


def load_calculator_configurations(force_reload=False):
    _load_calculator_configurations(force=force_reload)


def _get_os_matcher(os_installer_name, os_name):
    """Get OS adapter matcher by os name and installer name."""
    _load_calculator_configurations()
    for configuration in OS_ADAPTER_CONFIGURATIONS:
        if configuration.match(os_installer_name, os_name):
            return configuration
        else:
            logging.debug('configuration %s does not match %s and %s',
                          configuration, os_name, os_installer_name)
    logging.error('No configuration found for os installer %s os %s',
                  os_installer_name, os_name)
    return None


def _get_package_matcher(
    package_installer_name, adapter_name
):
    """Get package adapter matcher by adapter name and installer name."""
    _load_calculator_configurations()
    for configuration in PACKAGE_ADAPTER_CONFIGURATIONS:
        if configuration.match(
            package_installer_name,
            adapter_name
        ):
            return configuration
        else:
            logging.debug('configuration %s does not match %s and %s',
                          configuration, adapter_name,
                          package_installer_name)
    logging.error('No configuration found for package installer %s adapter %s',
                  package_installer_name, adapter_name)
    return None


def update_host_progress(host_mappping):
    for host_id, (host, host_state, host_log_history_mapping) in (
        host_mappping.items()
    ):
        os_name = host['os_name']
        os_installer_name = host['os_installer']['name']
        os_matcher = _get_os_matcher(
            os_installer_name, os_name
        )
        if not os_matcher:
            continue
        name = host[setting.HOST_INSTALLATION_LOGDIR_NAME]
        os_matcher.update_progress(
            name, host_state, host_log_history_mapping
        )


def update_clusterhost_progress(clusterhost_mapping):
    for (
        clusterhost_id,
        (clusterhost, clusterhost_state, clusterhost_log_history_mapping)
    ) in (
        clusterhost_mapping.items()
    ):
        adapter_name = clusterhost['adapter_name']
        package_installer_name = clusterhost['package_installer']['name']
        package_matcher = _get_package_matcher(
            package_installer_name,
            adapter_name
        )
        if not package_matcher:
            continue
        name = clusterhost[setting.CLUSTERHOST_INATALLATION_LOGDIR_NAME]
        package_matcher.update_progress(
            name, clusterhost_state,
            clusterhost_log_history_mapping
        )


def update_cluster_progress(cluster_mapping):
    for cluster_id, (cluster, cluster_state) in cluster_mapping.items():
        pass
