import unittest2

from compass.utils import util


class TestDictMerge(unittest2.TestCase):
    def test_simple_merge(self):
        lhs = {1: 1}
        rhs = {2: 2}
        util.merge_dict(lhs, rhs)
        self.assertEqual(lhs, {1: 1, 2: 2})

    def test_recursive_merge(self):
        lhs = {1: {2: 3}}
        rhs = {1: {3: 4}}
        util.merge_dict(lhs, rhs)
        self.assertEqual(lhs, {1: {2: 3, 3: 4}})

    def test_merge_override(self):
        lhs = {1: 1}
        rhs = {1: 2}
        util.merge_dict(lhs, rhs)
        self.assertEqual(lhs, {1: 2})

        lhs = {1: {2: 3, 3: 5}}
        rhs = {1: {2: 4, 4: 6}}
        util.merge_dict(lhs, rhs)
        self.assertEqual(lhs, {1: {2: 4, 3: 5, 4: 6}})

    def test_merge_not_override(self):
        lhs = {1: 1}
        rhs = {1: 2}
        util.merge_dict(lhs, rhs, False)
        self.assertEqual(lhs, {1: 1})

        lhs = {1: {2: 3, 3: 5}}
        rhs = {1: {2: 4, 4: 6}}
        util.merge_dict(lhs, rhs, False)
        self.assertEqual(lhs, {1: {2: 3, 3: 5, 4: 6}})

    def test_change_after_merge(self):
        lhs = {1: {2: 3}}
        rhs = {1: {3: [4, 5, 6]}}
        util.merge_dict(lhs, rhs)
        self.assertEqual(lhs, {1: {2: 3, 3: [4, 5, 6]}})
        self.assertEqual(rhs, {1: {3: [4, 5, 6]}})
        rhs[1][3].append(7)
        self.assertEqual(lhs, {1: {2: 3, 3: [4, 5, 6]}})
        self.assertEqual(rhs, {1: {3: [4, 5, 6, 7]}})

    def test_lhs_rhs_notdict(self):
        lhs = [1, 2, 3]
        rhs = {1: 2}
        self.assertRaises(TypeError, util.merge_dict, (lhs, rhs))
        lhs = {1: 2}
        rhs = [1, 2, 3]
        self.assertRaises(TypeError, util.merge_dict, (lhs, rhs))


class TestOrderKeys(unittest2.TestCase):
    def test_simple_order_keys(self):
        keys = [1, 2, 3, 4, 5]
        orders = [3, 4, 5]
        ordered_keys = util.order_keys(keys, orders)
        self.assertEqual(ordered_keys, [3, 4, 5, 1, 2])

    def test_order_keys_with_dot(self):
        keys = [1, 2, 3, 4, 5]
        orders = [3, 4, '.', 5]
        ordered_keys = util.order_keys(keys, orders)
        self.assertEqual(ordered_keys, [3, 4, 1, 2, 5])

    def test_order_keys_with_multidot(self):
        keys = [1, 2, 3, 4, 5]
        orders = [3, '.', 4, '.', 5]
        ordered_keys = util.order_keys(keys, orders)
        self.assertEqual(ordered_keys, [3, 1, 2, 4, 5])

    def test_others_in_orders(self):
        keys = [1, 2, 3, 4, 5]
        orders = [3, '.', 5, 6]
        ordered_keys = util.order_keys(keys, orders)
        self.assertEqual(ordered_keys, [3, 1, 2, 4, 5])

    def test_keys_orders_notlist(self):
        keys = {1: 1}
        orders = [3, 4, 5]
        self.assertRaises(TypeError, util.order_keys, keys, orders)

        keys = [1, 2, 3, 4, 5]
        orders = {3: 3}
        self.assertRaises(TypeError, util.order_keys, keys, orders)


class TestIsInstanceOf(unittest2.TestCase):
    def test_isinstance(self):
        self.assertTrue(util.is_instance({}, [dict, list]))
        self.assertFalse(util.is_instance({}, [str, list]))
        self.assertFalse(util.is_instance({}, []))


class TestGetListWithPossibility(unittest2.TestCase):
    def test_simple_case(self):
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
    unittest2.main()
