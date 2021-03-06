"""
Isolated unit-ish tests for PagerUnit.
"""

import shutil
import smtplib
import socket
import tempfile

class Dummy(object):
    """
    No-op version of the standard library's smtplib.SMTP class.
    """

    def __init__(self, *args, **kwargs):
        pass

    def ehlo(self, *args, **kwargs):
        pass

    def login(self, *args, **kwargs):
        pass

    def quit(self):
        pass

    def sendmail(self, *args, **kwargs):
        pass

    def starttls(self, *args, **kwargs):
        pass

smtplib.SMTP = Dummy

import pagerunit
from pagerunit import smtp


p = pagerunit.PagerUnit(['example.py'])

def setup():
    p.cfg.set('mail', 'address', 'test@example.com')
    p.cfg.set('mail', 'batch', str(True))
    p.cfg.set('sms', 'address', '5555555555@txt.att.net')
    p.cfg.set('sms', 'batch', str(True))
    p.cfg.set('smtp', 'username', 'test@example.com')
    p.cfg.set('state', 'dirname', tempfile.mkdtemp())

def teardown():
    shutil.rmtree(p.cfg.get('state', 'dirname'))


def test_mime_json():
    assert '''Content-Type: application/json; charset="utf-8"
MIME-Version: 1.0
Content-Disposition: attachment; filename="test.json"

{"name": "test"}''' == smtp.mime_json(name='test').as_string()

def test_mime_text():
    assert '''Content-Type: text/plain; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit

test''' == smtp.mime_text('{test}', test='test').as_string()

def test_strip():
    assert '''foo
bar
baz
''' == pagerunit._strip(''' foo\t
\tbar\r
baz  ''')


def test_send():
    m = p.smtp.send('test1@example.com,test2@example.com',
                    '{name} subject',
                    '{name} body',
                    name='test')
    assert 'test@example.com' == m['From']
    assert 'test1@example.com' == m['Reply-To'], m['Reply-To']
    assert 'test1@example.com,test2@example.com' == m['To']

def test_send_multipart():
    m = p.smtp.send_multipart('test1@example.com,test2@example.com',
                              '{test} subject',
                              smtp.mime_text('{test} body 1', test='test'),
                              smtp.mime_text('{test} body 2', test='test'),
                              test='test')
    assert 'test@example.com' == m['From']
    assert 'test1@example.com' == m['Reply-To'], m['Reply-To']
    assert 'test1@example.com,test2@example.com' == m['To']
    assert 2 == len(m.get_payload())


def test_problem():
    def test():
        assert False, 'Test assertion.'
    result = p.unit(test)
    assert 'exc' in result

def test_recovery():
    def test():
        assert False, 'Test assertion.'
    result = p.unit(test)
    def test():
        assert True, 'Test assertion.'
    result = p.unit(test)
    assert 'exc' not in result

def test_steady():
    def test():
        assert True, 'Test assertion.'
    result = p.unit(test)
    assert result is None


def test_call():
    teardown()
    setup()
    results = p()
    assert 1 == len(results), results
    return results

def test_batch_mail():
    m = p.batch_mail(test_call())
    payload = m.get_payload()
    assert 2 == len(payload)
    assert ['application/json', 'text/plain'] == [part.get_content_type()
                                                  for part in payload]
    assert '1 PROBLEMS, 0 RECOVERIES on {0}'.format(socket.getfqdn()) \
        == m['Subject']

def test_batch_sms():
    m = p.batch_sms(test_call())
    assert 'text/plain' == m.get_content_type()
    assert '''Content-Type: text/plain; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit
From: test@example.com
Reply-To: 5555555555@txt.att.net
To: 5555555555@txt.att.net

PROBLEMS: bar; RECOVERIES: (none) on vagrant.vagrantup.com''' == m.as_string()
