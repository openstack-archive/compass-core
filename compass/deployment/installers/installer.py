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


"""Module to provider installer interface.
"""
from Cheetah.Template import Template
from copy import deepcopy
import imp
import logging
import os
import simplejson as json

from compass.deployment.installers.config_manager import BaseConfigManager
from compass.utils import setting_wrapper as compass_setting
from compass.utils import util


CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))


class BaseInstaller(object):
    """Interface for installer."""
    NAME = 'installer'

    def __repr__(self):
        return '%r[%r]' % (self.__class__.__name__, self.NAME)

    def deploy(self, **kwargs):
        """virtual method to start installing process."""
        raise NotImplementedError

    def clean_progress(self, **kwargs):
        raise NotImplementedError

    def delete_hosts(self, **kwargs):
        """Delete hosts from installer server."""
        raise NotImplementedError

    def redeploy(self, **kwargs):
        raise NotImplementedError

    def ready(self, **kwargs):
        pass

    def cluster_ready(self, **kwargs):
        pass

    def get_tmpl_vars_from_metadata(self, metadata, config):
        """Get variables dictionary for rendering templates from metadata.

        :param dict metadata: The metadata dictionary.
        :param dict config: The
        """
        template_vars = {}
        self._get_tmpl_vars_helper(metadata, config, template_vars)

        return template_vars

    def _get_key_mapping(self, metadata, key, is_regular_key):
        """Get the keyword which the input key maps to.

        This keyword will be added to dictionary used to render templates.

        If the key in metadata has a mapping to another keyword which is
        used for templates, then return this keyword. If the key is started
        with '$', which is a variable in metadata, return the key itself as
        the mapping keyword. If the key has no mapping, return None.

        :param dict metadata: metadata/submetadata dictionary.
        :param str key: The keyword defined in metadata.
        :param bool is_regular_key: False when the key defined in metadata
                                    is a variable(starting with '$').
        """
        mapping_to = key
        if is_regular_key:
            try:
                mapping_to = metadata['_self']['mapping_to']
            except Exception:
                mapping_to = None

        return mapping_to

    def _get_submeta_by_key(self, metadata, key):
        """Get submetadata dictionary.

        Based on current metadata key. And
        determines the input key is a regular string keyword or a variable
        keyword defined in metadata, which starts with '$'.

        :param dict metadata: The metadata dictionary.
        :param str key: The keyword defined in the metadata.
        """
        if key in metadata:
            return (True, metadata[key])

        temp = deepcopy(metadata)
        if '_self' in temp:
            del temp['_self']
        meta_key = temp.keys()[0]
        if meta_key.startswith("$"):
            return (False, metadata[meta_key])

        raise KeyError("'%s' is invalid in metadata '%s'!" % (key, metadata))

    def _get_tmpl_vars_helper(self, metadata, config, output):
        for key, config_value in sorted(config.iteritems()):
            is_regular_key, sub_meta = self._get_submeta_by_key(metadata, key)
            mapping_to = self._get_key_mapping(sub_meta, key, is_regular_key)

            if isinstance(config_value, dict):
                if mapping_to:
                    new_output = output[mapping_to] = {}
                else:
                    new_output = output

                self._get_tmpl_vars_helper(sub_meta, config_value, new_output)

            elif mapping_to:
                output[mapping_to] = config_value

    def get_config_from_template(self, tmpl_path, vars_dict):
        logging.debug("template path is %s", tmpl_path)
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

        # Load base template first if it exists
        base_config = {}
        base_tmpl_path = os.path.join(os.path.dirname(tmpl_path), 'base.tmpl')
        if os.path.isfile(base_tmpl_path) and base_tmpl_path != tmpl_path:
            base_tmpl = Template(file=base_tmpl_path, searchList=searchList)
            base_config = json.loads(base_tmpl.respond(), encoding='utf-8')
            base_config = json.loads(json.dumps(base_config), encoding='utf-8')

        # Load specific template for current adapter
        tmpl = Template(file=open(tmpl_path, "r"), searchList=searchList)
        config = json.loads(tmpl.respond(), encoding='utf-8')
        config = json.loads(json.dumps(config), encoding='utf-8')

        # Merge the two outputs
        config = util.merge_dict(base_config, config)

        logging.debug("get_config_from_template resulting %s", config)
        return config

    @classmethod
    def get_installer(cls, name, path, adapter_info, cluster_info, hosts_info):
        try:
            mod_file, path, descr = imp.find_module(name, [path])
            if mod_file:
                mod = imp.load_module(name, mod_file, path, descr)
                config_manager = BaseConfigManager(adapter_info, cluster_info,
                                                   hosts_info)
                return getattr(mod, mod.NAME)(config_manager)

        except ImportError as exc:
            logging.error('No such module found: %s', name)
            logging.exception(exc)

        return None


class OSInstaller(BaseInstaller):
    """Interface for os installer."""
    NAME = 'OSInstaller'
    INSTALLER_BASE_DIR = os.path.join(CURRENT_DIR, 'os_installers')

    def get_oses(self):
        """virtual method to get supported oses.

        :returns: list of str, each is the supported os version.
        """
        return []

    @classmethod
    def get_installer(cls, name, adapter_info, cluster_info, hosts_info):
        if name is None:
            logging.info("Installer name is None! No OS installer loaded!")
            return None

        path = os.path.join(cls.INSTALLER_BASE_DIR, name)
        installer = super(OSInstaller, cls).get_installer(name, path,
                                                          adapter_info,
                                                          cluster_info,
                                                          hosts_info)

        if not isinstance(installer, OSInstaller):
            logging.info("Installer '%s' is not an OS installer!" % name)
            return None

        return installer

    def poweron(self, host_id):
        pass

    def poweroff(self, host_id):
        pass

    def reset(self, host_id):
        pass


class PKInstaller(BaseInstaller):
    """Interface for package installer."""
    NAME = 'PKInstaller'
    INSTALLER_BASE_DIR = os.path.join(CURRENT_DIR, 'pk_installers')

    def generate_installer_config(self):
        raise NotImplementedError(
            'generate_installer_config is not defined in %s',
            self.__class__.__name__
        )

    def get_target_systems(self):
        """virtual method to get available target_systems for each os.

        :param oses: supported os versions.
        :type oses: list of st

        :returns: dict of os_version to target systems as list of str.
        """
        return {}

    def get_roles(self, target_system):
        """virtual method to get all roles of given target system.

        :param target_system: target distributed system such as OpenStack.
        :type target_system: str

        :returns: dict of role to role description as str.
        """
        return {}

    def os_ready(self, **kwargs):
        pass

    def cluster_os_ready(self, **kwargs):
        pass

    def serialize_config(self, config, destination):
        with open(destination, "w") as f:
            f.write(config)

    @classmethod
    def get_installer(cls, name, adapter_info, cluster_info, hosts_info):
        if name is None:
            logging.info("Install name is None. No package installer loaded!")
            return None

        path = os.path.join(cls.INSTALLER_BASE_DIR, name)
        if not os.path.exists(path):
            path = os.path.join(os.path.join(os.path.join(
                compass_setting.PLUGINS_DIR, name), "implementation"), name)
        if not os.path.exists(path):
            logging.info("Installer '%s' does not exist!" % name)
            return None
        installer = super(PKInstaller, cls).get_installer(name, path,
                                                          adapter_info,
                                                          cluster_info,
                                                          hosts_info)

        if not isinstance(installer, PKInstaller):
            logging.info("Installer '%s' is not a package installer!" % name)
            return None

        return installer
