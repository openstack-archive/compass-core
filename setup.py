try:
    from setuptools import setup, find_packages
    from setuptools.command.test import test as TestCommand
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup
    from setuptools.command.test import test as TestCommand

import sys
import os


class Tox(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import tox
        errno = tox.cmdline(self.test_args)
        sys.exit(errno)

install_requires_dir = os.path.join(
    os.path.dirname(__file__), 'requirements.txt')

with open(install_requires_dir, 'r') as f:
    requirements = [line.strip() for line in f if line != '\n']

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
    install_requires=requirements,
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
