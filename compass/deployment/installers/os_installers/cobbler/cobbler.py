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

"""os installer cobbler plugin.
"""
import logging
import os
import shutil
import xmlrpclib

from compass.deployment.installers.installer import OSInstaller
from compass.deployment.utils import constants as const
from compass.utils import setting_wrapper as compass_setting
from compass.utils import util
from copy import deepcopy


NAME = 'CobblerInstaller'


class CobblerInstaller(OSInstaller):
    """cobbler installer"""
    CREDENTIALS = "credentials"
    USERNAME = 'username'
    PASSWORD = 'password'

    INSTALLER_URL = "cobbler_url"
    TMPL_DIR = 'tmpl_dir'
    SYS_TMPL = 'system.tmpl'
    SYS_TMPL_NAME = 'system.tmpl'
    SYS_PROFILE_NAME = 'profile.tmpl'
    PROFILE = 'profile'

    POWER_TYPE = 'power_type'
    POWER_ADDR = 'power_address'
    POWER_USER = 'power_user'
    POWER_PASS = 'power_pass'

    def __init__(self, config_manager):
        super(CobblerInstaller, self).__init__()

        self.config_manager = config_manager
        installer_settings = self.config_manager.get_os_installer_settings()
        try:
            username = installer_settings[self.CREDENTIALS][self.USERNAME]
            password = installer_settings[self.CREDENTIALS][self.PASSWORD]
            cobbler_url = installer_settings[self.INSTALLER_URL]
            self.tmpl_dir = CobblerInstaller.get_tmpl_path()

        except KeyError as ex:
            raise KeyError(ex.message)

        # The connection is created when cobbler installer is initialized.
        self.remote = self._get_cobbler_server(cobbler_url)
        self.token = self._get_token(username, password)
        self.pk_installer_config = None

        logging.debug('%s instance created', 'CobblerInstaller')

    @classmethod
    def get_tmpl_path(cls):
        return os.path.join(compass_setting.TMPL_DIR, 'cobbler')

    def __repr__(self):
        return '%r[remote=%r,token=%r' % (
            self.__class__.__name__, self.remote, self.token)

    def _get_cobbler_server(self, cobbler_url):
        if not cobbler_url:
            logging.error("Cobbler URL is None!")
            raise Exception("Cobbler URL cannot be None!")

        return xmlrpclib.Server(cobbler_url)

    def _get_token(self, username, password):
        if self.remote is None:
            raise Exception("Cobbler remote instance is None!")
        return self.remote.login(username, password)

    def get_supported_oses(self):
        """get supported os versions.

        note::
        In cobbler, we treat profile name as the indicator
        of os version. It is just a simple indicator
        and not accurate.
        """
        profiles = self.remote.get_profiles()
        oses = []
        for profile in profiles:
            oses.append(profile['name'])
        return oses

    def deploy(self):
        """Sync cobbler to catch up the latest update config and start to

        install OS. Return both cluster and hosts deploy configs. The return
        format:
        {
            "cluster": {
                "id": 1,
                "deployed_os_config": {},
            },
            "hosts": {
                 1($clusterhost_id): {
                      "deployed_os_config": {...},
                 },
                 ....
            }
        }
        """
        host_ids = self.config_manager.get_hosts_id_list_for_os_installation()
        if not host_ids:
            # No hosts need to install OS
            logging.info("Cobbler: No host needs to install OS.")
            return {}

        os_version = self.config_manager.get_os_version()
        profile = self._get_profile_from_server(os_version)

        global_vars_dict = self._get_cluster_tmpl_vars_dict()

        self.update_profile_config_to_cobbler(profile, global_vars_dict)

        hosts_deploy_config = {}

        for host_id in host_ids:
            hostname = self.config_manager.get_hostname(host_id)
            vars_dict = self._get_host_tmpl_vars_dict(host_id,
                                                      global_vars_dict,
                                                      hostname=hostname,
                                                      profile=profile)

            self.update_host_config_to_cobbler(host_id, hostname, vars_dict)

            # set host deploy config
            host_config = {}
            host_config[const.DEPLOYED_OS_CONFIG] = vars_dict[const.OS_CONFIG]
            hosts_deploy_config[host_id] = host_config

        # sync to cobbler and trigger installtion.
        self._sync()

        cluster_config = global_vars_dict.setdefault(const.OS_CONFIG, {})

        return {
            const.CLUSTER: {
                const.ID: self.config_manager.get_cluster_id(),
                const.DEPLOYED_OS_CONFIG: cluster_config
            },
            const.HOSTS: hosts_deploy_config
        }

    def clean_progress(self):
        """clean log files and config for hosts which to deploy."""
        clusterhost_list = self.config_manager.get_host_id_list()
        log_dir_prefix = compass_setting.INSTALLATION_LOGDIR[NAME]

        for host_id in clusterhost_list:
            hostname = self.config_manager.get_hostname(host_id)
            self._clean_log(log_dir_prefix, hostname)

    def redeploy(self):
        """redeploy hosts."""
        host_ids = self.config_manager.get_host_id_list()
        if not host_ids:
            logging.info("Cobbler: hostlist is None, no host is redeployed")
            return
        for host_id in host_ids:
            hostname = self.config_manager.get_hostname(host_id)
            sys_id = self._get_create_system(hostname)
            if sys_id:
                # enable netboot for this host
                self._netboot_enabled(sys_id)

        self._sync()

    def set_package_installer_config(self, package_configs):
        """Cobbler can install and configure package installer right after

        OS installation compelets by setting package_config info provided
        by package installer.

        :param dict package_configs: The dict of config generated by package
                                     installer for each clusterhost. The IDs
                                     of clusterhosts are the keys of
                                     package_configs.
        """
        self.pk_installer_config = package_configs

    def _sync(self):
        """Sync the updated config to cobbler and trigger installation."""
        try:
            self.remote.sync(self.token)
            os.system('sudo service rsyslog restart')
        except Exception as ex:
            logging.debug("Failed to sync cobbler server! Error: %s" % ex)
            raise ex

    def dump_system_info(self, host_id):

        hostname = self.config_manager.get_hostname(host_id)
        if self.remote is None or not hostname:
            logging.info("[dump_system_info]Remote or hostname is None.")
            return {}

        return self.remote.get_system_as_rendered(hostname)

    def _generate_system_config(self, host_id, host_vars_dict):
        """Generate updated system config from the template.

           :param host_vars_dict: dict of variables for the system template to
                                  generate system config dict for each host.
        """
        os_version = self.config_manager.get_os_version()

        tmpl_path = os.path.join(
            os.path.join(self.tmpl_dir, os_version), self.SYS_TMPL_NAME
        )
        if not os.path.exists(tmpl_path):
            err_msg = "Template '%s' does not exists!" % tmpl_path
            logging.error(err_msg)
            raise Exception(err_msg)

        system_config = self.get_config_from_template(tmpl_path,
                                                      host_vars_dict)

        # update package config info to cobbler ksmeta
        if self.pk_installer_config and host_id in self.pk_installer_config:
            pk_config = self.pk_installer_config[host_id]
            ksmeta = system_config.setdefault("ksmeta", {})
            util.merge_dict(ksmeta, pk_config)
            system_config["ksmeta"] = ksmeta

        return system_config

    def _generate_profile_config(self, cluster_vars_dict):
        os_version = self.config_manager.get_os_version()
        tmpl_path = os.path.join(
            os.path.join(self.tmpl_dir, os_version), self.SYS_PROFILE_NAME
        )

        return self.get_config_from_template(tmpl_path, cluster_vars_dict)

    def _get_profile_from_server(self, os_version):
        """Get profile from cobbler server."""
        result = self.remote.find_profile({'name': os_version})
        if not result:
            raise Exception("Cannot find profile for '%s'", os_version)

        profile = result[0]
        return profile

    def _get_create_system(self, hostname):
        """get system reference id for the host."""
        sys_name = hostname
        sys_id = None
        system_info = self.remote.find_system({"name": hostname})

        if not system_info:
            # Create a new system
            sys_id = self.remote.new_system(self.token)
            self.remote.modify_system(sys_id, "name", hostname, self.token)
            logging.debug('create new system %s for %s', sys_id, sys_name)
        else:
            sys_id = self.remote.get_system_handle(sys_name, self.token)

        return sys_id

    def _get_profile_id(self, profilename):
        """get profile reference id for the cluster."""
        return self.remote.get_profile_handle(profilename, self.token)

    def _clean_system(self, hostname):
        """clean system."""
        sys_name = hostname
        try:
            self.remote.remove_system(sys_name, self.token)
            logging.debug('system %s is removed', sys_name)
        except Exception:
            logging.debug('no system %s found to remove', sys_name)

    def _update_system_config(self, sys_id, system_config):
        """update modify system."""
        for key, value in system_config.iteritems():
            self.remote.modify_system(sys_id, str(key), value, self.token)

        self.remote.save_system(sys_id, self.token)

    def _update_profile_config(self, profile_id, profile_config):
        for key, value in profile_config.iteritems():
            self.remote.modify_profile(profile_id, str(key), value, self.token)

        self.remote.save_profile(profile_id, self.token)

    def _netboot_enabled(self, sys_id):
        """enable netboot."""
        self.remote.modify_system(sys_id, 'netboot_enabled', True, self.token)
        self.remote.save_system(sys_id, self.token)

    def _clean_log(self, log_dir_prefix, system_name):
        """clean log."""
        log_dir = os.path.join(log_dir_prefix, system_name)
        shutil.rmtree(log_dir, True)

    def update_host_config_to_cobbler(self, host_id, hostname, host_vars_dict):
        """update host config and upload to cobbler server."""
        sys_id = self._get_create_system(hostname)

        system_config = self._generate_system_config(host_id, host_vars_dict)
        logging.debug('%s system config to update: %s', host_id, system_config)

        self._update_system_config(sys_id, system_config)
        self._netboot_enabled(sys_id)

    def update_profile_config_to_cobbler(self, profilename, cluster_vars_dict):
        """update profile config and upload to cobbler server."""

        profile_id = self._get_profile_id(profilename)

        profile_config = self._generate_profile_config(cluster_vars_dict)
        logging.debug(
            '%s profile config to update: %s', profilename, profile_config
        )

        self._update_profile_config(profile_id, profile_config)

    def delete_hosts(self):
        hosts_id_list = self.config_manager.get_host_id_list()
        logging.debug('delete hosts %s', hosts_id_list)
        for host_id in hosts_id_list:
            self.delete_single_host(host_id)
        self._sync()

    def delete_single_host(self, host_id):
        """Delete the host from cobbler server and clean up the installation

        progress.
        """
        hostname = self.config_manager.get_hostname(host_id)
        try:
            log_dir_prefix = compass_setting.INSTALLATION_LOGDIR[NAME]
            self._clean_system(hostname)
            self._clean_log(log_dir_prefix, hostname)
        except Exception as ex:
            logging.error("Deleting host got exception: %s", ex)
            logging.exception(ex)

    def _get_host_tmpl_vars_dict(self, host_id, global_vars_dict, **kwargs):
        """Generate template variables dictionary."""
        vars_dict = {}
        if global_vars_dict:
            # Set cluster template vars_dict from cluster os_config.
            vars_dict = deepcopy(global_vars_dict)

        # Set hostname, MAC address and hostname, networks, dns and so on.
        host_baseinfo = self.config_manager.get_host_baseinfo(host_id)
        vars_dict[const.BASEINFO] = host_baseinfo

        # Set profile
        if self.PROFILE in kwargs:
            profile = kwargs[self.PROFILE]
        else:
            os_version = self.config_manager.get_os_version()
            profile = self._get_profile_from_server(os_version)

        vars_dict[const.BASEINFO][self.PROFILE] = profile

        metadata = self.config_manager.get_os_config_metadata()
        os_config = self.config_manager.get_host_os_config(host_id)

        # Get template variables values from host os_config
        host_vars_dict = self.get_tmpl_vars_from_metadata(metadata, os_config)
        util.merge_dict(
            vars_dict.setdefault(const.OS_CONFIG, {}), host_vars_dict
        )
        return vars_dict

    def _get_cluster_tmpl_vars_dict(self):
        metadata = self.config_manager.get_os_config_metadata()
        os_config = self.config_manager.get_cluster_os_config()

        cluster_vas_dict = {}
        cluster_vas_dict[const.OS_CONFIG] = \
            self.get_tmpl_vars_from_metadata(metadata, os_config)

        return cluster_vas_dict

    def _check_and_set_system_impi(self, host_id, sys_id):
        if not sys_id:
            logging.info("System is None!")
            return False

        system = self.dump_system_info(host_id)
        if system[self.POWER_TYPE] != 'ipmilan' or not system[self.POWER_USER]:
            # Set sytem power type to ipmilan if needs and set IPMI info
            ipmi_info = self.config_manager.get_host_ipmi_info(host_id)
            if not ipmi_info:
                logging.info('No IPMI information found! Failed power on.')
                return False

            ipmi_ip, ipmi_user, ipmi_pass = ipmi_info
            power_opts = {}
            power_opts[self.POWER_TYPE] = 'ipmilan'
            power_opts[self.POWER_ADDR] = ipmi_ip
            power_opts[self.POWER_USER] = ipmi_user
            power_opts[self.POWER_PASS] = ipmi_pass

            self._update_system_config(sys_id, power_opts)

        return True

    def poweron(self, host_id):
        hostname = self.config_manager.get_hostname(host_id)
        sys_id = self._get_create_system(hostname)
        if not self._check_and_set_system_impi(sys_id):
            return

        self.remote.power_system(sys_id, self.token, power='on')
        logging.info("Host with ID=%d starts to power on!" % host_id)

    def poweroff(self, host_id):
        hostname = self.config_manager.get_hostname(host_id)
        sys_id = self._get_create_system(hostname)
        if not self._check_and_set_system_impi(sys_id):
            return

        self.remote.power_system(sys_id, self.token, power='off')
        logging.info("Host with ID=%d starts to power off!" % host_id)

    def reset(self, host_id):
        hostname = self.config_manager.get_hostname(host_id)
        sys_id = self._get_create_system(hostname)
        if not self._check_and_set_system_impi(sys_id):
            return

        self.remote.power_system(sys_id, self.token, power='reboot')
        logging.info("Host with ID=%d starts to reboot!" % host_id)
