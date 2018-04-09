# -*- encoding: utf-8 -*-
# Heavily inspired by python-ovh code
# https://github.com/ovh/python-ovh

"""
The client will successively attempt to locate this configuration file in

1. Current working directory: ``./linxo.conf``
2. Current user's home directory ``~/.linxo.conf``
3. System wide configuration ``/etc/linxo.conf``

"""

import os

try:
    from ConfigParser import RawConfigParser, NoSectionError, NoOptionError
except ImportError:  # pragma: no cover
    # Python 3
    from configparser import RawConfigParser, NoSectionError, NoOptionError

__all__ = ['config']

#: Locations where to look for configuration file by *increasing* priority
CONFIG_PATH = [
    os.path.realpath('./linxo.conf'),
    os.path.expanduser('~/.linxo.conf'),
    '/etc/linxo.conf',
]


class ConfigurationManager(object):
    '''
    Application wide configuration manager
    '''
    def __init__(self):
        '''
        Create a config parser and load config from environment.
        '''
        self.config = RawConfigParser()
        for f in CONFIG_PATH:
            if os.path.isfile(f):
                self.config.read(f)
                self.filename = f
                return

    def get(self, section, name):
        '''
        Load parameter ``name`` from configuration, respecting priority order.
        Most of the time, ``section`` will correspond to the current api
        ``endpoint``. ``default`` section only contains ``endpoint`` and general
        configuration.

        :param str section: configuration section or region name. Ignored when
            looking in environment
        :param str name: configuration parameter to lookup
        '''
        # 1/ try env
        try:
            return os.environ['LINXO_' + name.upper()]
        except KeyError:
            pass

        # 2/ try from specified section/endpoint
        try:
            return self.config.get(section, name)
        except (NoSectionError, NoOptionError):
            pass

        # not found, sorry
        return None

    def set(self, section, name, value):
        return self.config.set(section, name, value)

    def read(self, config_file):
        # Read an other config file
        if not os.path.isfile(config_file):
            raise IOError('File {0} not found'.format(config_file))
        self.config.read(config_file)
        self.filename = config_file

    def write(self):
        cfg = open(self.filename, 'w')
        self.config.write(cfg)
        cfg.close()


config = ConfigurationManager()
