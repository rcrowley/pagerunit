"""
Configuration for PagerUnit.
"""

from ConfigParser import ConfigParser
import logging
import os.path
import sys

cfg = ConfigParser(defaults={'dirname': '/var/run/pagerunit',
                             'mail_server': 'smtp.gmail.com',
                             'mail_server_port': str(587)})
getattr(cfg, '_sections')['default'] = getattr(cfg, '_dict')()
cfg.read(['/etc/pagerunit.cfg',
          os.path.expanduser('~/.pagerunit.cfg')])
for option in ('address',
               'dirname',
               'mail_password',
               'mail_server',
               'mail_server_port',
               'mail_username'):
    if not cfg.has_option('default', option):
        logging.error('missing {0}'.format(option))
        sys.exit(1)

def address():
    """
    Return the address that will receive problem and recovery emails.
    """
    return cfg.get('default', 'address')

def dirname():
    """
    Return the directory name where runtime state will be stored.
    """
    return cfg.get('default', 'dirname')

def mail_password():
    """
    Return the password to use when authenticating with the mail server.
    """
    return cfg.get('default', 'mail_password')

def mail_server():
    """
    Return the mail server to use to send problem and recovery emails.
    """
    return cfg.get('default', 'mail_server')

def mail_server_port():
    """
    Return the port to connect to on the mail server.
    """
    return cfg.get('default', 'mail_server_port')

def mail_username():
    """
    Return the username to use when authenticating with the mail server.
    """
    return cfg.get('default', 'mail_username')
