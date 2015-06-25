# Copyright 2014 Huawei Technologies Co. Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test base installer functionalities."""

import os
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as compass_setting
reload(compass_setting)


from compass.deployment.installers.installer import BaseInstaller
from compass.tests.deployment.test_data import config_data
from compass.utils import flags
from compass.utils import logsetting


class TestBaseInstaller(unittest2.TestCase):
    """Test base installer."""
    def setUp(self):
        super(TestBaseInstaller, self).setUp()
        self.test_installer = BaseInstaller()

    def tearDown(self):
        super(TestBaseInstaller, self).tearDown()
        del self.test_installer

    def test_get_tmpl_vars_from_metadata(self):
        test_cases = config_data.metadata_test_cases
        for case in test_cases:
            metadata = case["metadata"]
            config = case["config"]
            expected_output = case["expected_output"]

            output = self.test_installer.get_tmpl_vars_from_metadata(
                metadata, config
            )

            self.maxDiff = None
            self.assertDictEqual(expected_output, output)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
