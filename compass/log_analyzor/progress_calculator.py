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

"""module to provide updating installing process function.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import logging

from compass.log_analyzor.adapter_matcher import AdapterItemMatcher
from compass.log_analyzor.adapter_matcher import AdapterMatcher
from compass.log_analyzor.adapter_matcher import OSMatcher
from compass.log_analyzor.adapter_matcher import PackageMatcher
from compass.log_analyzor.file_matcher import FileMatcher
from compass.log_analyzor.line_matcher import IncrementalProgress
from compass.log_analyzor.line_matcher import LineMatcher


# TODO(weidong): reconsider intialization method for the following.
OS_INSTALLER_CONFIGURATIONS = {
    'Ubuntu': AdapterItemMatcher(
        file_matchers=[
            FileMatcher(
                filename='syslog',
                min_progress=0.0,
                max_progress=1.0,
                line_matchers={
                    'start': LineMatcher(
                        pattern=r'.*',
                        progress=.05,
                        message_template='start installing',
                        unmatch_nextline_next_matcher_name='start',
                        match_nextline_next_matcher_name='ethdetect'
                    ),
                    'ethdetect': LineMatcher(
                        pattern=r'Menu.*item.*\'ethdetect\'.*selected',
                        progress=.1,
                        message_template='ethdetect selected',
                        unmatch_nextline_next_matcher_name='ethdetect',
                        match_nextline_next_matcher_name='netcfg'
                    ),
                    'netcfg': LineMatcher(
                        pattern=r'Menu.*item.*\'netcfg\'.*selected',
                        progress=.12,
                        message_template='netcfg selected',
                        unmatch_nextline_next_matcher_name='netcfg',
                        match_nextline_next_matcher_name='network-preseed'
                    ),
                    'network-preseed': LineMatcher(
                        pattern=r'Menu.*item.*\'network-preseed\'.*selected',
                        progress=.15,
                        message_template='network-preseed selected',
                        unmatch_nextline_next_matcher_name='network-preseed',
                        match_nextline_next_matcher_name='localechooser'
                    ),
                    'localechoose': LineMatcher(
                        pattern=r'Menu.*item.*\'localechooser\'.*selected',
                        progress=.18,
                        message_template='localechooser selected',
                        unmatch_nextline_next_matcher_name='localechooser',
                        match_nextline_next_matcher_name='download-installer'
                    ),
                    'download-installer': LineMatcher(
                        pattern=(
                            r'Menu.*item.*\'download-installer\'.*selected'
                        ),
                        progress=.2,
                        message_template='download installer selected',
                        unmatch_nextline_next_matcher_name=(
                            'download-installer'),
                        match_nextline_next_matcher_name='clock-setup'
                    ),
                    'clock-setup': LineMatcher(
                        pattern=r'Menu.*item.*\'clock-setup\'.*selected',
                        progress=.3,
                        message_template='clock-setup selected',
                        unmatch_nextline_next_matcher_name='clock-setup',
                        match_nextline_next_matcher_name='disk-detect'
                    ),
                    'disk-detect': LineMatcher(
                        pattern=r'Menu.*item.*\'disk-detect\'.*selected',
                        progress=.32,
                        message_template='disk-detect selected',
                        unmatch_nextline_next_matcher_name='disk-detect',
                        match_nextline_next_matcher_name='partman-base'
                    ),
                    'partman-base': LineMatcher(
                        pattern=r'Menu.*item.*\'partman-base\'.*selected',
                        progress=.35,
                        message_template='partman-base selected',
                        unmatch_nextline_next_matcher_name='partman-base',
                        match_nextline_next_matcher_name='live-installer'
                    ),
                    'live-installer': LineMatcher(
                        pattern=r'Menu.*item.*\'live-installer\'.*selected',
                        progress=.45,
                        message_template='live-installer selected',
                        unmatch_nextline_next_matcher_name='live-installer',
                        match_nextline_next_matcher_name='pkgsel'
                    ),
                    'pkgsel': LineMatcher(
                        pattern=r'Menu.*item.*\'pkgsel\'.*selected',
                        progress=.5,
                        message_template='pkgsel selected',
                        unmatch_nextline_next_matcher_name='pkgsel',
                        match_nextline_next_matcher_name='grub-installer'
                    ),
                    'grub-installer': LineMatcher(
                        pattern=r'Menu.*item.*\'grub-installer\'.*selected',
                        progress=.9,
                        message_template='grub-installer selected',
                        unmatch_nextline_next_matcher_name='grub-installer',
                        match_nextline_next_matcher_name='finish-install'
                    ),
                    'finish-install': LineMatcher(
                        pattern=r'Menu.*item.*\'finish-install\'.*selected',
                        progress=.95,
                        message_template='finish-install selected',
                        unmatch_nextline_next_matcher_name='finish-install',
                        match_nextline_next_matcher_name='finish-install-done'
                    ),
                    'finish-install-done': LineMatcher(
                        pattern=r'Running.*finish-install.d/.*save-logs',
                        progress=1.0,
                        message_template='finish-install is done',
                        unmatch_nextline_next_matcher_name=(
                            'finish-install-done'
                        ),
                        match_nextline_next_matcher_name='exit'
                    ),
                }
            ),
            FileMatcher(
                filename='status',
                min_progress=.2,
                max_progress=.3,
                line_matchers={
                    'start': LineMatcher(
                        pattern=r'Package: (?P<package>.*)',
                        progress=IncrementalProgress(0.0, 0.99, 0.05),
                        message_template='Installing udeb %(package)s',
                        unmatch_nextline_next_matcher_name='start',
                        match_nextline_next_matcher_name='start'
                    )
                }
            ),
            FileMatcher(
                filename='initial-status',
                min_progress=.5,
                max_progress=.9,
                line_matchers={
                    'start': LineMatcher(
                        pattern=r'Package: (?P<package>.*)',
                        progress=IncrementalProgress(0.0, 0.99, 0.01),
                        message_template='Installing deb %(package)s',
                        unmatch_nextline_next_matcher_name='start',
                        match_nextline_next_matcher_name='start'
                    )
                }
            ),
        ]
    ),
    'CentOS': AdapterItemMatcher(
        file_matchers=[
            FileMatcher(
                filename='sys.log',
                min_progress=0.0,
                max_progress=0.1,
                line_matchers={
                    'start': LineMatcher(
                        pattern=r'NOTICE (?P<message>.*)',
                        progress=IncrementalProgress(.1, .9, .1),
                        message_template='%(message)s',
                        unmatch_nextline_next_matcher_name='start',
                        match_nextline_next_matcher_name='exit'
                    ),
                }
            ),
            FileMatcher(
                filename='anaconda.log',
                min_progress=0.1,
                max_progress=1.0,
                line_matchers={
                    'start': LineMatcher(
                        pattern=r'setting.*up.*kickstart',
                        progress=.1,
                        message_template=(
                            'Setting up kickstart configurations'),
                        unmatch_nextline_next_matcher_name='start',
                        match_nextline_next_matcher_name='STEP_STAGE2'
                    ),
                    'STEP_STAGE2': LineMatcher(
                        pattern=r'starting.*STEP_STAGE2',
                        progress=.15,
                        message_template=(
                            'Downloading installation '
                            'images from server'),
                        unmatch_nextline_next_matcher_name='STEP_STAGE2',
                        match_nextline_next_matcher_name='start_anaconda'
                    ),
                    'start_anaconda': LineMatcher(
                        pattern=r'Running.*anaconda.*script',
                        progress=.2,
                        unmatch_nextline_next_matcher_name=(
                            'start_anaconda'),
                        match_nextline_next_matcher_name=(
                            'start_kickstart_pre')
                    ),
                    'start_kickstart_pre': LineMatcher(
                        pattern=r'Running.*kickstart.*pre.*script',
                        progress=.25,
                        unmatch_nextline_next_matcher_name=(
                            'start_kickstart_pre'),
                        match_nextline_next_matcher_name=(
                            'kickstart_pre_done')
                    ),
                    'kickstart_pre_done': LineMatcher(
                        pattern=(
                            r'All.*kickstart.*pre.*script.*have.*been.*run'),
                        progress=.3,
                        unmatch_nextline_next_matcher_name=(
                            'kickstart_pre_done'),
                        match_nextline_next_matcher_name=(
                            'start_enablefilesystem')
                    ),
                    'start_enablefilesystem': LineMatcher(
                        pattern=r'moving.*step.*enablefilesystems',
                        progress=0.3,
                        message_template=(
                            'Performing hard-disk partitioning and '
                            'enabling filesystems'),
                        unmatch_nextline_next_matcher_name=(
                            'start_enablefilesystem'),
                        match_nextline_next_matcher_name=(
                            'enablefilesystem_done')
                    ),
                    'enablefilesystem_done': LineMatcher(
                        pattern=r'leaving.*step.*enablefilesystems',
                        progress=.35,
                        message_template='Filesystems are enabled',
                        unmatch_nextline_next_matcher_name=(
                            'enablefilesystem_done'),
                        match_nextline_next_matcher_name=(
                            'setup_repositories')
                    ),
                    'setup_repositories': LineMatcher(
                        pattern=r'moving.*step.*reposetup',
                        progress=0.35,
                        message_template=(
                            'Setting up Customized Repositories'),
                        unmatch_nextline_next_matcher_name=(
                            'setup_repositories'),
                        match_nextline_next_matcher_name=(
                            'repositories_ready')
                    ),
                    'repositories_ready': LineMatcher(
                        pattern=r'leaving.*step.*reposetup',
                        progress=0.4,
                        message_template=(
                            'Customized Repositories setting up are done'),
                        unmatch_nextline_next_matcher_name=(
                            'repositories_ready'),
                        match_nextline_next_matcher_name='checking_dud'
                    ),
                    'checking_dud': LineMatcher(
                        pattern=r'moving.*step.*postselection',
                        progress=0.4,
                        message_template='Checking DUD modules',
                        unmatch_nextline_next_matcher_name='checking_dud',
                        match_nextline_next_matcher_name='dud_checked'
                    ),
                    'dud_checked': LineMatcher(
                        pattern=r'leaving.*step.*postselection',
                        progress=0.5,
                        message_template='Checking DUD modules are done',
                        unmatch_nextline_next_matcher_name='dud_checked',
                        match_nextline_next_matcher_name='installing_packages'
                    ),
                    'installing_packages': LineMatcher(
                        pattern=r'moving.*step.*installpackages',
                        progress=0.5,
                        message_template='Installing packages',
                        unmatch_nextline_next_matcher_name=(
                            'installing_packages'),
                        match_nextline_next_matcher_name=(
                            'packages_installed')
                    ),
                    'packages_installed': LineMatcher(
                        pattern=r'leaving.*step.*installpackages',
                        progress=0.8,
                        message_template='Packages are installed',
                        unmatch_nextline_next_matcher_name=(
                            'packages_installed'),
                        match_nextline_next_matcher_name=(
                            'installing_bootloader')
                    ),
                    'installing_bootloader': LineMatcher(
                        pattern=r'moving.*step.*instbootloader',
                        progress=0.9,
                        message_template='Installing bootloaders',
                        unmatch_nextline_next_matcher_name=(
                            'installing_bootloader'),
                        match_nextline_next_matcher_name=(
                            'bootloader_installed'),
                    ),
                    'bootloader_installed': LineMatcher(
                        pattern=r'leaving.*step.*instbootloader',
                        progress=1.0,
                        message_template='bootloaders is installed',
                        unmatch_nextline_next_matcher_name=(
                            'bootloader_installed'),
                        match_nextline_next_matcher_name='exit'
                    ),
                }
            ),
            FileMatcher(
                filename='install.log',
                min_progress=0.56,
                max_progress=0.80,
                line_matchers={
                    'start': LineMatcher(
                        pattern=r'Installing (?P<package>.*)',
                        progress=IncrementalProgress(0.0, 0.99, 0.005),
                        message_template='Installing %(package)s',
                        unmatch_sameline_next_matcher_name='package_complete',
                        unmatch_nextline_next_matcher_name='start',
                        match_nextline_next_matcher_name='start'
                    ),
                    'package_complete': LineMatcher(
                        pattern='FINISHED.*INSTALLING.*PACKAGES',
                        progress=1.0,
                        message_template='installing packages finished',
                        unmatch_nextline_next_matcher_name='start',
                        match_nextline_next_matcher_name='exit'
                    ),
                }
            ),
        ]
    ),
}


PACKAGE_INSTALLER_CONFIGURATIONS = {
    'openstack': AdapterItemMatcher(
        file_matchers=[
            FileMatcher(
                filename='chef-client.log',
                min_progress=0.1,
                max_progress=1.0,
                line_matchers={
                    'start': LineMatcher(
                        pattern=(
                            r'Processing\s*(?P<install_type>.*)'
                            r'\[(?P<package>.*)\].*'),
                        progress=IncrementalProgress(0.0, .90, 0.005),
                        message_template=(
                            'Processing %(install_type)s %(package)s'),
                        unmatch_sameline_next_matcher_name=(
                            'chef_complete'),
                        unmatch_nextline_next_matcher_name='start',
                        match_nextline_next_matcher_name='start'
                    ),
                    'chef_complete': LineMatcher(
                        pattern=r'Chef.*Run.*complete',
                        progress=1.0,
                        message_template='Chef run complete',
                        unmatch_nextline_next_matcher_name='start',
                        match_nextline_next_matcher_name='exit'
                    ),
                }
            ),
        ]
    ),
}

OS_ADAPTER_CONFIGURATIONS = [
    OSMatcher(
        os_installer_name='cobbler',
        os_pattern='CentOS.*',
        item_matcher=OS_INSTALLER_CONFIGURATIONS['CentOS'],
        min_progress=0.0,
        max_progress=1.0
    ),
    OSMatcher(
        os_installer_name='cobbler',
        os_pattern='Ubuntu.*',
        item_matcher=OS_INSTALLER_CONFIGURATIONS['Ubuntu'],
        min_progress=0.0,
        max_progress=1.0
    )
]

PACKAGE_ADAPTER_CONFIGURATIONS = [
    PackageMatcher(
        package_installer_name='chef.*',
        target_system='openstack',
        item_matcher=PACKAGE_INSTALLER_CONFIGURATIONS['openstack'],
        min_progress=0.0,
        max_progress=1.0
    )
]


def _get_os_adapter_matcher(os_installer, os_name):
    """Get OS adapter matcher by os name and installer name."""
    for configuration in OS_ADAPTER_CONFIGURATIONS:
        if configuration.match(os_installer, os_name):
            return configuration
        else:
            logging.debug('configuration %s does not match %s and %s',
                          configuration, os_name, os_installer)
    logging.error('No configuration found for os installer %s os %s',
                  os_installer, os_name)
    return None


def _get_package_adapter_matcher(package_installer, target_system):
    """Get package adapter matcher by pacakge name and installer name."""
    for configuration in PACKAGE_ADAPTER_CONFIGURATIONS:
        if configuration.match(package_installer, target_system):
            return configuration
        else:
            logging.debug('configuration %s does not match %s and %s',
                          configuration, target_system, package_installer)
    logging.error('No configuration found for package installer %s os %s',
                  package_installer, target_system)
    return None


def update_progress(
    os_installers, os_names, package_installers, target_systems,
    cluster_hosts
):
    """Update adapter installing progress.

    :param os_installers: cluster id to os installer name
    :param package_installers: cluster id to package installer name.
    :param cluster_hosts: clusters and hosts in each cluster to update.
    :param cluster_hosts: dict of int to list of int.
    """
    for clusterid, hostids in cluster_hosts.items():
        """
        adapter = _get_adapter_matcher(os_installers[clusterid],
                                       os_names[clusterid],
                                       package_installers[clusterid],
                                       target_systems[clusterid])
        if not adapter:
            continue

        adapter.update_progress(clusterid, hostids)
        """
        os_adapter = _get_os_adapter_matcher(
            os_installers[clusterid], os_names[clusterid]
        )
        package_adapter = _get_package_adapter_matcher(
            package_installers[clusterid],
            target_systems[clusterid]
        )
        if not (os_adapter or package_adapter):
            continue

        adapter = AdapterMatcher(os_adapter, package_adapter)
        adapter.update_progress(clusterid, hostids)
