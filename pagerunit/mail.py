"""
Send problem and recovery emails through the configured SMTP gateway.
"""

import smtplib
import traceback

import cfg

def _strip(s):
    """
    Strip whitespace from a multiline string.
    """
    return ''.join([line.strip() + '\n' for line in s.strip().splitlines()])

def _mail(address, subject, body):
    """
    Send an email through the configured SMTP gateway.

    Based on <http://exchange.nagios.org/directory/Plugins/Uncategorized/Operating-Systems/Linux/Nagios-Alerts-via-gmail-and-python/details>.
    """
    s = smtplib.SMTP(cfg.mail_server(), cfg.mail_server_port())
    s.ehlo(cfg.mail_username())
    s.starttls()
    s.ehlo(cfg.mail_username())
    s.login(cfg.mail_username(), cfg.mail_password())
    s.sendmail(cfg.mail_username(),
               address.split(','),
               'To: {0}\nSubject: {1}\n\n{2}'.format(address, subject, body))
    s.quit()

def problem(name, doc, exc):
    """
    Send a problem email.
    """
    _mail(cfg.address(),
          'PROBLEM {0}'.format(name),
          '{0}\n\n{1}'.format(exc, _strip(doc)))

def recovery(name, doc):
    """
    Send a recovery email.
    """
    _mail(cfg.address(), 'RECOVERY {0}'.format(name), _strip(doc))
