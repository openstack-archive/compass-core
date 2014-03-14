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

"""test util module.

   .. moduleauthor:: Xiaodong Wang <xiaodongwang@huawei.com>
"""
import os
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from compass.db import database
from compass.utils import flags
from compass.utils import logsetting


class TestDatabase(unittest2.TestCase):
    """Test database actions."""

    def setUp(self):
        super(TestDatabase, self).setUp()
        logsetting.init()
        database.init('sqlite://')

    def tearDown(self):
        super(TestDatabase, self).tearDown()

    def test_init(self):
        database.init('sqlite:///tmp/app.db')
        self.assertEqual(str(database.ENGINE.url),
                         'sqlite:///tmp/app.db')
        self.assertEqual(str(database.SCOPED_SESSION.bind.url),
                         'sqlite:///tmp/app.db')

    def test_session(self):
        with database.session() as session:
            self.assertEqual(database.current_session(), session)
            self.assertTrue(database.in_session())

        self.assertFalse(database.in_session())


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
