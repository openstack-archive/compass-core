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

"""package installer: chef plugin."""

from copy import deepcopy
import logging
from netaddr import IPAddress
import os
import re
import shutil

from compass.deployment.installers.installer import PKInstaller
from compass.deployment.utils import constants as const
from compass.utils import setting_wrapper as compass_setting
from compass.utils import util


NAME = 'ChefInstaller'


class ChefInstaller(PKInstaller):
    """chef package installer."""
    ENV_TMPL_DIR = 'environments'
    NODE_TMPL_DIR = 'nodes'
    DATABAG_TMPL_DIR = 'databags'

    # keywords in package installer settings of adapter info
    DATABAGS = "databags"
    CHEFSERVER_URL = "chef_url"
    CHEFSERVER_DNS = "chef_server_dns"
    CHEFSERVER_IP = "chef_server_ip"
    KEY_DIR = "key_dir"
    CLIENT = "client_name"

    def __init__(self, config_manager):
        super(ChefInstaller, self).__init__()

        self.config_manager = config_manager
        adapter_name = self.config_manager.get_dist_system_name()
        self.tmpl_dir = ChefInstaller.get_tmpl_path(adapter_name)

        installer_settings = self.config_manager.get_pk_installer_settings()
        self.installer_url = self.get_chef_url(installer_settings)
        key, client = self.get_chef_credentials(installer_settings)

        self.chef_api = self._get_chef_api(key, client)
        logging.debug('%s instance created', self)

    @classmethod
    def get_tmpl_path(cls, adapter_name):
        tmpl_path = os.path.join(os.path.join(compass_setting.TMPL_DIR,
                                              'chef_installer'),
                                 adapter_name)
        return tmpl_path

    def __repr__(self):
        return '%s[name=%s,installer_url=%s]' % (
            self.__class__.__name__, self.NAME, self.installer_url)

    def _get_chef_api(self, key=None, client=None):
        """Initializes chef API client."""
        import chef
        chef_api = None
        try:
            if key and client:
                chef_api = chef.ChefAPI(self.installer_url, key, client)
            else:
                chef_api = chef.autoconfigure()

        except Exception as ex:
            err_msg = "Failed to instantiate chef API, error: %s" % ex.message
            raise Exception(err_msg)

        return chef_api

    def get_env_name(self, dist_sys_name, cluster_name):
        """Generate environment name."""
        return "-".join((dist_sys_name, cluster_name))

    def get_databag(self, databag_name):
        """Get databag object from chef server. Create the databag if it
           does not exist.
        """
        import chef
        databag = None
        if databag_name not in chef.DataBag.list(api=self.chef_api):
            databag = chef.DataBag.create(databag_name, api=self.chef_api)
        else:
            databag = chef.DataBag(databag_name, api=self.chef_api)

        return databag

    def get_node(self, node_name, env_name):
        """Get chef node if existing, otherwise create one and set its
           environment.

           :param str node_name: The name for this node.
           :param str env_name: The environment name for this node.
        """
        import chef
        if not self.chef_api:
            logging.info("Cannot find ChefAPI object!")
            raise Exception("Cannot find ChefAPI object!")

        node = chef.Node(node_name, api=self.chef_api)
        if node not in chef.Node.list(api=self.chef_api):
            if env_name:
                node.chef_environment = env_name
            node.save()

        return node

    def delete_hosts(self):
        hosts_id_list = self.config_manager.get_host_id_list()
        for host_id in hosts_id_list:
            self.delete_node(host_id)

    def delete_node(self, host_id):
        fullname = self.config_manager.get_host_fullname(host_id)
        node = self.get_node(fullname)
        self._delete_node(node)

    def _delete_node(self, node):
        """clean node attributes about target system."""
        import chef
        if node is None:
            raise Exception("Node is None, cannot delete a none node.")
        node_name = node.name
        client_name = node_name

        # Clean log for this node first
        log_dir_prefix = compass_setting.INSTALLATION_LOGDIR[self.NAME]
        self._clean_log(log_dir_prefix, node_name)

        # Delete node and its client on chef server
        try:
            node.delete()
            client = chef.Client(client_name, api=self.chef_api)
            client.delete()
            logging.debug('delete node %s', node_name)
            log_dir_prefix = compass_setting.INSTALLATION_LOGDIR[self.NAME]
            self._clean_log(log_dir_prefix, node_name)
        except Exception as error:
            logging.debug(
                'failed to delete node %s, error: %s', node_name, error)

    def _add_roles(self, node, roles):
        """Add roles to the node.
           :param object node: The node object.
           :param list roles: The list of roles for this node.
        """
        if node is None:
            raise Exception("Node is None!")

        if not roles:
            logging.info("Role list is None. Run list will no change.")
            return

        run_list = node.run_list
        for role in roles:
            node_role = 'role[%s]' % role
            if node_role not in run_list:
                node.run_list.append(node_role)

        node.save()
        logging.debug('Runlist for node %s is %s', node.name, node.run_list)

    def _get_node_attributes(self, roles, vars_dict):
        """Get node attributes from templates according to its roles. The
           templates are named by roles without '-'. Return the dictionary
           of attributes defined in the templates.

           :param list roles: The roles for this node, used to load the
                              specific template.
           :param dict vars_dict: The dictionary used in cheetah searchList to
                                  render attributes from templates.
        """
        if not roles:
            return {}

        node_tmpl_dir = os.path.join(self.tmpl_dir, self.NODE_TMPL_DIR)
        node_attr = {}
        for role in roles:
            role = role.replace('-', '_')
            tmpl_name = '.'.join((role, 'tmpl'))
            node_tmpl = os.path.join(node_tmpl_dir, tmpl_name)
            util.merge_dict(
                node_attr, self.get_config_from_template(node_tmpl, vars_dict)
            )

        return node_attr

    def update_node(self, node, roles, vars_dict):
        """Update node attributes to chef server."""
        if node is None:
            raise Exception("Node is None!")

        if not roles:
            logging.info("The list of roles is None.")
            return

        # Add roles to node Rolelist on chef server.
        self._add_roles(node, roles)

        # Update node attributes.
        node_config = self._get_node_attributes(roles, vars_dict)
        for attr in node_config:
            node.attributes[attr] = node_config[attr]

        node.save()

    def _get_env_attributes(self, vars_dict):
        """Get environment attributes from env templates."""

        env_tmpl_fname = self.config_manager.get_cluster_flavor_template()
        env_tmpl_path = os.path.join(
            os.path.join(self.tmpl_dir, self.ENV_TMPL_DIR), env_tmpl_fname
        )
        env_attri = self.get_config_from_template(env_tmpl_path, vars_dict)
        return env_attri

    def get_environment(self, env_name):
        import chef
        env = chef.Environment(env_name, api=self.chef_api)
        env.save()
        return env

    def _update_env(self, env, env_attrs):
        for attr in env_attrs:
            if attr in env.attributes:
                setattr(env, attr, env_attrs[attr])
        env.save()

    def update_environment(self, env_name, vars_dict):
        """Generate environment attributes based on the template file and
           upload it to chef server.

           :param str env_name: The environment name.
           :param dict vars_dict: The dictionary used in cheetah searchList to
                                  render attributes from templates.
        """
        env_config = self._get_env_attributes(vars_dict)
        env = self.get_environment(env_name)
        self._update_env(env, env_config)

    def _get_databagitem_attributes(self, tmpl_dir, vars_dict):
        databagitem_attrs = self.get_config_from_template(tmpl_dir,
                                                          vars_dict)

        return databagitem_attrs

    def update_databags(self, vars_dict):
        """Update databag item attributes.

           :param dict vars_dict: The dictionary used to get attributes from
                                  templates.
        """
        databag_names = self.get_chef_databag_names()
        if not databag_names:
            return

        import chef
        databags_dir = os.path.join(self.tmpl_dir, self.DATABAG_TMPL_DIR)
        for databag_name in databag_names:
            databag_tmpl = os.path.join(databags_dir, databag_name)
            databagitem_attrs = self._get_databagitem_attributes(databag_tmpl,
                                                                 vars_dict)
            if not databagitem_attrs:
                logging.info("Databag template not found or vars_dict is None")
                logging.info("databag template is %s", databag_tmpl)
                continue

            databag = self.get_databag(databag_name)
            for item, item_values in databagitem_attrs.iteritems():
                databagitem = chef.DataBagItem(databag, item, self.chef_api)
                for key, value in item_values.iteritems():
                    databagitem[key] = value
                databagitem.save()

    def _get_host_tmpl_vars(self, host_id, global_vars_dict):
        """Get templates variables dictionary for cheetah searchList based
           on host package config.

           :param int host_id: The host ID.
           :param dict global_vars_dict: The vars_dict got from cluster level
                                         package_config.
        """
        vars_dict = {}
        if global_vars_dict:
            temp = global_vars_dict[const.CLUSTER][const.DEPLOYED_PK_CONFIG]
            vars_dict[const.DEPLOYED_PK_CONFIG] = deepcopy(temp)

        host_baseinfo = self.config_manager.get_host_baseinfo(host_id)
        util.merge_dict(vars_dict, host_baseinfo)

        pk_config = self.config_manager.get_host_package_config(host_id)
        if pk_config:
            # Get host template variables and merge to vars_dict
            metadata = self.config_manager.get_pk_config_meatadata()
            host_dict = self.get_tmpl_vars_from_metadata(metadata, pk_config)
            #util.merge_dict(vars_dict[const.DEPLOYED_PK_CONFIG], host_dict)
            vars_dict[const.DEPLOYED_PK_CONFIG].update(host_dict)

        # Set role_mapping for host
        mapping = self.config_manager.get_host_roles_mapping(host_id)
        vars_dict[const.DEPLOYED_PK_CONFIG][const.ROLES_MAPPING] = mapping

        return {const.HOST: vars_dict}

    def _get_cluster_tmpl_vars(self):
        vars_dict = {}
        # set cluster basic information to vars_dict
        cluster_baseinfo = self.config_manager.get_cluster_baseinfo()
        util.merge_dict(vars_dict, cluster_baseinfo)

        # get and set template variables from cluster package config.
        pk_metadata = self.config_manager.get_pk_config_meatadata()
        pk_config = self.config_manager.get_cluster_package_config()
        meta_dict = self.get_tmpl_vars_from_metadata(pk_metadata, pk_config)
        vars_dict[const.DEPLOYED_PK_CONFIG] = meta_dict

        # get and set roles_mapping to vars_dict
        mapping = self.config_manager.get_cluster_roles_mapping()
        vars_dict[const.DEPLOYED_PK_CONFIG][const.ROLES_MAPPING] = mapping

        return {const.CLUSTER: vars_dict}

    def deploy(self):
        """Start to deploy a distributed system. Return both cluster and hosts
           deployed configs. The return format:
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
        adapter_name = self.config_manager.get_adapter_name()
        cluster_name = self.config_manager.get_clustername()
        env_name = self.get_env_name(adapter_name, cluster_name)

        global_vars_dict = self._get_cluster_tmpl_vars()

        # Update environment
        self.update_environment(env_name, global_vars_dict)

        # Update Databag item
        self.update_databags(global_vars_dict)

        host_list = self.config_manager.get_host_id_list()
        hosts_deployed_configs = {}

        for host_id in host_list:
            node_name = self.config_manager.get_host_fullname(host_id)
            roles = self.config_manager.get_host_roles(host_id)

            node = self.get_node(node_name, env_name)
            vars_dict = self._get_host_tmpl_vars(host_id, global_vars_dict)
            self.update_node(node, roles, vars_dict)

            # set each host deployed config
            tmp = {}
            host_config = {}
            tmp.update(vars_dict[const.HOST][const.DEPLOYED_PK_CONFIG])
            host_config = {
                host_id: {const.DEPLOYED_PK_CONFIG: tmp}
            }
            hosts_deployed_configs.update(host_config)

        # set cluster deployed config
        cl_config = {}
        cl_config.update(global_vars_dict)

        output = {}
        output.update(cl_config)
        output.update({const.HOSTS: hosts_deployed_configs})
        return output

    def generate_installer_config(self):
        """Render chef config file (client.rb) by OS installing right after
           OS is installed successfully.
           The output format:
           {
              '1'($host_id/clusterhost_id):{
                  'tool': 'chef',
                  'chef_url': 'https://xxx',
                  'chef_client_name': '$host_name',
                  'chef_node_name': '$host_name',
                  'chef_server_ip': 'xxx',(op)
                  'chef_server_dns': 'xxx' (op)
              },
              .....
           }
        """
        host_ids = self.config_manager.get_host_id_list()
        os_installer_configs = {}
        regex = "http[s]?://([^:/]+)[:\d]?.*"
        for host_id in host_ids:
            fullname = self.config_manager.get_host_fullname(host_id)
            temp = {
                "tool": "chef",
                "chef_url": self.installer_url
            }
            chef_host = re.search(regex, self.installer_url).groups()[0]
            try:
                IPAddress(chef_host)
                temp['chef_server_ip'] = chef_host
                temp['chef_server_dns'] = self.get_chef_server_dns()
            except Exception:
                chef_server_ip = self.get_chef_server_ip()
                if chef_server_ip:
                    temp['chef_server_ip'] = chef_server_ip
                    temp['chef_server_dns'] = chef_host

            temp['chef_client_name'] = fullname
            temp['chef_node_name'] = fullname
            os_installer_configs[host_id] = temp

        return os_installer_configs

    def clean_progress(self):
        """Clean all installing log about the node."""
        log_dir_prefix = compass_setting.INSTALLATION_LOGDIR[self.NAME]
        hosts_list = self.config_manager.get_host_id_list()
        for host_id in hosts_list:
            fullname = self.config_manager.get_host_fullname()
            self._clean_log(log_dir_prefix, fullname)

    def _clean_log(self, log_dir_prefix, node_name):
        log_dir = os.path.join(log_dir_prefix, node_name)
        shutil.rmtree(log_dir, False)

    def get_supported_dist_systems(self):
        """get target systems from chef. All target_systems for compass will
           be stored in the databag called "compass".
        """
        databag = self.__get_compass_databag()
        target_systems = {}
        for system_name, item in databag:
            target_systems[system_name] = item

        return target_systems

    def _clean_databag_item(self, databag, item_name):
        """clean databag item."""
        import chef
        if item_name not in chef.DataBagItem.list(api=self.chef_api):
            logging.info("Databag item '%s' is not found!", item_name)
            return

        bag_item = databag[item_name]
        try:
            bag_item.delete()
            logging.debug('databag item %s is removed from databag',
                          item_name)
            bag_item.save()
        except Exception as error:
            logging.debug('Failed to delete item  %s from databag! Error: %s',
                          item_name, error)

    def redeploy(self):
        """reinstall host."""
        pass

    def get_chef_server_ip(self, installer_settings=None):
        settings = installer_settings
        if settings is None:
            settings = self.config_manager.get_pk_installer_settings()

        return settings.setdefault(self.CHEFSERVER_IP, None)

    def get_chef_url(self, installer_settings=None):
        settings = installer_settings
        if settings is None:
            settings = self.config_manager.get_pk_installer_settings()

        if self.CHEFSERVER_URL not in settings:
            err_msg = "%s is not in chef server settings" % self.CHEFSERVER_URL
            raise Exception(err_msg)

        return settings[self.CHEFSERVER_URL]

    def get_chef_credentials(self, installer_settings=None):
        settings = installer_settings
        if settings is None:
            settings = self.config_manager.get_pk_installer_settings()

        key_dir = settings.setdefault(self.KEY_DIR, None)
        client = settings.setdefault(self.CLIENT, None)

        return (key_dir, client)

    def get_chef_databag_names(self, installer_settings=None):
        settings = installer_settings
        if settings is None:
            settings = self.config_manager.get_pk_installer_settings()

        if self.DATABAGS not in settings:
            logging.info("No databags is set!")
            return None

        return settings[self.DATABAGS]

    def get_chef_server_dns(self, installer_settings=None):
        settings = installer_settings
        if settings is None:
            settings = self.config_manager.get_pk_installer_settings()

        return settings.setdefault(self.CHEFSERVER_DNS, None)
