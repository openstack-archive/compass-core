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

"""os installer cobbler plugin.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import functools
import logging
import os.path
import shutil
import xmlrpclib

from compass.config_management.installers import os_installer
from compass.config_management.utils.config_translator import ConfigTranslator
from compass.config_management.utils.config_translator import KeyTranslator
from compass.config_management.utils import config_translator_callbacks
from compass.utils import setting_wrapper as setting
from compass.utils import util


TO_HOST_TRANSLATOR = ConfigTranslator(
    mapping={
        '/networking/global/gateway': [KeyTranslator(
            translated_keys=['/gateway']
        )],
        '/networking/global/nameservers': [KeyTranslator(
            translated_keys=['/name_servers']
        )],
        '/networking/global/search_path': [KeyTranslator(
            translated_keys=['/name_servers_search']
        )],
        '/networking/global/proxy': [KeyTranslator(
            translated_keys=['/ksmeta/proxy']
        )],
        '/networking/global/ignore_proxy': [KeyTranslator(
            translated_keys=['/ksmeta/ignore_proxy']
        )],
        '/networking/global/ntp_server': [KeyTranslator(
            translated_keys=['/ksmeta/ntp_server']
        )],
        '/security/server_credentials/username': [KeyTranslator(
            translated_keys=['/ksmeta/username']
        )],
        '/security/server_credentials/password': [KeyTranslator(
            translated_keys=['/ksmeta/password'],
            translated_value=config_translator_callbacks.get_encrypted_value
        )],
        '/partition': [KeyTranslator(
            translated_keys=['/ksmeta/partition']
        )],
        '/networking/interfaces/*/mac': [KeyTranslator(
            translated_keys=[functools.partial(
                config_translator_callbacks.get_key_from_pattern,
                to_pattern='/modify_interface/macaddress-%(nic)s')],
            from_keys={'nic': '../nic'},
            override=functools.partial(
                config_translator_callbacks.override_path_has,
                should_exist='management')
        )],
        '/networking/interfaces/*/ip': [KeyTranslator(
            translated_keys=[functools.partial(
                config_translator_callbacks.get_key_from_pattern,
                to_pattern='/modify_interface/ipaddress-%(nic)s')],
            from_keys={'nic': '../nic'},
            override=functools.partial(
                config_translator_callbacks.override_path_has,
                should_exist='management')
        )],
        '/networking/interfaces/*/netmask': [KeyTranslator(
            translated_keys=[functools.partial(
                config_translator_callbacks.get_key_from_pattern,
                to_pattern='/modify_interface/netmask-%(nic)s')],
            from_keys={'nic': '../nic'},
            override=functools.partial(
                config_translator_callbacks.override_path_has,
                should_exist='management')
        )],
        '/networking/interfaces/*/dns_alias': [KeyTranslator(
            translated_keys=[functools.partial(
                config_translator_callbacks.get_key_from_pattern,
                to_pattern='/modify_interface/dnsname-%(nic)s')],
            from_keys={'nic': '../nic'},
            override=functools.partial(
                config_translator_callbacks.override_path_has,
                should_exist='management')
        )],
        '/networking/interfaces/*/nic': [KeyTranslator(
            translated_keys=[functools.partial(
                config_translator_callbacks.get_key_from_pattern,
                to_pattern='/modify_interface/static-%(nic)s')],
            from_keys={'nic': '../nic'},
            translated_value=True,
            override=functools.partial(
                config_translator_callbacks.override_path_has,
                should_exist='management'),
        ), KeyTranslator(
            translated_keys=[functools.partial(
                config_translator_callbacks.get_key_from_pattern,
                to_pattern='/modify_interface/management-%(nic)s')],
            from_keys={'nic': '../nic'},
            translated_value=functools.partial(
                config_translator_callbacks.override_path_has,
                should_exist='management'),
            override=functools.partial(
                config_translator_callbacks.override_path_has,
                should_exist='management')
        ), KeyTranslator(
            translated_keys=['/ksmeta/promisc_nics'],
            from_values={'condition': '../promisc'},
            translated_value=config_translator_callbacks.add_value,
            override=True,
        )],
    }
)


class Installer(os_installer.Installer):
    """cobbler installer"""
    NAME = 'cobbler'

    def __init__(self, **kwargs):
        super(Installer, self).__init__()
        # the connection is created when cobbler installer is initialized.
        self.remote_ = xmlrpclib.Server(
            setting.COBBLER_INSTALLER_URL,
            allow_none=True)
        self.token_ = self.remote_.login(
            *setting.COBBLER_INSTALLER_TOKEN)

        # cobbler tries to get package related config from package installer.
        self.package_installer_ = kwargs['package_installer']
        logging.debug('%s instance created', self)

    def __repr__(self):
        return '%s[name=%s,remote=%s,token=%s' % (
            self.__class__.__name__, self.NAME,
            self.remote_, self.token_)

    def get_oses(self):
        """get supported os versions.

        :returns: list of os version.

        .. note::
           In cobbler, we treat profile name as the indicator
           of os version. It is just a simple indicator
           and not accurate.
        """
        profiles = self.remote_.get_profiles()
        oses = []
        for profile in profiles:
            oses.append(profile['name'])
        return oses

    def sync(self):
        """Sync cobbler to catch up the latest update config."""
        logging.debug('sync %s', self)
        self.remote_.sync(self.token_)
        os.system('service rsyslog restart')

    def _get_modify_system(self, profile, config, **kwargs):
        """get modified system config."""
        system_config = {
            'name': config['fullname'],
            'hostname': config['hostname'],
            'profile': profile,
        }

        translated_config = TO_HOST_TRANSLATOR.translate(config)
        util.merge_dict(system_config, translated_config)

        ksmeta = system_config.setdefault('ksmeta', {})
        package_config = {'tool': self.package_installer_.NAME}
        util.merge_dict(
            package_config,
            self.package_installer_.os_installer_config(
                config, **kwargs))
        util.merge_dict(ksmeta, package_config)

        return system_config

    def _get_profile(self, os_version, **_kwargs):
        """get profile name."""
        profile_found = self.remote_.find_profile(
            {'name': os_version})
        return profile_found[0]

    def _get_system(self, config, create_if_not_exists=True):
        """get system reference id."""
        sys_name = config['fullname']
        try:
            sys_id = self.remote_.get_system_handle(
                sys_name, self.token_)
            logging.debug('using existing system %s for %s',
                          sys_id, sys_name)
        except Exception:
            if create_if_not_exists:
                sys_id = self.remote_.new_system(self.token_)
                logging.debug('create new system %s for %s',
                              sys_id, sys_name)
            else:
                sys_id = None

        return sys_id

    def _clean_system(self, config):
        """clean system."""
        sys_name = config['fullname']
        try:
            self.remote_.remove_system(sys_name, self.token_)
            logging.debug('system %s is removed', sys_name)
        except Exception:
            logging.debug('no system %s found to remove', sys_name)

    def _save_system(self, sys_id):
        """save system config update."""
        self.remote_.save_system(sys_id, self.token_)

    def _update_modify_system(self, sys_id, system_config):
        """update modify system."""
        for key, value in system_config.items():
            self.remote_.modify_system(
                sys_id, key, value, self.token_)

    def _netboot_enabled(self, sys_id):
        """enable netboot."""
        self.remote_.modify_system(
            sys_id, 'netboot_enabled', True, self.token_)

    def clean_host_config(self, hostid, config, **kwargs):
        """clean host config."""
        self.clean_host_installing_progress(
            hostid, config, **kwargs)
        self._clean_system(config)

    @classmethod
    def _clean_log(cls, system_name):
        """clean log."""
        log_dir = os.path.join(
            setting.INSTALLATION_LOGDIR,
            system_name)
        shutil.rmtree(log_dir, True)

    def clean_host_installing_progress(
        self, hostid, config, **kwargs
    ):
        """clean host installing progress."""
        self._clean_log(config['fullname'])

    def reinstall_host(self, hostid, config, **kwargs):
        """reinstall host."""
        sys_id = self._get_system(config, False)
        if sys_id:
            self.clean_host_installing_progress(
                hostid, config, **kwargs)
            self._netboot_enabled(sys_id)
            self._save_system(sys_id)

    def update_host_config(self, hostid, config, **kwargs):
        """update host config."""
        self.clean_host_config(hostid, config, **kwargs)
        profile = self._get_profile(**kwargs)
        sys_id = self._get_system(config)
        system_config = self._get_modify_system(
            profile, config, **kwargs)
        logging.debug('%s system config to update: %s',
                      hostid, system_config)

        self._update_modify_system(sys_id, system_config)
        self._save_system(sys_id)


os_installer.register(Installer)
