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

"""Compass Command Line Interface"""
import logging
import subprocess
import sys

from compass.actions.health_check import check
from compass.db.api import database

from compass.utils import flags
from compass.utils import logsetting
from compass.utils import setting_wrapper as setting
from compass.utils.util import pretty_print


ACTION_MAP = {
    "check": "apache celery dhcp dns hds misc os_installer "
             "package_installer squid tftp".split(" "),
    "refresh": "db sync".split(" "),
}


class BootCLI(object):
    """CLI to do compass check."""

    def __init__(self):
        return

    def run(self, args):
        """cli takes the commands and calls respective modules."""
        action = self.get_action(args)
        if action is None:
            self.print_help()
        else:
            module = self.get_module(action, args)
            if module == "invalid":
                self.print_help(action)
            else:
                method = "self.run_" + action + "(module)"
                eval(method)

    @classmethod
    def get_action(cls, args):
        """This method returns an action type.

           .. note::
              For 'compass check dhcp' command, it will return 'check'.
        """
        if len(args) == 1:
            return None
        elif args[1] in ACTION_MAP.keys():
            return args[1]
        return None

    @classmethod
    def get_module(cls, action, args):
        """This method returns a module.

           .. note::
              For 'compass check dhcp' command, it will return 'dhcp'.
        """
        if len(args) <= 2:
            return None
        elif args[2] in ACTION_MAP[action]:
            return args[2]
        return "invalid"

    def run_check(self, module=None):
        """This provides a flexible sanity check.

           .. note::
              param module default set to None.
              if parameter module is none. Compass checks all modules.
              If module specified, Compass will only check such module.
        """
        if module is None:
            pretty_print("Starting: Compass Health Check",
                         "==============================")
            chk = check.BootCheck()
            res = chk.run()
            self.output_check_result(res)

        else:
            pretty_print("Checking Module: %s" % module,
                         "============================")
            chk = check.BootCheck()
            method = "chk._check_" + module + "()"
            res = eval(method)
            print "\n".join(msg for msg in res[1])

    @classmethod
    def output_check_result(cls, result):
        """output check result."""
        if result == {}:
            return
        pretty_print("\n",
                     "===============================",
                     "* Compass Health Check Report *",
                     "===============================")
        successful = True
        for key in result.keys():
            if result[key][0] == 0:
                successful = False
            print "%s" % "\n".join(item for item in result[key][1])

        print "===================="
        if successful is True:
            print "Compass Check completes. No problems found, all systems go"
            sys.exit(0)
        else:
            print (
                "Compass has ERRORS shown above. Please fix them before "
                "deploying!")
            sys.exit(1)

    @classmethod
    def run_refresh(cls, action=None):
        """Run refresh."""
        # TODO(xicheng): replace refresh.sh with refresh.py
        if action is None:
            pretty_print("Refreshing Compass...",
                         "=================")
            subprocess.Popen(
                ['/opt/compass/bin/refresh.sh'], shell=True)
        elif action == "db":
            pretty_print("Refreshing Compass Database...",
                         "===================")
            subprocess.Popen(
                ['/opt/compass/bin/manage_db.py createdb'], shell=True)
        else:
            pretty_print("Syncing with Installers...",
                         "================")
            subprocess.Popen(
                ['/opt/compass/bin/manage_db.py sync_from_installers'],
                shell=True
            )

    @classmethod
    def print_help(cls, module_help=""):
        """print help."""
        if module_help == "":
            pretty_print("usage\n=====",
                         "compass <refresh|check>",
                         "type 'compass {action} --help' for detailed "
                         "command list")

        elif module_help == "refresh":
            pretty_print("usage\n=====",
                         "compass refresh [%s]" %
                         "|".join(action for action in ACTION_MAP['refresh']))

        else:
            pretty_print("usage\n=====",
                         "compass check [%s]" %
                         "|".join(action for action in ACTION_MAP['check']))
        sys.exit(2)


def main():
    """Compass cli entry point."""
    flags.init()
    logsetting.init()
    database.init()
    cli = BootCLI()
    output = cli.run(sys.argv)
    return sys.exit(output)
