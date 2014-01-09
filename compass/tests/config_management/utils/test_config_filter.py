import unittest2

from compass.config_management.utils import config_filter


class TestConfigFilter(unittest2.TestCase):
    def test_allows(self):
        config = {'1': '1',
                  '2': {'22': '22',
                        '33': {'333': '333',
                               '44': '444'}},
                  '3': {'33': '44'}}
        allows = ['*', '3', '5']
        filter = config_filter.ConfigFilter(allows)
        filtered_config = filter.filter(config)
        self.assertEqual(filtered_config, config)
        allows = ['/1', '2/22', '5']
        expected_config = {'1': '1', '2': {'22': '22'}}
        filter = config_filter.ConfigFilter(allows)
        filtered_config = filter.filter(config)
        self.assertEqual(filtered_config, expected_config)
        allows = ['*/33']
        expected_config = {'2': {'33': {'333': '333',
                                        '44': '444'}},
                           '3': {'33': '44'}}
        filter = config_filter.ConfigFilter(allows)
        filtered_config = filter.filter(config)
        self.assertEqual(filtered_config, expected_config)

    def test_denies(self):
        config = {'1': '1', '2': {'22': '22',
                                  '33': {'333': '333',
                                         '44': '444'}},
                            '3': {'33': '44'}}
        denies = ['/1', '2/22', '2/33/333', '5']
        expected_config = {'2': {'33': {'44': '444'}}, '3': {'33': '44'}}
        filter = config_filter.ConfigFilter(denies=denies)
        filtered_config = filter.filter(config)
        self.assertEqual(filtered_config, expected_config)
        denies = ['*']
        filter = config_filter.ConfigFilter(denies=denies)
        filtered_config = filter.filter(config)
        self.assertIsNone(filtered_config)
        denies = ['*/33']
        expected_config = {'1': '1', '2': {'22': '22'}}
        filter = config_filter.ConfigFilter(denies=denies)
        filtered_config = filter.filter(config)
        self.assertEqual(filtered_config, expected_config)


if __name__ == '__main__':
    unittest2.main()
