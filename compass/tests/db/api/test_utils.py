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

import logging
import os
import unittest2


os.environ['COMPASS_IGNORE_SETTING'] = 'true'


from compass.utils import setting_wrapper as setting
reload(setting)


from compass.db.api import database
from compass.db.api import utils
from compass.db import exception
from compass.db import models

from compass.utils import flags
from compass.utils import logsetting


class TestModelQuery(unittest2.TestCase):
    """Test model query."""

    def setUp(self):
        super(TestModelQuery, self).setUp()
        os.environ['COMPASS_IGNORE_SETTING'] = 'true'
        os.environ['COMPASS_CONFIG_DIR'] = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'data'
        )
        reload(setting)
        database.init('sqlite://')

    def tearDown(self):
        reload(setting)
        super(TestModelQuery, self).tearDown()

    def test_model_query(self):
        with database.session() as session:
            model = models.Machine
            res = utils.model_query(session, model)
            self.assertIsNotNone(res)

    def test_model_query_non_exist(self):
        with database.session() as session:
            self.assertRaises(
                exception.DatabaseException,
                utils.model_query,
                session,
                models.JSONEncoded
            )


class TestModelFilter(unittest2.TestCase):
    """Test model filter"""

    def setUp(self):
        super(TestModelFilter, self).setUp()
        os.environ['COMPASS_IGNORE_SETTING'] = 'true'
        os.environ['COMPASS_CONFIG_DIR'] = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'data'
        )
        reload(setting)
        database.init('sqlite://')
        database.create_db()

    def tearDown(self):
        database.drop_db()
        reload(setting)
        super(TestModelFilter, self).tearDown()

    def _filter_test_dict_util(self, op, exp_name, exp_id, **kwargs):
        with database.session() as session:
            query = utils.model_query(session, models.Permission)
            filters = {}
            for key, value in kwargs.iteritems():
                filters[key] = {
                    op: value
                }
            resources = utils.model_filter(query, models.Permission, **filters)
            ret = [resource.to_dict() for resource in resources.all()]
            expected = {
                'name': exp_name,
                'id': exp_id
            }
            return (expected, ret)

    def test_filter_with_list(self):
        with database.session() as session:
            query = utils.model_query(session, models.Permission)
            filters = {
                'name': [
                    'list_permissions',
                    'list_switches'
                ]
            }
            resources = utils.model_filter(query, models.Permission, **filters)
            ret = [resource.to_dict() for resource in resources.all()]
            expected = [
                {
                    'description': 'list all permissions',
                    'alias': 'list permissions',
                    'id': 1,
                    'name': 'list_permissions'
                },
                {
                    'description': 'list all switches',
                    'alias': 'list switches',
                    'id': 2,
                    'name': u'list_switches'
                }
            ]
            for i, v in enumerate(ret):
                self.assertTrue(
                    all(item in ret[i].items() for item in expected[i].items())
                )

    def test_filter_with_dict_eq(self):
        expected, ret = self._filter_test_dict_util(
            'eq',
            'list_permissions',
            1,
            id=1
        )
        self.assertTrue(
            all(item in ret[0].items() for item in expected.items())
        )

    def test_filter_with_dict_lt(self):
        expected, ret = self._filter_test_dict_util(
            'lt',
            'list_permissions',
            1,
            id=2
        )
        self.assertTrue(
            all(item in ret[0].items() for item in expected.items())
        )

    def test_filter_with_dict_gt(self):
        expected, ret = self._filter_test_dict_util(
            'gt',
            'update_clusterhost_state',
            49,
            id=48
        )
        self.assertTrue(
            all(item in ret[0].items() for item in expected.items())
        )

    def test_filter_with_dict_le(self):
        expected, ret = self._filter_test_dict_util(
            'le',
            'list_permissions',
            1,
            id=1
        )
        self.assertTrue(
            all(item in ret[0].items() for item in expected.items())
        )

    def test_filter_with_dict_ge(self):
        expected, ret = self._filter_test_dict_util(
            'ge',
            'update_clusterhost_state',
            49,
            id=49
        )
        logging.debug('expected: %s', expected)
        logging.debug('ret: %s', ret)
        self.assertTrue(
            all(item in ret[0].items() for item in expected.items())
        )

    def test_filter_with_dict_ne(self):
        expected, ret = self._filter_test_dict_util(
            'ne',
            'list_permissions',
            1,
            id=[2, 3, 4, 5, 6, 7, 8, 9]
        )
        self.assertTrue(
            all(item in ret[0].items() for item in expected.items())
        )

    def test_filter_with_dict_startswith(self):
        expected, ret = self._filter_test_dict_util(
            'startswith',
            'list_permissions',
            1,
            name='list_per'
        )
        self.assertTrue(
            all(item in ret[0].items() for item in expected.items())
        )

    def test_filter_with_dict_endswith(self):
        expected, ret = self._filter_test_dict_util(
            'endswith',
            'list_permissions',
            1,
            name='ssions'
        )
        self.assertTrue(
            all(item in ret[0].items() for item in expected.items())
        )

    def test_filter_with_dict_like(self):
        expected, ret = self._filter_test_dict_util(
            'like',
            'list_permissions',
            1,
            name='%per%'
        )
        self.assertTrue(
            all(item in ret[0].items() for item in expected.items())
        )

    def test_filter_with_dict_between_one_table(self):
        expected, ret = self._filter_test_dict_util(
            'between',
            'list_permissions',
            1,
            id=(1, 1)
        )
        self.assertTrue(
            all(item in ret[0].items() for item in expected.items())
        )

    def test_filter_with_dict_between_multiple_tables(self):
        _, ret = self._filter_test_dict_util(
            'between',
            'list_permissions',
            1,
            id=(3, 6)
        )
        key_list = []
        for item in ret:
            for k, v in item.iteritems():
                if k == 'id':
                    key_list.append(v)

        self.assertEqual([3, 4, 5, 6], key_list)

    def test_filter_with_other_type(self):
        with database.session() as session:
            query = utils.model_query(session, models.Permission)
            filters = {
                'id': 1
            }
            resources = utils.model_filter(query, models.Permission, **filters)
            ret = [resource.to_dict() for resource in resources.all()]
            expected = {
                'id': 1
            }
            self.assertTrue(
                all(item in ret[0].items() for item in expected.items())
            )


class TestGetDbObject(unittest2.TestCase):
    def setUp(self):
        super(TestGetDbObject, self).setUp()
        os.environ['COMPASS_IGNORE_SETTING'] = 'true'
        os.environ['COMPASS_CONFIG_DIR'] = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'data'
        )
        reload(setting)
        database.init('sqlite://')
        database.create_db()

    def tearDown(self):
        database.drop_db()
        reload(setting)
        super(TestGetDbObject, self).tearDown()

    def test_get_alias(self):
        with database.session() as session:
            machines = utils.get_db_object(
                session,
                models.Permission,
                name='list_machines'
            )
            expected = 'list machines'
            self.assertEqual(expected, machines.alias)
            self.assertEqual(expected, machines.description)

    def test_get_none_with_flag_off(self):
        with database.session() as session:
            dummy = utils.get_db_object(
                session,
                models.Permission,
                False,
                name='dummy'
            )
            self.assertEqual(None, dummy)

    def test_get_none_with_flag_on(self):
        with self.assertRaises(exception.RecordNotExists):
            with database.session() as session:
                utils.get_db_object(
                    session,
                    models.Permission,
                    name='dummy'
                )


class TestAddDbObject(unittest2.TestCase):
    def setUp(self):
        super(TestAddDbObject, self).setUp()
        os.environ['COMPASS_IGNORE_SETTING'] = 'true'
        os.environ['COMPASS_CONFIG_DIR'] = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'data'
        )
        reload(setting)
        database.init('sqlite://')
        database.create_db()

    def tearDown(self):
        database.drop_db()
        reload(setting)
        super(TestAddDbObject, self).tearDown()

    def test_add_alias(self):
        with database.session() as session:
            db_objs = utils.add_db_object(
                session,
                models.Permission,
                True,
                'test',
                alias='test'
            )
            expected = 'test'
            self.assertEqual(expected, db_objs.alias)

    def test_add_nothing(self):
        with database.session() as session:
            db_objs = utils.add_db_object(
                session,
                models.Permission,
                True,
                'test'
            )
            self.assertEqual('test', db_objs.name)
            self.assertIsNone(db_objs.alias)

    def test_add_duplicate_with_flag(self):
        with self.assertRaises(exception.DuplicatedRecord):
            with database.session() as session:
                utils.add_db_object(
                    session,
                    models.Permission,
                    True,
                    'test',
                    alias='test'
                )
                utils.add_db_object(
                    session,
                    models.Permission,
                    True,
                    'test',
                    alias='test'
                )

    def test_add_duplicate_with_no_flag(self):
        with database.session() as session:
            db_objs = utils.add_db_object(
                session,
                models.Permission,
                False,
                'test',
                alias='test'
            )
            duplicate = utils.add_db_object(
                session,
                models.Permission,
                False,
                'test',
                alias='test'
            )
            self.assertEqual(duplicate, db_objs)

    def test_add_with_invalid_args(self):
        with self.assertRaises(exception.InvalidParameter):
            with database.session() as session:
                utils.add_db_object(
                    session,
                    models.Permission,
                    True,
                    'test1',
                    'test2',
                    name='test1'
                )

    def test_add_with_multiple_args(self):
        with database.session() as session:
            db_permission = utils.add_db_object(
                session,
                models.Permission,
                False,
                'test',
                alias='test'
            )
            db_user = utils.add_db_object(
                session,
                models.User,
                False,
                'test@huawei.com',
                password='test'
            )
            db_objs = utils.add_db_object(
                session,
                models.UserPermission,
                True,
                db_user.id,
                db_permission.id
            )
            self.assertEqual(db_user.id, db_objs.user_id)
            self.assertEqual(db_permission.id, db_objs.permission_id)


class TestListDbObjects(unittest2.TestCase):
    def setUp(self):
        super(TestListDbObjects, self).setUp()
        os.environ['COMPASS_IGNORE_SETTING'] = 'true'
        os.environ['COMPASS_CONFIG_DIR'] = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'data'
        )
        reload(setting)
        database.init('sqlite://')
        database.create_db()

    def tearDown(self):
        database.drop_db()
        reload(setting)
        super(TestListDbObjects, self).tearDown()

    def test_list_specific_obj(self):
        with database.session() as session:
            db_objs = utils.list_db_objects(
                session,
                models.Permission,
                name='list_permissions'
            )
            self.assertEqual(
                'list permissions',
                db_objs[0].alias
            )

    def test_list_specfic_objs(self):
        with database.session() as session:
            db_objs = utils.list_db_objects(
                session,
                models.Permission,
                name=[
                    'list_permissions',
                    'list_machines'
                ]
            )
            self.assertEqual(
                ['list_permissions', 'list_machines'].sort(),
                [obj.name for obj in db_objs].sort()
            )

    def test_list_none_objs(self):
        with database.session() as session:
            db_objs = utils.list_db_objects(
                session,
                models.Permission,
                id=99
            )
            self.assertListEqual([], db_objs)

    def test_list_none_table(self):
        with self.assertRaises(exception.DatabaseException):
            with database.session() as session:
                utils.list_db_objects(
                    session,
                    models.Dummy,
                )


class TestDelDbObjects(unittest2.TestCase):
    def setUp(self):
        super(TestDelDbObjects, self).setUp()
        os.environ['COMPASS_IGNORE_SETTING'] = 'true'
        os.environ['COMPASS_CONFIG_DIR'] = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'data'
        )
        reload(setting)
        database.init('sqlite://')
        database.create_db()

    def tearDown(self):
        database.drop_db()
        reload(setting)
        super(TestDelDbObjects, self).tearDown()

    def test_del_all_objects(self):
        with database.session() as session:
            utils.del_db_objects(
                session,
                models.Permission
            )
            remained = utils.list_db_objects(
                session,
                models.Permission
            )
            self.assertListEqual([], remained)

    def test_del_single_object(self):
        with database.session() as session:
            utils.del_db_objects(
                session,
                models.Permission,
                name='list_permissions'
            )
            query_deleted = utils.list_db_objects(
                session,
                models.Permission,
                name='list_permissions'
            )
            self.assertListEqual([], query_deleted)


class TestUpdateDbObject(unittest2.TestCase):
    def setUp(self):
        super(TestUpdateDbObject, self).setUp()
        os.environ['COMPASS_IGNORE_SETTING'] = 'true'
        os.environ['COMPASS_CONFIG_DIR'] = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'data'
        )
        reload(setting)
        database.init('sqlite://')
        database.create_db()

    def tearDown(self):
        database.drop_db()
        reload(setting)
        super(TestUpdateDbObject, self).tearDown()

    def test_update_db_object(self):
        with database.session() as session:
            db_obj = utils.get_db_object(
                session,
                models.Permission,
                id=1
            )
            updated_obj = utils.update_db_object(
                session,
                db_obj,
                alias='updated'
            )
            self.assertEqual(
                'updated',
                updated_obj.alias
            )

    def test_update_db_obj_none_exist(self):
        with self.assertRaises(exception.DatabaseException):
            with database.session() as session:
                db_obj = utils.get_db_object(
                    session,
                    models.Permission,
                    id=1000
                )
                utils.update_db_object(
                    session,
                    db_obj,
                    name='dummy'
                )


class TestDelDbObject(unittest2.TestCase):
    def setUp(self):
        super(TestDelDbObject, self).setUp()
        os.environ['COMPASS_IGNORE_SETTING'] = 'true'
        os.environ['COMPASS_CONFIG_DIR'] = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'data'
        )
        reload(setting)
        database.init('sqlite://')
        database.create_db()

    def tearDown(self):
        database.drop_db()
        reload(setting)
        super(TestDelDbObject, self).tearDown()

    def test_del_db_object(self):
        with self.assertRaises(exception.RecordNotExists):
            with database.session() as session:
                db_obj = utils.get_db_object(
                    session,
                    models.Permission,
                    id=1
                )
                utils.del_db_object(
                    session,
                    db_obj
                )
                utils.get_db_object(
                    session,
                    models.Permission,
                    id=1
                )


class TestCheckIp(unittest2.TestCase):
    def setUp(self):
        super(TestCheckIp, self).setUp()
        os.environ['COMPASS_IGNORE_SETTING'] = 'true'
        os.environ['COMPASS_CONFIG_DIR'] = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'data'
        )
        reload(setting)
        database.init('sqlite://')
        database.create_db()

    def tearDown(self):
        database.drop_db()
        reload(setting)
        super(TestCheckIp, self).tearDown()

    def test_check_ip_correct(self):
        ip = '10.1.1.1'
        self.assertIsNone(utils.check_ip(ip))

    def test_check_ip_incorrect(self):
        ip = 'dummy'
        self.assertRaises(
            exception.InvalidParameter,
            utils.check_ip,
            ip
        )


class TestCheckMac(unittest2.TestCase):
    def setUp(self):
        super(TestCheckMac, self).setUp()
        os.environ['COMPASS_IGNORE_SETTING'] = 'true'
        os.environ['COMPASS_CONFIG_DIR'] = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'data'
        )
        reload(setting)
        database.init('sqlite://')
        database.create_db()

    def tearDown(self):
        database.drop_db()
        reload(setting)
        super(TestCheckMac, self).tearDown()

    def test_check_mac_correct(self):
        mac = '00:01:02:03:04:05'
        self.assertIsNone(utils.check_mac(mac))

    def test_check_mac_incorrect(self):
        mac = '00:01'
        self.assertRaises(
            exception.InvalidParameter,
            utils.check_mac,
            mac
        )


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
