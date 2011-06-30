"""
Send problem and recovery emails through the configured SMTP gateway.
"""

import smtplib
import socket
import traceback

def _strip(s):
    """
    Strip whitespace from a multiline string.
    """
    return ''.join([line.strip() + '\n' for line in s.strip().splitlines()])

class Mail(object):
    """
    An SMTP gateway instance that knows how to format PagerUnit emails.
    """

    def __init__(self, server, port, username, password):
        self.server = server
        self.port = port
        self.username = username
        self.password = password

    def problem(self, address, name, doc, exc):
        """
        Send a problem email.
        """
        self.send(address,
                  'PROBLEM {0}'.format(name),
                  '{0}: {1}\n\n{2}'.format(socket.getfqdn(), exc, _strip(doc)))

    def recovery(self, address, name, doc):
        """
        Send a recovery email.
        """
        self.send(address,
                  'RECOVERY {0}'.format(name),
                  '{0}\n\n{1}'.format(socket.getfqdn(), _strip(doc)))

    def send(self, address, subject, body):
        """
        Send an email through the configured SMTP gateway.

        Based on <http://exchange.nagios.org/directory/Plugins/Uncategorized/Operating-Systems/Linux/Nagios-Alerts-via-gmail-and-python/details>.
        """
        s = smtplib.SMTP(self.server, self.port)
        s.ehlo(self.username)
        s.starttls()
        s.ehlo(self.username)
        s.login(self.username, self.password)
        s.sendmail(self.username,
                   address.split(','),
                   'To: {0}\r\nSubject: {1}\r\n\r\n{2}'.format(address,
                                                               subject,
                                                               body))
        s.quit()
