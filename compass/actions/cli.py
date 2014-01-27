"""Compass Command Line Interface"""

import sys
import os
from subprocess import Popen

from compass.actions.health_check import check
from compass.utils.util import pretty_print

ACTION_MAP = {"check":   "apache celery dhcp dns hds misc os_installer "
                         "package_installer squid tftp".split(" "),
              "refresh": "db sync".split(" "),
              }


class BootCLI:

    def __init__(self):
        return

    def run(self, args):
        """
        cli takes the commands and calls respective modules
        """
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

    def get_action(self, args):
        """
        This method returns an action type.
        For 'compass check dhcp' command, it will return 'check'.
        """
        if len(args) == 1:
            return None
        elif args[1] in ACTION_MAP.keys():
            return args[1]
        return None

    def get_module(self, action, args):
        """
        This method returns a module.
        For 'compass check dhcp' command, it will return 'dhcp'.
        """
        if len(args) <= 2:
            return None
        elif args[2] in ACTION_MAP[action]:
            return args[2]
        return "invalid"

    def run_check(self, module=None):
        """
        param module default set to None.
        This provides a flexible sanity check,
        if parameter module is none. Compass checks all modules.
        If module specified, Compass will only check such module.

        """
        if module is None:
            pretty_print("Starting: Compass Health Check",
                         "==============================")
            c = check.BootCheck()
            res = c.run()
            self.output_check_result(res)

        else:
            pretty_print("Checking Module: %s" % module,
                         "============================")
            c = check.BootCheck()
            method = "c.check_" + module + "()"
            res = eval(method)
            print "\n".join(msg for msg in res[1])

    def output_check_result(self, result):
        if result == {}:
            return
        pretty_print("\n",
                     "===============================",
                     "* Compass Health Check Report *",
                     "===============================")
        successful = True
        num = 1
        for key in result.keys():
            if result[key][0] == 0:
                successful = False
            print "%s" % "\n".join(item for item in result[key][1])

        print "===================="
        if successful is True:
            print "Compass Check completes. No problems found, all systems go"
            sys.exit(0)
        else:
            print "Compass has ERRORS shown above. Please fix them before " \
                  "deploying!"
            sys.exit(1)

    def run_refresh(self, action=None):
        ## TODO: replace refresh.sh with refresh.py
        if action is None:
            pretty_print("Refreshing Compass...",
                         "=================")
            Popen(['/opt/compass/bin/refresh.sh'], shell=True)
        elif action == "db":
            pretty_print("Refreshing Compass Database...",
                         "===================")
            Popen(['/opt/compass/bin/manage_db.py createdb'], shell=True)
        else:
            pretty_print("Syncing with Installers...",
                         "================")
            Popen(['/opt/compass/bin/manage_db.py sync_from_installers'],
                  shell=True)

    def print_help(self, module_help=""):
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
    """
    Compass cli entry point
    """
    cli = BootCLI()
    output = cli.run(sys.argv)
    return sys.exit(output)

if __name__ == "__main__":
    main()
