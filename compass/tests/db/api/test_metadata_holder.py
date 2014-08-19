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
import os
import unittest2

from base import BaseTest
from compass.db.api import adapter_holder as adapter
from compass.db.api import database
from compass.db.api import metadata_holder as metadata
from compass.db.api import user as user_api
from compass.db import exception
from compass.utils import flags
from compass.utils import logsetting
from compass.utils import setting_wrapper as setting


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


class TestGetPackageMetadata(BaseTest):
    """test get package metadata."""

    def setUp(self):
        super(TestGetPackageMetadata, self).setUp()

    def tearDown(self):
        super(TestGetPackageMetadata, self).tearDown()

    def test_get_package_metadata(self):
        adapter_object = adapter.list_adapters(self.user_object)
        package_metadata = metadata.get_package_metadata(
            self.user_object,
            adapter_object[0]['id']
        )
        self.assertIsNotNone(package_metadata)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
