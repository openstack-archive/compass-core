#!/usr/bin/python
#
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

"""Bootstrap setuptools installation

If you want to use setuptools in your package's setup.py, just include this
file in the same directory with it, and add this to the top of your setup.py::

    from ez_setup import use_setuptools
    use_setuptools()

If you want to require a specific version of setuptools, set a download
mirror, or use an alternate download directory, you can do so by supplying
the appropriate options to ``use_setuptools()``.

This file can also be run as a script to install or upgrade setuptools.
"""

"""setup script."""
try:
    from setuptools import find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()


from setuptools.command.test import test as TestCommand
from setuptools import setup


import os
import sys


class Tox(TestCommand):
    """Tox to do the setup."""

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import tox
        errno = tox.cmdline(self.test_args)
        sys.exit(errno)


INSTALL_REQUIRES_DIR = os.path.join(
    os.path.dirname(__file__), 'requirements.txt')


with open(INSTALL_REQUIRES_DIR, 'r') as requires_file:
    REQUIREMENTS = [line.strip() for line in requires_file if line != '\n']


setup(
    name='compass',
    version='0.1.0',

    # general info
    description='Open Deployment System for zero touch installation',
    long_description='Open Deployment System for zero touch installation',
    author='Compass Dev Group, Huawei Cloud',
    author_email='shuo.yang@huawei.com',
    url='https://github.com/huawei-cloud/compass',
    download_url='',

    # dependency
    install_requires=REQUIREMENTS,
    packages=find_packages(exclude=['compass.tests']),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ],
    # test,
    tests_require=['tox'],
    cmdclass={'test': Tox},
)
