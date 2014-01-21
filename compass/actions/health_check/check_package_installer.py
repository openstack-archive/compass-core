"""Health Check module for Package Installer"""

import os
import re
import requests

import base
import utils as health_check_utils
import setting as health_check_setting

class PackageInstallerCheck(base.BaseCheck):

    NAME = "Package Installer Check"
    def run(self):
        installer = self.config.PACKAGE_INSTALLER
        method_name = "self." + installer + "_check()"
        return eval(method_name)

    def chef_check(self):
        """Checks chef setting, cookbooks, databags and roles"""

        CHEFDATA_MAP = { 'CookBook'   :  health_check_setting.COOKBOOKS,
                         'DataBag'    :  health_check_setting.DATABAGS,
                         'Role'       :  health_check_setting.ROLES,
                       }

        total_missing = []
        for data_type in CHEFDATA_MAP.keys():
            total_missing.append(self.check_chef_data(data_type, CHEFDATA_MAP[data_type]))
            print "[Done]"

        missing = False
        for item in total_missing:
            if item[1] != []:
                missing = True
                break

        if missing == True:
            messages = []
            for item in total_missing:
                messages.append("[%s]:%s" % (item[0], ', '.join(missed for missed in item[1])))
            self.set_status(0, "[Package_Installer]Error: Missing modules on chef server: %s. " % ' ;'.join(message for message in messages))

        self.check_chef_config_dir()
        print "[Done]"
        if self.code == 1:
            self.messages.append("[Package Installer]Info: Package installer health check has completed. No problems found, all systems go.")
        return (self.code, self.messages)

    def check_chef_data(self, data_type, github_url):
        """
        Checks if chef cookbooks/roles/databags are correct.

        :param data_type  : chef data type, should be one of ['CookBook','DataBag','Role']
        :type data_type   : string
        :param github_url : Latest chef data on stackforge/compass-adapters
        :type github_url  : string

        """
        print "Checking Chef %s......" % (data_type.lower().strip() + 's'),
        try:
            import chef
        except:
            self.set_status(0, "[Package Installer]Error: pychef is not installed.")
            return self.get_status()

        self.api_ = chef.autoconfigure()

        github = set([item['name'] for item in requests.get(github_url).json()])
        if data_type == 'CookBook':
            local = set(os.listdir('/var/chef/cookbooks'))
        elif data_type == 'Role':
            local = set([name for name, item in chef.Role.list(api = self.api_).iteritems()])
            github = set([item['name'].replace(".rb","") for item in requests.get(github_url).json()])
        else:
            local = set([item for item in eval('chef.' + data_type + '.list(api = self.api_)')])
        diff = github - local

        if len(diff) <= 0:
            return (data_type, [])
        else:
            return (data_type, list(diff))

    def check_chef_config_dir(self):
        """Validates chef configuration directories"""

        print "Checking Chef configurations......",
        message = health_check_utils.check_path(self.NAME, '/etc/chef-server/')
        if not message == "":
            self.set_status(0, message)

        message = health_check_utils.check_path(self.NAME, '/opt/chef-server/')
        if not message == "":
            self.set_status(0, message)
        return None
