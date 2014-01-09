"""Module to load flags.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import sys

from optparse import OptionParser


PARSER = OptionParser()
OPTIONS = None


def init():
    """Init flag parsing.
    """
    global OPTIONS
    (options, argv) = PARSER.parse_args()
    sys.argv = [sys.argv[0]] + argv
    OPTIONS = options


def add(flagname, **kwargs):
    """Add a flag name and its setting.

    :param flagname: flag name declared in cmd as --<flagname>=...
    :type flagname: str
    """
    PARSER.add_option('--%s' % flagname, dest=flagname, **kwargs)


def add_bool(flagname, default=True, **kwargs):
    """Add a bool flag name and its setting.

    :param flagname: flag name declared in cmd as --[no]<flagname>.
    :type flagname: str
    :param default: default value
    :type default: bool
    """
    PARSER.add_option('--%s' % flagname,
                      dest=flagname, default=default,
                      action="store_true", **kwargs)
    PARSER.add_option('--no%s' % flagname,
                      dest=flagname,
                      action="store_false", **kwargs)
