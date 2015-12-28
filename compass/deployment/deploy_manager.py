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
        """Init deploy manager."""
        self.os_installer = None
        self.pk_installer = None

        # Get OS installer
        os_installer_name = adapter_info[const.OS_INSTALLER][const.NAME]
        self.os_installer = DeployManager._get_installer(OSInstaller,
                                                         os_installer_name,
                                                         adapter_info,
                                                         cluster_info,
                                                         hosts_info)

        # Get package installer
        pk_info = adapter_info.setdefault(const.PK_INSTALLER, {})
        if pk_info:
            pk_installer_name = pk_info[const.NAME]
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

    def deploy(self):
        """Deploy the cluster."""
        deployed_config = self.deploy_os()
        package_deployed_config = self.deploy_target_system()

        util.merge_dict(deployed_config, package_deployed_config)

        return deployed_config

    def check_cluster_health(self, callback_url):
        logging.info("DeployManager check_cluster_health...........")
        self.pk_installer.check_cluster_health(callback_url)

    def clean_progress(self):
        """Clean previous installation log and progress."""
        self.clean_os_installtion_progress()
        self.clean_package_installation_progress()

    def clean_os_installtion_progress(self):
        # OS installer cleans previous installing progress.
        if self.os_installer:
            self.os_installer.clean_progress()

    def clean_package_installation_progress(self):
        # Package installer cleans previous installing progress.
        if self.pk_installer:
            self.pk_installer.clean_progress()

    def prepare_for_deploy(self):
        self.clean_progress()

    def deploy_os(self):
        """Deploy OS to hosts which need to in the cluster.

        Return OS deployed config.
        """
        if not self.os_installer:
            return {}

        pk_installer_config = {}
        if self.pk_installer:
            # generate target system config which will be installed by OS
            # installer right after OS installation is completed.
            pk_installer_config = self.pk_installer.generate_installer_config()
            logging.debug('[DeployManager]package installer config is %s',
                          pk_installer_config)

        # Send package installer config info to OS installer.
        self.os_installer.set_package_installer_config(pk_installer_config)

        # start to deploy OS
        return self.os_installer.deploy()

    def deploy_target_system(self):
        """Deploy target system to all hosts in the cluster.

        Return package deployed config.
        """
        if not self.pk_installer:
            return {}

        return self.pk_installer.deploy()

    def redeploy_os(self):
        """Redeploy OS for this cluster without changing configurations."""
        if not self.os_installer:
            logging.info("Redeploy_os: No OS installer found!")
            return

        self.os_installer.redeploy()
        logging.info("Start to redeploy OS for cluster.")

    def redeploy_target_system(self):
        """Redeploy target system for the cluster without changing config."""
        if not self.pk_installer:
            logging.info("Redeploy_target_system: No installer found!")
            return

        self.pk_installer.deploy()
        logging.info("Start to redeploy target system.")

    def redeploy(self):
        """Redeploy the cluster without changing configurations."""
        self.redeploy_os()
        self.redeploy_target_system()

    def remove_hosts(self, package_only=False, delete_cluster=False):
        """Remove hosts from both OS and/or package installlers server side."""
        if self.os_installer and not package_only:
            self.os_installer.delete_hosts()

        if self.pk_installer:
            self.pk_installer.delete_hosts(delete_cluster=delete_cluster)

    def os_installed(self):
        if self.os_installer:
            self.os_installer.ready()
        if self.pk_installer:
            self.pk_installer.os_ready()

    def cluster_os_installed(self):
        if self.os_installer:
            self.os_installer.cluster_ready()
        if self.pk_installer:
            self.pk_installer.cluster_os_ready()

    def package_installed(self):
        if self.pk_installer:
            self.pk_installer.ready()

    def cluster_installed(self):
        if self.pk_installer:
            self.pk_installer.cluster_ready()


class Patcher(DeployManager):
    """Patcher Module."""
    def __init__(self, adapter_info, cluster_info, hosts_info, cluster_hosts):
        self.pk_installer = None
        self.cluster_info = cluster_info
        registered_roles = cluster_info['flavor']['roles']

        pk_info = adapter_info.setdefault(const.PK_INSTALLER, {})
        if pk_info:
            pk_installer_name = pk_info[const.NAME]
            self.pk_installer = Patcher._get_installer(PKInstaller,
                                                       pk_installer_name,
                                                       adapter_info,
                                                       cluster_info,
                                                       hosts_info)

        patched_role_mapping = {}
        for role in registered_roles:
            patched_role_mapping[role] = []
        for host in cluster_hosts:
            if len(host['patched_roles']) == 0:
                continue
            for role in host['patched_roles']:
                patched_role_mapping[role['name']].append(host)
        self.patched_role_mapping = patched_role_mapping

    def patch(self):
        patched_config = self.pk_installer.patch(self.patched_role_mapping)

        return patched_config


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
