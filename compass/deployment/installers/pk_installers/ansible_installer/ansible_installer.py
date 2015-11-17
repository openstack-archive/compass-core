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

__auther__ = "Compass Dev Team (dev-team@syscompass.org)"

"""package installer: ansible plugin."""

from Cheetah.Template import Template
from copy import deepcopy
import json
import logging
import os
import re
import shutil
import subprocess

from compass.deployment.installers.installer import PKInstaller
from compass.deployment.utils import constants as const
from compass.utils import setting_wrapper as compass_setting
from compass.utils import util

NAME = "AnsibleInstaller"

def byteify(input):
    if isinstance(input, dict):
        return dict([(byteify(key),byteify(value)) for key,value in input.iteritems()])
    elif isinstance(input, list):
        return [byteify(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input

class AnsibleInstaller(PKInstaller):
    INVENTORY_TMPL_DIR = 'inventories'
    GROUPVARS_TMPL_DIR = 'vars'

    # keywords in package installer settings
    ANSIBLE_DIR = 'ansible_dir'
    ANSIBLE_RUN_DIR = 'ansible_run_dir'
    LOG_FILE = 'ansible_log_file'
    ANSIBLE_CONFIG = 'ansible_config'
    INVENTORY = 'inventory_file'
    GROUP_VARIABLE = 'group_variable'
    HOSTS_PATH = 'etc_hosts_path'
    RUNNER_DIRS = 'runner_dirs'

    def __init__(self, config_manager):
        super(AnsibleInstaller, self).__init__()

        self.config_manager = config_manager
        self.tmpl_name = self.config_manager.get_cluster_flavor_template()
        self.installer_settings = (
            self.config_manager.get_pk_installer_settings()
        )
        settings = self.installer_settings
        self.ansible_dir = settings.setdefault(self.ANSIBLE_DIR, None)
        self.ansible_run_dir = (
            settings.setdefault(self.ANSIBLE_RUN_DIR, None)
        )
        self.log_file = settings.setdefault(self.LOG_FILE, None)
        self.ansible_config = (
            settings.setdefault(self.ANSIBLE_CONFIG, None)
        )
        self.inventory = settings.setdefault(self.INVENTORY, None)
        self.group_variable = (
            settings.setdefault(self.GROUP_VARIABLE, None)
        )
        self.hosts_path = (
            settings.setdefault(self.HOSTS_PATH, None)
        )
        self.runner_dirs = (
            settings.setdefault(self.RUNNER_DIRS, None)
        )
        self.playbook = self.tmpl_name.replace('tmpl', 'yml')
        self.runner_files = [self.playbook]

        adapter_name = self.config_manager.get_dist_system_name()
        self.tmpl_dir = AnsibleInstaller.get_tmpl_path(adapter_name)
        self.adapter_dir = os.path.join(self.ansible_dir, adapter_name)
        logging.debug('%s instance created', self)

    @classmethod
    def get_tmpl_path(cls, adapter_name):
        tmpl_path = os.path.join(
            os.path.join(compass_setting.TMPL_DIR, 'ansible_installer'),
            adapter_name
        )
        return tmpl_path

    def __repr__(self):
        return '%s[name=%s,installer_url=%s]' % (
            self.__class__.__name__, self.NAME, self.installer_url)

    def generate_installer_config(self):
        """Render ansible config file by OS installing.

        The output format:
        {
           '1'($host_id/clusterhost_id):{
               'tool': 'ansible',
           },
           .....
        }
        """
        host_ids = self.config_manager.get_host_id_list()
        os_installer_configs = {}
        for host_id in host_ids:
            temp = {
                "tool": "ansible",
            }
            os_installer_configs[host_id] = temp

        return os_installer_configs

    def get_env_name(self, dist_sys_name, cluster_name):
        return "-".join((dist_sys_name, cluster_name))

    def _get_cluster_tmpl_vars(self):
        """Generate template variables dict

        Generates based on cluster level config.
        The vars_dict will be:
        {
            "baseinfo": {
                "id":1,
                "name": "cluster01",
                ...
            },
            "package_config": {
                .... //mapped from original package config based on metadata
            },
            "role_mapping": {
                ....
            }
        }
        """
        cluster_vars_dict = {}
        # set cluster basic information to vars_dict
        cluster_baseinfo = self.config_manager.get_cluster_baseinfo()
        cluster_vars_dict[const.BASEINFO] = cluster_baseinfo

        # get and set template variables from cluster package config.
        pk_metadata = self.config_manager.get_pk_config_meatadata()
        pk_config = self.config_manager.get_cluster_package_config()

        # get os config as ansible needs them
        os_metadata = self.config_manager.get_os_config_metadata()
        os_config = self.config_manager.get_cluster_os_config()

        pk_meta_dict = self.get_tmpl_vars_from_metadata(pk_metadata, pk_config)
        os_meta_dict = self.get_tmpl_vars_from_metadata(os_metadata, os_config)
        util.merge_dict(pk_meta_dict, os_meta_dict)

        cluster_vars_dict[const.PK_CONFIG] = pk_meta_dict

        # get and set roles_mapping to vars_dict
        mapping = self.config_manager.get_cluster_roles_mapping()
        logging.info("cluster role mapping is %s", mapping)
        cluster_vars_dict[const.ROLES_MAPPING] = mapping

        # get ip settings to vars_dict
        hosts_ip_settings = self.config_manager.get_hosts_ip_settings(
                pk_meta_dict["network_cfg"]["ip_settings"],
                pk_meta_dict["network_cfg"]["sys_intf_mappings"])
        logging.info("hosts_ip_settings is %s", hosts_ip_settings)
        cluster_vars_dict["ip_settings"] = hosts_ip_settings

        return byteify(cluster_vars_dict)

    def _generate_inventory_attributes(self, global_vars_dict):
        inventory_tmpl_path = os.path.join(
            os.path.join(self.tmpl_dir, self.INVENTORY_TMPL_DIR),
            self.tmpl_name
        )
        if not os.path.exists(inventory_tmpl_path):
            logging.error(
                "Inventory template '%s' does not exist", self.tmpl_name
            )
            raise Exception("Template '%s' does not exist!" % self.tmpl_name)

        return self.get_config_from_template(
            inventory_tmpl_path, global_vars_dict
        )

    def _generate_group_vars_attributes(self, global_vars_dict):
        logging.info("global vars dict is %s", global_vars_dict)
        group_vars_tmpl_path = os.path.join(
            os.path.join(self.tmpl_dir, self.GROUPVARS_TMPL_DIR),
            self.tmpl_name
        )
        if not os.path.exists(group_vars_tmpl_path):
            logging.error("Vars template '%s' does not exist",
                          self.tmpl_name)
            raise Exception("Template '%s' does not exist!" % self.tmpl_name)

        return self.get_config_from_template(
            group_vars_tmpl_path, global_vars_dict
        )

    def _generate_hosts_attributes(self, global_vars_dict):
        hosts_tmpl_path = os.path.join(
            os.path.join(self.tmpl_dir, 'hosts'), self.tmpl_name
        )
        if not os.path.exists(hosts_tmpl_path):
            logging.error("Hosts template '%s' does not exist", self.tmpl_name)
            raise Exception("Template '%s' does not exist!" % self.tmpl_name)

        return self.get_config_from_template(hosts_tmpl_path, global_vars_dict)

    def _generate_ansible_cfg_attributes(self, global_vars_dict):
        ansible_cfg_tmpl_path = os.path.join(
            os.path.join(self.tmpl_dir, 'ansible_cfg'), self.tmpl_name
        )
        if not os.path.exists(ansible_cfg_tmpl_path):
            logging.error("cfg template '%s' does not exist", self.tmpl_name)
            raise Exception("Template '%s' does not exist!" % self.tmpl_name)

        return self.get_config_from_template(
            ansible_cfg_tmpl_path,
            global_vars_dict
        )

    def get_config_from_template(self, tmpl_path, vars_dict):
        logging.debug("vars_dict is %s", vars_dict)

        if not os.path.exists(tmpl_path) or not vars_dict:
            logging.info("Template dir or vars_dict is None!")
            return {}

        searchList = []
        copy_vars_dict = deepcopy(vars_dict)
        for key, value in vars_dict.iteritems():
            if isinstance(value, dict):
                temp = copy_vars_dict[key]
                del copy_vars_dict[key]
                searchList.append(temp)
        searchList.append(copy_vars_dict)

        # Load specific template for current adapter
        tmpl = Template(file=tmpl_path, searchList=searchList)
        return tmpl.respond()

    def _create_ansible_run_env(self, env_name):
        ansible_run_destination = os.path.join(self.ansible_run_dir, env_name)
        os.mkdir(ansible_run_destination)

        # copy roles to run env
        dirs = self.runner_dirs
        files = self.runner_files
        for dir in dirs:
            items = dir.split(':')
            src, dst = items[0], items[-1]
            if not os.path.exists(os.path.join(self.ansible_dir, src)):
               continue

            shutil.copytree(
                os.path.join(self.ansible_dir, src),
                os.path.join(
                    ansible_run_destination,
                    dst
                )
            )
        for file in files:
            logging.info('file is %s', file)
            shutil.copy(
                os.path.join(self.adapter_dir, file),
                os.path.join(
                    ansible_run_destination,
                    file
                )
            )

    def prepare_ansible(self, env_name, global_vars_dict):
        ansible_run_destination = os.path.join(self.ansible_run_dir, env_name)
        self._create_ansible_run_env(env_name)
        inv_config = self._generate_inventory_attributes(global_vars_dict)
        inventory_dir = os.path.join(ansible_run_destination, 'inventories')

        vars_config = self._generate_group_vars_attributes(global_vars_dict)
        vars_dir = os.path.join(ansible_run_destination, 'group_vars')

        hosts_config = self._generate_hosts_attributes(global_vars_dict)
        hosts_destination = os.path.join(
            ansible_run_destination, self.hosts_path
        )

        cfg_config = self._generate_ansible_cfg_attributes(global_vars_dict)
        cfg_destination = os.path.join(
            ansible_run_destination,
            self.ansible_config
        )

        os.mkdir(inventory_dir)
        os.mkdir(vars_dir)

        inventory_destination = os.path.join(inventory_dir, self.inventory)
        group_vars_destination = os.path.join(vars_dir, self.group_variable)
        self.serialize_config(inv_config, inventory_destination)
        self.serialize_config(vars_config, group_vars_destination)
        self.serialize_config(hosts_config, hosts_destination)
        self.serialize_config(cfg_config, cfg_destination)

    def deploy(self):
        """Start to deploy a distributed system.

        Return both cluster and hosts deployed configs.
        The return format:
        {
            "cluster": {
                "id": 1,
                "deployed_package_config": {
                    "roles_mapping": {...},
                    "service_credentials": {...},
                    ....
                }
            },
            "hosts": {
                1($clusterhost_id): {
                    "deployed_package_config": {...}
                },
                ....
            }
        }
        """
        host_list = self.config_manager.get_host_id_list()
        if not host_list:
            return {}

        adapter_name = self.config_manager.get_adapter_name()
        cluster_name = self.config_manager.get_clustername()
        env_name = self.get_env_name(adapter_name, cluster_name)

        global_vars_dict = self._get_cluster_tmpl_vars()
        logging.info(
            '%s var dict: %s', self.__class__.__name__, global_vars_dict
        )
        # Create ansible related files
        self.prepare_ansible(env_name, global_vars_dict)

    def cluster_os_ready(self):
        adapter_name = self.config_manager.get_adapter_name()
        cluster_name = self.config_manager.get_clustername()
        env_name = self.get_env_name(adapter_name, cluster_name)
        ansible_run_destination = os.path.join(self.ansible_run_dir, env_name)
        inventory_dir = os.path.join(ansible_run_destination, 'inventories')
        inventory_file = os.path.join(inventory_dir, self.inventory)
        playbook_file = os.path.join(ansible_run_destination, self.playbook)
        log_file = os.path.join(ansible_run_destination, 'run.log')
        config_file = os.path.join(
            ansible_run_destination, self.ansible_config
        )
        cmd = "ANSIBLE_CONFIG=%s ansible-playbook -i %s %s" % (config_file,
                                                               inventory_file,
                                                               playbook_file)
        with open(log_file, 'w') as logfile:
            subprocess.Popen(cmd, shell=True, stdout=logfile, stderr=logfile)
