"""Module to load flags.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import sys

from optparse import OptionParser


class Flags(object):
    PARSER = OptionParser()
    PARSED_OPTIONS = None

    def parse_args(self):
        (options, argv) = Flags.PARSER.parse_args()
        sys.argv = [sys.argv[0]] + argv
        Flags.PARSED_OPTIONS = options

    def __getattr__(self, name):
        if Flags.PARSED_OPTIONS and hasattr(Flags.PARSED_OPTIONS, name):
            return getattr(Flags.PARSED_OPTIONS, name)

        for option in Flags.PARSER.option_list:
            if option.dest == name:
                return option.default

        raise AttributeError('Option instance has no attribute %s' % name)

    def __setattr__(self, name, value):
        if Flags.PARSED_OPTIONS and hasattr(Flags.PARSED_OPTIONS, name):
            setattr(Flags.PARSED_OPTIONS, name, value)
            return

        for option in Flags.PARSER.option_list:
            if option.dest == name:
                option.default = value
                return

        object.__setattr__(self, name, value)


OPTIONS = Flags()


def init():
    """Init flag parsing.
    """
    global OPTIONS
    OPTIONS.parse_args()


def add(flagname, **kwargs):
    """Add a flag name and its setting.

    :param flagname: flag name declared in cmd as --<flagname>=...
    :type flagname: str
    """
    Flags.PARSER.add_option('--%s' % flagname,
                            dest=flagname, **kwargs)


def add_bool(flagname, default=True, **kwargs):
    """Add a bool flag name and its setting.

    :param flagname: flag name declared in cmd as --[no]<flagname>.
    :type flagname: str
    :param default: default value
    :type default: bool
    """
    Flags.PARSER.add_option('--%s' % flagname,
                            dest=flagname, default=default,
                            action="store_true", **kwargs)
    Flags.PARSER.add_option('--no%s' % flagname,
                            dest=flagname,
                            action="store_false", **kwargs)
