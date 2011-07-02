"""
Send problem and recovery emails through the configured SMTP gateway.
"""

import smtplib

class Mail(object):
    """
    An SMTP gateway instance that knows how to format PagerUnit emails.
    """

    def __init__(self, server, port, username, password):
        self.server = server
        self.port = port
        self.username = username
        self.password = password

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
