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


from compass.utils import flags
from compass.utils import logsetting
from compass.utils import util


class TestDictMerge(unittest2.TestCase):
    """Test dict merge."""

    def setUp(self):
        super(TestDictMerge, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestDictMerge, self).tearDown()

    def test_simple_merge(self):
        """simple test of merge
           merge_dict performs in-place merge of rhs to lhs
        """
        lhs = {1: 1}
        rhs = {2: 2}
        util.merge_dict(lhs, rhs)
        self.assertEqual(lhs, {1: 1, 2: 2})

    def test_recursive_merge(self):
        """test merge recursively."""
        lhs = {1: {2: 3}}
        rhs = {1: {3: 4}}
        util.merge_dict(lhs, rhs)
        self.assertEqual(lhs, {1: {2: 3, 3: 4}})

    def test_merge_override(self):
        """test merge override."""
        lhs = {1: 1}
        rhs = {1: 2}
        util.merge_dict(lhs, rhs)
        self.assertEqual(lhs, {1: 2})

        lhs = {1: {2: 3, 3: 5}}
        rhs = {1: {2: 4, 4: 6}}
        util.merge_dict(lhs, rhs)
        self.assertEqual(lhs, {1: {2: 4, 3: 5, 4: 6}})

    def test_merge_not_override(self):
        """test merge not override."""
        lhs = {1: 1}
        rhs = {1: 2}
        util.merge_dict(lhs, rhs, False)
        self.assertEqual(lhs, {1: 1})

        lhs = {1: {2: 3, 3: 5}}
        rhs = {1: {2: 4, 4: 6}}
        util.merge_dict(lhs, rhs, False)
        self.assertEqual(lhs, {1: {2: 3, 3: 5, 4: 6}})

    def test_change_after_merge(self):
        """test change after merge."""
        lhs = {1: {2: 3}}
        rhs = {1: {3: [4, 5, 6]}}
        util.merge_dict(lhs, rhs)
        self.assertEqual(lhs, {1: {2: 3, 3: [4, 5, 6]}})
        self.assertEqual(rhs, {1: {3: [4, 5, 6]}})
        rhs[1][3].append(7)
        self.assertEqual(lhs, {1: {2: 3, 3: [4, 5, 6]}})
        self.assertEqual(rhs, {1: {3: [4, 5, 6, 7]}})

    def test_lhs_rhs_notdict(self):
        """test merge not dict."""
        lhs = [1, 2, 3]
        rhs = {1: 2}
        self.assertRaises(TypeError, util.merge_dict, (lhs, rhs))
        lhs = {1: 2}
        rhs = [1, 2, 3]
        self.assertRaises(TypeError, util.merge_dict, (lhs, rhs))


class TestOrderKeys(unittest2.TestCase):
    """test order keys."""

    def test_simple_order_keys(self):
        """test simple order keys."""
        keys = [1, 2, 3, 4, 5]
        orders = [3, 4, 5]
        ordered_keys = util.order_keys(keys, orders)
        self.assertEqual(ordered_keys, [3, 4, 5, 1, 2])

    def test_order_keys_with_dot(self):
        """test order keys with dot in it."""
        keys = [1, 2, 3, 4, 5]
        orders = [3, 4, '.', 5]
        ordered_keys = util.order_keys(keys, orders)
        self.assertEqual(ordered_keys, [3, 4, 1, 2, 5])

    def test_order_keys_with_multidot(self):
        """test order keys with multi dots in it."""
        keys = [1, 2, 3, 4, 5]
        orders = [3, '.', 4, '.', 5]
        ordered_keys = util.order_keys(keys, orders)
        self.assertEqual(ordered_keys, [3, 1, 2, 4, 5])

    def test_others_in_orders(self):
        """test other key in order."""
        keys = [1, 2, 3, 4, 5]
        orders = [3, '.', 5, 6]
        ordered_keys = util.order_keys(keys, orders)
        self.assertEqual(ordered_keys, [3, 1, 2, 4, 5])

    def test_keys_orders_notlist(self):
        """test keys not in order."""
        keys = {1: 1}
        orders = [3, 4, 5]
        self.assertRaises(TypeError, util.order_keys, keys, orders)

        keys = [1, 2, 3, 4, 5]
        orders = {3: 3}
        self.assertRaises(TypeError, util.order_keys, keys, orders)


class TestIsInstanceOf(unittest2.TestCase):
    """test isinstanceof function."""
    def test_isinstance(self):
        """test isinstance."""
        self.assertTrue(util.is_instance({}, [dict, list]))
        self.assertFalse(util.is_instance({}, [str, list]))
        self.assertFalse(util.is_instance({}, []))


class TestGetListWithPossibility(unittest2.TestCase):
    """test get list with possibility."""

    def test_simple_case(self):
        """test simple case."""
        lists = [['role1'], ['role2'], ['role3']]
        self.assertEqual(util.flat_lists_with_possibility(lists),
                         ['role1', 'role2', 'role3'])
        lists = [['role1', 'role1'], ['role2'], ['role3']]
        self.assertEqual(util.flat_lists_with_possibility(lists),
                         ['role1', 'role2', 'role3', 'role1'])
        lists = [['role1', 'role1', 'role1'], ['role2', 'role2'], ['role3']]
        self.assertEqual(util.flat_lists_with_possibility(lists),
                         ['role1', 'role2', 'role3',
                          'role1', 'role2', 'role1'])
        lists = [['role1', 'role1', 'role1', 'role1'],
                 ['role2', 'role2'], ['role3']]
        self.assertEqual(util.flat_lists_with_possibility(lists),
                         ['role1', 'role2', 'role3', 'role1',
                          'role1', 'role2', 'role1'])
        lists = [['role3'],
                 ['role2', 'role2'],
                 ['role1', 'role1', 'role1', 'role1']]
        self.assertEqual(util.flat_lists_with_possibility(lists),
                         ['role1', 'role2', 'role3', 'role1',
                          'role1', 'role2', 'role1'])


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
