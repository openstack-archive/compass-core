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


import datetime
import logging
import mock
import os
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from base import BaseTest
from compass.db.api import adapter as adapter_api
from compass.db.api import adapter_holder as adapter
from compass.db.api import database
from compass.db.api import metadata as metadata_api
from compass.db.api import metadata_holder as metadata
from compass.db.api import user as user_api
from compass.db import exception
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import util


class MetadataTestCase(unittest2.TestCase):
    """Metadata base test case."""

    def setUp(self):
        super(MetadataTestCase, self).setUp()
        reload(setting)
        setting.CONFIG_DIR = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'data'
        )
        database.init('sqlite://')
        database.create_db()
        adapter.load_adapters()
        metadata.load_metadatas()

        #Get a os_id and adapter_id
        self.user_object = (
            user_api.get_user_object(
                setting.COMPASS_ADMIN_EMAIL
            )
        )
        self.adapter_object = adapter.list_adapters(self.user_object)
        test_adapter = None
        for adapter_obj in self.adapter_object:
            if adapter_obj['name'] == 'openstack_icehouse':
                self.adapter_id = adapter_obj['id']
                test_adapter = adapter_obj
                break
        self.os_id = None
        if test_adapter['flavors']:
            for supported_os in test_adapter['supported_oses']:
                self.os_id = supported_os['os_id']
                break
            for flavor in test_adapter['flavors']:
                if flavor['name'] == 'HA-multinodes':
                    self.flavor_id = flavor['id']
                    break

    def tearDown(self):
        super(MetadataTestCase, self).setUp()
        reload(setting)
        database.drop_db()


class TestGetPackageMetadata(MetadataTestCase):

    def setUp(self):
        self.backup_load_configs = util.load_configs

        def mock_load_configs(config_dir, *args, **kwargs):
            if config_dir != setting.PACKAGE_METADATA_DIR:
                return self.backup_load_configs(
                    config_dir, *args, **kwargs
                )
            config = {
                'ADAPTER': 'openstack',
                'METADATA': {
                    'security': {
                        '_self': {
                            'required_in_whole_config': True
                        },
                        'service_credentials': {
                            '_self': {
                                'mapping_to': 'service_credentials'
                            },
                            '$service': {
                                'username': {
                                    '_self': {
                                        'is_required': True,
                                        'field': 'username',
                                        'mapping_to': 'username'
                                    }
                                },
                                'password': {
                                    '_self': {
                                        'is_required': True,
                                        'field': 'password',
                                        'mapping_to': 'password'
                                    }
                                }
                            }
                        }
                    },
                    'test_package_metadata': {
                        '_self': {
                            'dummy': 'fake'
                        }
                    }
                }
            }
            return [config]

        util.load_configs = mock.Mock(side_effect=mock_load_configs)
        super(TestGetPackageMetadata, self).setUp()

    def tearDown(self):
        util.load_configs = self.backup_load_configs
        super(TestGetPackageMetadata, self).tearDown()

    def test_get_package_metadata(self):
        """Test get package metadata."""
        package_metadata = metadata.get_package_metadata(
            self.adapter_id,
            user=self.user_object
        )
        expected = []
        for k, v in package_metadata['package_config'].iteritems():
            expected.append(k)
        self.assertIsNotNone(package_metadata)
        self.assertIn('test_package_metadata', expected)

    def test_adapter_not_exist(self):
        """Test give a non-exited package_id."""
        self.assertRaises(
            exception.RecordNotExists,
            metadata.get_package_metadata,
            99,
            user=self.user_object
        )


class TestGetOsMetadata(MetadataTestCase):
    def setUp(self):
        self.backup_load_configs = util.load_configs

        def mock_load_configs(config_dir, *args, **kwargs):
            if config_dir != setting.OS_METADATA_DIR:
                return self.backup_load_configs(
                    config_dir, *args, **kwargs
                )
            config = {
                'OS': 'general',
                'METADATA': {
                    'general': {
                        '_self': {
                            'required_in_whole_config': True
                        },
                        'language': {
                            '_self': {
                                'field': 'general',
                                'default_value': 'EN',
                                'options': ['EN', 'CN'],
                                'mapping_to': 'language'
                            }
                        },
                        'timezone': {
                            '_self': {
                                'field': 'general',
                                'default_value': 'UTC',
                                'options': [
                                    'America/New_York', 'America/Chicago',
                                    'America/Los_Angeles', 'Asia/Shanghai',
                                    'Asia/Tokyo', 'Europe/Paris',
                                    'Europe/London', 'Europe/Moscow',
                                    'Europe/Rome', 'Europe/Madrid',
                                    'Europe/Berlin', 'UTC'
                                ],
                                'mapping_to': 'timezone'
                            }
                        }
                    },
                    'test_os_metadata': {
                        '_self': {
                            'test': 'dummy'
                        }
                    }
                }
            }
            return [config]

        util.load_configs = mock.Mock(side_effect=mock_load_configs)
        super(TestGetOsMetadata, self).setUp()

    def tearDown(self):
        util.load_configs = self.backup_load_configs
        super(TestGetOsMetadata, self).tearDown()

    def test_get_os_metadata(self):
        """Test get os metadata."""
        os_metadata = metadata.get_os_metadata(
            self.os_id,
            user=self.user_object
        )
        expected = []
        for k, v in os_metadata['os_config'].iteritems():
            expected.append(k)
        self.assertIsNotNone(os_metadata)
        self.assertIn('test_os_metadata', expected)

    def test_os_non_exist(self):
        """Test give a non-existed os_id."""
        self.assertRaises(
            exception.RecordNotExists,
            metadata.get_os_metadata,
            99,
            user=self.user_object
        )


class TestGetFlavorMetadata(MetadataTestCase):
    def setUp(self):
        self.backup_load_configs = util.load_configs

        def mock_load_configs(config_dir, *args, **kwargs):
            if config_dir != setting.FLAVOR_METADATA_DIR:
                return self.backup_load_configs(
                    config_dir, *args, **kwargs
                )
            config = {
                'FLAVOR': 'HA-multinodes',
                'METADATA': {
                    'test_ha_proxy': {
                        '_self': {
                        },
                        'vip': {
                            '_self': {
                                'is_required': True,
                                'field': 'general',
                                'mapping_to': 'ha_vip'
                            }
                        }
                    }
                }
            }
            return [config]
        util.load_configs = mock.Mock(side_effect=mock_load_configs)
        super(TestGetFlavorMetadata, self).setUp()

    def tearDown(self):
        util.load_configs = self.backup_load_configs
        super(TestGetFlavorMetadata, self).tearDown()

    def test_get_flavor_metadata(self):
        flavor_metadata = metadata.get_flavor_metadata(
            self.flavor_id,
            user=self.user_object
        )
        self.assertIsNotNone(flavor_metadata)
        self.assertTrue(
            'test_ha_proxy' in flavor_metadata['flavor_config'].keys()
        )


class TestGetPackageOsMetadata(MetadataTestCase):
    def setUp(self):
        super(TestGetPackageOsMetadata, self).setUp()

    def tearDown(self):
        super(TestGetPackageOsMetadata, self).tearDown()

    def test_get_package_os_metadata(self):
        """Test get package and os metadata."""
        package_os_metadata = metadata.get_package_os_metadata(
            self.adapter_id,
            self.os_id,
            user=self.user_object
        )
        self.assertIsNotNone(package_os_metadata)

    def test_invalid_parameter(self):
        """Test give a non-existed os_id."""
        self.assertRaises(
            exception.InvalidParameter,
            metadata.get_package_os_metadata,
            self.adapter_id,
            99,
            user=self.user_object
        )


class TestListFlavors(MetadataTestCase):
    def setUp(self):
        super(TestListFlavors, self).setUp()

    def tesrDown(self):
        super(TestListFlavors, self).tearDown()

    def test_list_flavors(self):
        """Test list flavors."""
        flavors = metadata.list_flavors(
            user=self.user_object
        )
        flavor_name = []
        for flavor in flavors:
            flavor_name.append(flavor['name'])
        expected = [
            'allinone',
            'multiroles',
            'HA-multinodes',
            'single-contoller-multi-compute'
        ]
        for expect in expected:
            self.assertIn(expect, flavor_name)


class TestGetFlavors(MetadataTestCase):
    def setUp(self):
        super(TestGetFlavors, self).setUp()

    def tearDown(self):
        super(TestGetFlavors, self).tearDown()

    def test_get_flavor(self):
        """Test get a flavor."""
        flavor = metadata.get_flavor(
            self.flavor_id,
            user=self.user_object
        )
        expected = {
            'display_name': 'Multi-node Cluster with HA',
            'id': 3,
            'template': 'ha_multinodes.tmpl',
            'name': 'HA-multinodes'
        }
        self.assertTrue(
            all(item in flavor.items() for item in expected.items())
        )


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
