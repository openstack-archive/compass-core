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


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from base import BaseTest
from compass.db.api import database
from compass.db.api import network
from compass.db.api import user as user_api
from compass.db import exception
from compass.utils import flags
from compass.utils import logsetting


class TestListSubnets(BaseTest):
    """Test list subnets."""

    def setUp(self):
        super(TestListSubnets, self).setUp()

    def tearDown(self):
        super(TestListSubnets, self).tearDown()

    def test_list_subnets(self):
        network.add_subnet(
            self.user_object,
            subnet='10.145.89.0/24'
        )
        list_subnet = network.list_subnets(
            self.user_object
        )
        expected = '10.145.89.0/24'
        self.assertTrue(
            item in list_subnet[0].items() for item in expected
        )


class TestGetSubnet(BaseTest):
    """Test get subnet."""

    def setUp(self):
        super(TestGetSubnet, self).setUp()

    def tearDown(self):
        super(TestGetSubnet, self).tearDown()

    def test_get_subnet(self):
        network.add_subnet(
            self.user_object,
            subnet='10.145.89.0/24'
        )
        get_subnet = network.get_subnet(
            self.user_object,
            1
        )
        self.assertEqual(
            '10.145.89.0/24',
            get_subnet['subnet']
        )

    def tset_get_subnet_no_exist(self):
        get_subnet_no_exist = network.get_subnet(
            self.user_object,
            2
        )
        self.assertEqual([], get_subnet_no_exist)


class TestAddSubnet(BaseTest):
    """Test add subnet."""

    def setUp(self):
        super(TestAddSubnet, self).setUp()

    def tearDown(self):
        super(TestAddSubnet, self).tearDown()

    def test_add_subnet(self):
        network.add_subnet(
            self.user_object,
            subnet='10.145.89.0/24'
        )
        add_subnets = network.list_subnets(
            self.user_object
        )
        expected = '10.145.89.0/24'
        for add_subnet in add_subnets:
            self.assertEqual(expected, add_subnet['subnet'])

    def test_add_subnet_position(self):
        network.add_subnet(
            self.user_object,
            True,
            '10.145.89.0/23'
        )
        add_subnets = network.list_subnets(
            self.user_object
        )
        expected = '10.145.89.0/23'
        for add_subnet in add_subnets:
            self.assertEqual(expected, add_subnet['subnet'])

    def test_add_subnet_session(self):
        with database.session() as session:
            network.add_subnet(
                self.user_object,
                subnet='10.145.89.0/22',
                session=session
            )
        add_subnets = network.list_subnets(
            self.user_object
        )
        expected = '10.145.89.0/22'
        for add_subnet in add_subnets:
            self.assertEqual(expected, add_subnet['subnet'])

    def test_add_subnet_position_session(self):
        with database.session() as session:
            network.add_subnet(
                self.user_object,
                True,
                '10.145.89.0/21',
                session
            )
        add_subnets = network.list_subnets(
            self.user_object
        )
        expected = '10.145.89.0/21'
        for add_subnet in add_subnets:
            self.assertEqual(expected, add_subnet['subnet'])


class TestUpdateSubnet(BaseTest):
    """Test update subnet."""

    def setUp(self):
        super(TestUpdateSubnet, self).setUp()

    def tearDown(self):
        super(TestUpdateSubnet, self).tearDown()

    def test_update_subnet(self):
        network.add_subnet(
            self.user_object,
            subnet='10.145.89.0/24'
        )
        network.update_subnet(
            self.user_object,
            1,
            subnet='192.168.100.0/24'
        )
        update_subnet = network.list_subnets(
            self.user_object
        )
        expected = '192.168.100.0/24'
        self.assertTrue(
            item in update_subnet[0].items() for item in expected
        )

    def test_update_subnet_no_exist(self):
        self.assertRaises(
            exception.DatabaseException,
            network.update_subnet,
            self.user_object,
            2
        )


class TestDelSubnet(BaseTest):
    """Test delete subnet."""

    def setUp(self):
        super(TestDelSubnet, self).setUp()

    def tearDown(self):
        super(TestDelSubnet, self).tearDown()

    def test_del_subnet(self):
        network.add_subnet(
            self.user_object,
            subnet='10.145.89.0/24'
        )
        network.del_subnet(
            self.user_object,
            1
        )
        del_subnet = network.list_subnets(
            self.user_object
        )
        self.assertEqual([], del_subnet)

    def test_del_subnet_not_exist(self):
        self.assertRaises(
            exception.RecordNotExists,
            network.del_subnet,
            self.user_object,
            2
        )


if __name__ == '__main__':
    flags.init()
    unittest2.main()
