"""test config translator module"""
import functools
import unittest2

from compass.config_management.utils import config_translator
from compass.config_management.utils import config_translator_callbacks
from compass.utils import flags
from compass.utils import logsetting


class TestConfigTranslatorFunctions(unittest2.TestCase):
    """test config translator class"""

    def setUp(self):
        super(TestConfigTranslatorFunctions, self).setUp()
        logsetting.init()

    def tearDown(self):
        super(TestConfigTranslatorFunctions, self).tearDown()

    def test_translate_1(self):
        """config translate test"""
        config = {
            'networking': {
                'interfaces': {
                    'management': {
                        'mac': '00:00:00:01:02:03',
                        'ip': '192.168.1.1',
                        'netmask': '255.255.255.0',
                        'promisc': 0,
                        'nic': 'eth0',
                        'gateway': '2.3.4.5',
                        'dns_alias': 'hello.ods.com',
                    },
                    'floating': {
                        'promisc': 1,
                        'nic': 'eth1',
                    },
                    'storage': {
                        'ip': '172.16.1.1',
                        'nic': 'eth2',
                    },
                    'tenant': {
                        'ip': '10.1.1.1',
                        'netmask': '255.255.0.0',
                        'nic': 'eth0',
                    },
                },
                'global': {
                    'name_servers': ['nameserver.ods.com'],
                    'search_path': 'ods.com',
                    'gateway': '10.0.0.1',
                    'proxy': 'http://1.2.3.4:3128',
                    'ntp_server': '1.2.3.4',
                    'ignore_proxy': '127.0.0.1',
                },
            },
        }
        expected_config = {
            'name_servers_search': 'ods.com',
            'gateway': '10.0.0.1',
            'modify_interface': {
                'dnsname-eth0': 'hello.ods.com',
                'ipaddress-eth2': '172.16.1.1',
                'static-eth2': True,
                'static-eth1': True,
                'static-eth0': True,
                'netmask-eth0': '255.255.255.0',
                'ipaddress-eth0': '192.168.1.1',
                'macaddress-eth0': '00:00:00:01:02:03',
                'management-eth2': False,
                'management-eth0': True,
                'management-eth1': False
            },
            'ksmeta': {
                'promisc_nics': 'eth1',
                'ntp_server': '1.2.3.4',
                'proxy': 'http://1.2.3.4:3128',
                'ignore_proxy': '127.0.0.1'
            }
        }
        translator = config_translator.ConfigTranslator(
            mapping={
                '/networking/global/gateway': [
                    config_translator.KeyTranslator(
                        translated_keys=['/gateway']
                    )
                ],
                '/networking/global/nameservers': [
                    config_translator.KeyTranslator(
                        translated_keys=['/name_servers']
                    )
                ],
                '/networking/global/search_path': [
                    config_translator.KeyTranslator(
                        translated_keys=['/name_servers_search']
                    )
                ],
                '/networking/global/proxy': [
                    config_translator.KeyTranslator(
                        translated_keys=['/ksmeta/proxy']
                    )
                ],
                '/networking/global/ignore_proxy': [
                    config_translator.KeyTranslator(
                        translated_keys=['/ksmeta/ignore_proxy']
                    )
                ],
                '/networking/global/ntp_server': [
                    config_translator.KeyTranslator(
                        translated_keys=['/ksmeta/ntp_server']
                    )
                ],
                '/security/server_credentials/username': [
                    config_translator.KeyTranslator(
                        translated_keys=['/ksmeta/username']
                    )
                ],
                '/security/server_credentials/password': [
                    config_translator.KeyTranslator(
                        translated_keys=['/ksmeta/password'],
                        translated_value=(
                            config_translator_callbacks.get_encrypted_value)
                    )
                ],
                '/partition': [
                    config_translator.KeyTranslator(
                        translated_keys=['/ksmeta/partition']
                    )
                ],
                '/networking/interfaces/*/mac': [
                    config_translator.KeyTranslator(
                        translated_keys=[functools.partial(
                            config_translator_callbacks.get_key_from_pattern,
                            to_pattern='/modify_interface/macaddress-%(nic)s'
                        )],
                        from_keys={'nic': '../nic'},
                        override=functools.partial(
                            config_translator_callbacks.override_path_has,
                            should_exist='management')
                    )
                ],
                '/networking/interfaces/*/ip': [
                    config_translator.KeyTranslator(
                        translated_keys=[functools.partial(
                            config_translator_callbacks.get_key_from_pattern,
                            to_pattern='/modify_interface/ipaddress-%(nic)s')],
                        from_keys={'nic': '../nic'},
                        override=functools.partial(
                            config_translator_callbacks.override_path_has,
                            should_exist='management')
                    )
                ],
                '/networking/interfaces/*/netmask': [
                    config_translator.KeyTranslator(
                        translated_keys=[functools.partial(
                            config_translator_callbacks.get_key_from_pattern,
                            to_pattern='/modify_interface/netmask-%(nic)s')],
                        from_keys={'nic': '../nic'},
                        override=functools.partial(
                            config_translator_callbacks.override_path_has,
                            should_exist='management')
                    )
                ],
                '/networking/interfaces/*/dns_alias': [
                    config_translator.KeyTranslator(
                        translated_keys=[functools.partial(
                            config_translator_callbacks.get_key_from_pattern,
                            to_pattern='/modify_interface/dnsname-%(nic)s')],
                        from_keys={'nic': '../nic'},
                        override=functools.partial(
                            config_translator_callbacks.override_path_has,
                            should_exist='management')
                    )
                ],
                '/networking/interfaces/*/nic': [
                    config_translator.KeyTranslator(
                        translated_keys=[functools.partial(
                            config_translator_callbacks.get_key_from_pattern,
                            to_pattern='/modify_interface/static-%(nic)s')],
                        from_keys={'nic': '../nic'},
                        translated_value=True,
                        override=functools.partial(
                            config_translator_callbacks.override_path_has,
                            should_exist='management'),
                    ), config_translator.KeyTranslator(
                        translated_keys=[functools.partial(
                            config_translator_callbacks.get_key_from_pattern,
                            to_pattern='/modify_interface/management-%(nic)s'
                        )],
                        from_keys={'nic': '../nic'},
                        translated_value=functools.partial(
                            config_translator_callbacks.override_path_has,
                            should_exist='management'),
                        override=functools.partial(
                            config_translator_callbacks.override_path_has,
                            should_exist='management')
                    ), config_translator.KeyTranslator(
                        translated_keys=['/ksmeta/promisc_nics'],
                        from_values={'condition': '../promisc'},
                        translated_value=config_translator_callbacks.add_value,
                        override=True,
                    )
                ],
            }
        )

        translated_config = translator.translate(config)
        self.assertEqual(translated_config, expected_config)

    def test_translate_2(self):
        """config translate test"""
        translator = config_translator.ConfigTranslator(
            mapping={
                '/networking/interfaces/management/ip': [
                    config_translator.KeyTranslator(
                        translated_keys=[
                            '/db/mysql/bind_address',
                            '/mq/rabbitmg/bind_address',
                            '/mq/rabbitmq/bind_address',
                            '/endpoints/compute/metadata/host',
                            '/endpoints/compute/novnc/host',
                            '/endpoints/compute/service/host',
                            '/endpoints/compute/xvpvnc/host',
                            '/endpoints/ec2/admin/host',
                            '/endpoints/ec2/service/host',
                            '/endpoints/identity/admin/host',
                            '/endpoints/identity/service/host',
                            '/endpoints/image/registry/host',
                            '/endpoints/image/service/host',
                            '/endpoints/metering/service/host',
                            '/endpoints/network/service/host',
                            '/endpoints/volume/service/host',
                        ],
                        translated_value=(
                            config_translator_callbacks.get_value_if),
                        from_values={'condition': '/has_dashboard_roles'},
                        override=config_translator_callbacks.override_if_any,
                        override_conditions={
                            'has_dashboard_roles': '/has_dashboard_roles'}
                    )
                ],
            }
        )
        config1 = {
            'networking': {
                'interfaces': {
                    'management': {
                        'ip': '1.2.3.4',
                    },
                },
            },
            'has_dashboard_roles': True,
        }
        expected_config1 = {
            'db': {
                'mysql': {
                    'bind_address': '1.2.3.4'
                }
            },
            'endpoints': {
                'compute': {
                    'novnc': {
                        'host': '1.2.3.4'
                    },
                    'xvpvnc': {
                        'host': '1.2.3.4'
                    },
                    'service': {
                        'host': '1.2.3.4'
                    },
                    'metadata': {
                        'host': '1.2.3.4'
                    }
                },
                'network': {
                    'service': {
                        'host': '1.2.3.4'
                    }
                },
                'image': {
                    'registry': {
                        'host': '1.2.3.4'
                    },
                    'service': {
                        'host': '1.2.3.4'
                    }
                },
                'metering': {
                    'service': {
                        'host': '1.2.3.4'
                    }
                },
                'volume': {
                    'service': {
                        'host': '1.2.3.4'
                    }
                },
                'ec2': {
                    'admin': {
                        'host': '1.2.3.4'
                    },
                    'service': {
                        'host': '1.2.3.4'
                    }
                },
                'identity': {
                    'admin': {
                        'host': '1.2.3.4'
                    },
                    'service': {
                        'host': '1.2.3.4'
                    }
                }
            },
            'mq': {
                'rabbitmg': {
                    'bind_address': '1.2.3.4'
                },
                'rabbitmq': {
                    'bind_address': '1.2.3.4'
                }
            }
        }
        translated_config1 = translator.translate(config1)
        self.assertEqual(translated_config1, expected_config1)

        config2 = {
            'networking': {
                'interfaces': {
                    'management': {
                        'ip': '1.2.3.4',
                    },
                },
            },
            'has_dashboard_roles': False,
        }

        expected_config2 = None
        translated_config2 = translator.translate(config2)
        print translated_config2
        self.assertEqual(translated_config2, expected_config2)


if __name__ == '__main__':
    flags.init()
    logsetting.init()
    unittest2.main()
