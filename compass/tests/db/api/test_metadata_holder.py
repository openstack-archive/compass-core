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

        #Get a os_id and adapter_id
        self.user_object = (
            user_api.get_user_object(
                setting.COMPASS_ADMIN_EMAIL
            )
        )
        self.adapter_object = adapter.list_adapters(self.user_object)
        self.adapter_id = self.adapter_object[0]['id']
        self.os_id = None
        if self.adapter_object[0]['flavors']:
            for supported_os in self.adapter_object[0]['supported_oses']:
                self.os_id = supported_os['os_id']
                break

    def tearDown(self):
        super(MetadataTestCase, self).setUp()
        reload(setting)
        database.drop_db()


class TestGetPackageMetadata(MetadataTestCase):

    def setUp(self):
        super(TestGetPackageMetadata, self).setUp()
        mock_config = mock.Mock()
        self.backup_package_configs = util.load_configs
        util.load_configs = mock_config
        configs = [{
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
        }]
        util.load_configs.return_value = configs
        with database.session() as session:
            metadata_api.add_package_metadata_internal(session)
        metadata.load_metadatas()

    def tearDown(self):
        util.load_configs = self.backup_package_configs
        super(TestGetPackageMetadata, self).tearDown()

    def test_get_package_metadata(self):
        """Test get package metadata."""
        package_metadata = metadata.get_package_metadata(
            self.user_object,
            self.adapter_id
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
            self.user_object,
            99
        )


class TestGetOsMetadata(MetadataTestCase):
    def setUp(self):
        super(TestGetOsMetadata, self).setUp()
        mock_config = mock.Mock()
        self.backup_os_configs = util.load_configs
        util.load_configs = mock_config
        configs = [{
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
        }]
        util.load_configs.return_value = configs
        with database.session() as session:
            metadata_api.add_os_metadata_internal(session)
        metadata.load_metadatas()

    def tearDown(self):
        super(TestGetOsMetadata, self).tearDown()
        util.load_configs = self.backup_os_configs

    def test_get_os_metadata(self):
        """Test get os metadata."""
        os_metadata = metadata.get_os_metadata(
            self.user_object,
            1
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
            self.user_object,
            99
        )


class TestGetPackageOsMetadata(MetadataTestCase):
    def setUp(self):
        super(TestGetPackageOsMetadata, self).setUp()

    def tearDown(self):
        super(TestGetPackageOsMetadata, self).tearDown()

    def test_get_package_os_metadata(self):
        """Test get package and os metadata."""
        package_os_metadata = metadata.get_package_os_metadata(
            self.user_object,
            self.adapter_id,
            self.os_id
        )
        self.assertIsNotNone(package_os_metadata)

    def test_invalid_parameter(self):
        """Test give a non-existed os_id."""
        self.assertRaises(
            exception.InvalidParameter,
            metadata.get_package_os_metadata,
            self.user_object,
            self.adapter_id,
            99
        )


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
