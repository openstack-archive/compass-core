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

"""Module to clean installers
"""
import chef
import logging
import xmlrpclib

from compass.actions import util


class CobblerInstaller(object):
    """cobbler installer"""
    CREDENTIALS = "credentials"
    USERNAME = 'username'
    PASSWORD = 'password'

    INSTALLER_URL = "cobbler_url"

    def __init__(self, settings):
        username = settings[self.CREDENTIALS][self.USERNAME]
        password = settings[self.CREDENTIALS][self.PASSWORD]
        cobbler_url = settings[self.INSTALLER_URL]
        try:
            self.remote = xmlrpclib.Server(cobbler_url)
            self.token = self.remote.login(username, password)
            logging.info('cobbler %s client created', cobbler_url)
        except Exception as error:
            logging.error(
                'failed to login %s with (%s, %s)',
                cobbler_url, username, password
            )
            logging.exception(error)

    def clean(self):
        systems = self.remote.get_systems()
        for system in systems:
            system_name = system['name']
            try:
                self.remote.remove_system(system_name, self.token)
                logging.info('system %s is removed', system_name)
            except Exception as error:
                logging.error(
                    'failed to remove system %s', system_name
                )
                logging.exception(error)


class AnsibleInstaller(object):

    def __init__(self, settings):
        return

    def clean(self):
        pass


class ChefInstaller(object):
    DATABAGS = "databags"
    CHEFSERVER_URL = "chef_url"
    CHEFSERVER_DNS = "chef_server_dns"
    CHEFSERVER_IP = "chef_server_ip"
    KEY_DIR = "key_dir"
    CLIENT = "client_name"

    def __init__(self, settings):
        installer_url = settings.get(self.CHEFSERVER_URL, None)
        key_dir = settings.get(self.KEY_DIR, None)
        client = settings.get(self.CLIENT, None)
        try:
            if installer_url and key_dir and client:
                self.api = chef.ChefAPI(installer_url, key_dir, client)
            else:
                self.api = chef.autoconfigure()
            logging.info(
                'chef client created %s(%s, %s)',
                installer_url, key_dir, client
            )
        except Exception as error:
            logging.error(
                'failed to create chef client %s(%s, %s)',
                installer_url, key_dir, client
            )
            logging.exception(error)

    def clean(self):
        try:
            for node_name in chef.Node.list(api=self.api):
                node = chef.Node(node_name, api=self.api)
                node.delete()
                logging.info('delete node %s', node_name)
        except Exception as error:
            logging.error('failed to delete some nodes')
            logging.exception(error)

        try:
            for client_name in chef.Client.list(api=self.api):
                if client_name in ['chef-webui', 'chef-validator']:
                    continue
                client = chef.Client(client_name, api=self.api)
                client.delete()
                logging.info('delete client %s', client_name)
        except Exception as error:
            logging.error('failed to delete some clients')
            logging.exception(error)

        try:
            for env_name in chef.Environment.list(api=self.api):
                if env_name == '_default':
                    continue
                env = chef.Environment(env_name, api=self.api)
                env.delete()
                logging.info('delete env %s', env_name)
        except Exception as error:
            logging.error('failed to delete some envs')
            logging.exception(error)

        try:
            for databag_name in chef.DataBag.list(api=self.api):
                databag = chef.DataBag(databag_name, api=self.api)
                for item_name, item in databag.items():
                    item.delete()
                    logging.info(
                        'delete item %s from databag %s',
                        item_name, databag_name
                    )
        except Exception as error:
            logging.error('failed to delete some databag items')
            logging.exception(error)


OS_INSTALLERS = {
    'cobbler': CobblerInstaller
}
PK_INSTALLERS = {
    'chef_installer': ChefInstaller,
    'ansible_installer': AnsibleInstaller
}


def clean_os_installer(
    os_installer_name, os_installer_settings
):
    with util.lock('serialized_action', timeout=100) as lock:
        if not lock:
            raise Exception(
                'failed to acquire lock to clean os installer'
            )

        if os_installer_name not in OS_INSTALLERS:
            logging.error(
                '%s not found in os_installers',
                os_installer_name
            )

        os_installer = OS_INSTALLERS[os_installer_name](
            os_installer_settings
        )
        os_installer.clean()


def clean_package_installer(
    package_installer_name, package_installer_settings
):
    with util.lock('serialized_action', timeout=100) as lock:
        if not lock:
            raise Exception(
                'failed to acquire lock to clean package installer'
            )

        if package_installer_name not in PK_INSTALLERS:
            logging.error(
                '%s not found in os_installers',
                package_installer_name
            )

        package_installer = PK_INSTALLERS[package_installer_name](
            package_installer_settings
        )
        package_installer.clean()
