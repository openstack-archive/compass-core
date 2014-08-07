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

__author__ = "Grace Yu (grace.yu@huawei.com)"

"""Module to get configs from provider and isntallers and update
   them to provider and installers.
"""
from compass.deployment.installers.installer import OSInstaller
from compass.deployment.installers.installer import PKInstaller
from compass.deployment.utils import constants as const
from compass.utils import util


import logging


class DeployManager(object):
    """Deploy manager module."""
    def __init__(self, adapter_info, cluster_info, hosts_info):
        os_installer_name = adapter_info[const.OS_INSTALLER][const.NAME]
        pk_installer_name = adapter_info[const.PK_INSTALLER][const.NAME]

        os_hosts_info = self._get_hosts_for_os_installation(hosts_info)

        self.os_installer = DeployManager._get_installer(OSInstaller,
                                                         os_installer_name,
                                                         adapter_info,
                                                         cluster_info,
                                                         os_hosts_info)
        self.pk_installer = DeployManager._get_installer(PKInstaller,
                                                         pk_installer_name,
                                                         adapter_info,
                                                         cluster_info,
                                                         hosts_info)

    @staticmethod
    def _get_installer(installer_type, name, adapter_info, cluster_info,
                       hosts_info):
        """Get installer instance."""
        callback = getattr(installer_type, 'get_installer')
        installer = callback(name, adapter_info, cluster_info, hosts_info)

        return installer

    def clean_progress(self):
        """Clean previous installation log and progress."""
        # Clean DB
        # db_api.cluster.clean_progress(self.cluster_id)
        # db_api.cluster.clean_progress(self.cluster_id, self.host_id_list)

        # OS installer cleans previous installing progress.
        if self.os_installer:
            self.os_installer.clean_progress()

        # Package installer cleans previous installing progress.
        if self.pk_installer:
            self.pk_installer.clean_progress()

    def prepare_for_deploy(self):
        self.clean_progress()

    def deploy(self):
        """Deploy the cluster."""
        deploy_config = {}
        pk_instl_confs = {}
        if self.pk_installer:
            # generate target system config which will be installed by OS
            # installer right after OS installation is completed.
            pk_instl_confs = self.pk_installer.generate_installer_config()
            logging.debug('[DeployManager][deploy] pk_instl_confs is %s',
                          pk_instl_confs)

        if self.os_installer:
            logging.info('[DeployManager][deploy]get OS installer %s',
                         self.os_installer)
            # Send package installer config info to OS installer.
            if pk_instl_confs:
                self.os_installer.set_package_installer_config(pk_instl_confs)

            # start to deploy OS
            try:
                os_deploy_config = self.os_installer.deploy()
                deploy_config['os_config'] = os_deploy_config
            except Exception as ex:
                logging.error(ex.message)

        if self.pk_installer:
            logging.info('DeployManager][deploy]get package installer %s',
                         self.pk_installer)

            pk_deploy_config = self.pk_installer.deploy()
            deploy_config['package_config'] = pk_deploy_config

        return deploy_config

    def redeploy(self):
        """Redeploy the cluster without changing configurations."""
        if self.os_installer:
            self.os_installer.redeploy()

        if self.pk_installer:
            self.pk_installer.redeploy()

    def remove_hosts(self):
        """Remove hosts from both OS and package installlers server side."""
        if self.os_installer:
            self.os_installer.delete_hosts()

        if self.pk_installer:
            self.pk_installer.delete_hosts()

    def _get_hosts_for_os_installation(self, hosts_info):
        """Get info of hosts which need to install/reinstall OS."""
        hosts_list = {}
        for host_id in hosts_info:
            reinstall_os_flag = hosts_info[host_id][const.REINSTALL_OS_FLAG]
            if not reinstall_os_flag:
                continue

            hosts_list[host_id] = hosts_info[host_id]

        return hosts_list


class PowerManager(object):
    """Manage host to power on, power off, and reset."""

    def __init__(self, adapter_info, cluster_info, hosts_info):
        os_installer_name = adapter_info[const.OS_INSTALLER][const.NAME]
        self.os_installer = DeployManager._get_installer(OSInstaller,
                                                         os_installer_name,
                                                         adapter_info,
                                                         cluster_info,
                                                         hosts_info)

    def poweron(self):
        if not self.os_installer:
            logging.info("No OS installer found, cannot power on machine!")
            return
        self.os_installer.poweron()

    def poweroff(self):
        if not self.os_installer:
            logging.info("No OS installer found, cannot power on machine!")
            return
        self.os_installer.poweroff()

    def reset(self):
        if not self.os_installer:
            logging.info("No OS installer found, cannot power on machine!")
            return
        self.os_installer.reset()
