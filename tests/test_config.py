# -*- encoding: utf-8 -*-

from linxo import config
import unittest
import mock
import os

M_CONFIG_PATH = [
    './tests/fixtures/linxo.conf',
]

M_CUSTOM_CONFIG_PATH = './tests/fixtures/custom_linxo.conf'


class testConfig(unittest.TestCase):
    def setUp(self):
        """Overload configuration lookup path"""
        self._orig_CONFIG_PATH = config.CONFIG_PATH
        config.CONFIG_PATH = M_CONFIG_PATH

    def tearDown(self):
        """Restore configuraton lookup path"""
        config.CONFIG_PATH = self._orig_CONFIG_PATH

    def test_real_lookup_path(self):
        home = os.environ['HOME']
        pwd = os.environ['PWD']

        self.assertEqual(['{0}/linxo.conf'.format(pwd),
                          '{0}/.linxo.conf'.format(home),
                          '/etc/linxo.conf'], self._orig_CONFIG_PATH)

    def test_config_get_conf(self):
        conf = config.ConfigurationManager()

        self.assertEqual('prod', conf.get('default', 'endpoint'))
        self.assertEqual('default client_id', conf.get('prod', 'client_id'))
        self.assertEqual('default client_secret', conf.get('prod', 'client_secret'))
        self.assertEqual('default access_token', conf.get('prod', 'access_token'))
        self.assertEqual('default refresh_token', conf.get('prod', 'refresh_token'))

        self.assertEqual('sandbox client_id', conf.get('sandbox', 'client_id'))
        self.assertEqual('sandbox client_secret', conf.get('sandbox', 'client_secret'))
        self.assertEqual('sandbox access_token', conf.get('sandbox', 'access_token'))
        self.assertEqual('sandbox refresh_token', conf.get('sandbox', 'refresh_token'))

        self.assertTrue(conf.get('prod', 'non-existent') is None)
        self.assertTrue(conf.get('non-existant', 'client_id') is None)

        conf.set('prod', 'client_id', 'new client_id')
        conf.write()

        conf2 = config.ConfigurationManager()
        self.assertEqual('new client_id', conf2.get('prod', 'client_id'))
        conf2.set('prod', 'client_id', 'default client_id')
        conf2.write()

    def test_config_get_custom_conf(self):
        conf = config.ConfigurationManager()
        conf.read(M_CUSTOM_CONFIG_PATH)

        self.assertEqual('sandbox', conf.get('default', 'endpoint'))
        self.assertEqual('custom client_id', conf.get('sandbox', 'client_id'))
        self.assertEqual('custom client_secret', conf.get('sandbox', 'client_secret'))
        self.assertEqual('custom access_token', conf.get('sandbox', 'access_token'))
        self.assertEqual('custom refresh_token', conf.get('sandbox', 'refresh_token'))
        self.assertTrue(conf.get('prod', 'non-existent') is None)

        conf.set('sandbox', 'client_id', 'new client_id')
        conf.write()

        conf2 = config.ConfigurationManager()
        conf2.read(M_CUSTOM_CONFIG_PATH)
        self.assertEqual('new client_id', conf2.get('sandbox', 'client_id'))
        conf2.set('sandbox', 'client_id', 'custom client_id')
        conf2.write()
