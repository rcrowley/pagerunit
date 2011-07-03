"""
Send problem and recovery emails through the configured SMTP gateway.
"""

import smtplib

class Mail(object):
    """
    An SMTP gateway instance that knows how to format PagerUnit emails.
    """

    def __init__(self, server, port, username, password):
        self.smtp = smtplib.SMTP(server, port)
        self.username = username
        self.password = password
        self.smtp.ehlo(self.username)
        self.smtp.starttls()
        self.smtp.ehlo(self.username)
        self.smtp.login(self.username, self.password)

    def __del__(self):
        self.smtp.quit()

    def send(self, address, subject, body):
        """
        Send an email through the configured SMTP gateway.

        Based on <http://exchange.nagios.org/directory/Plugins/Uncategorized/Operating-Systems/Linux/Nagios-Alerts-via-gmail-and-python/details>.
        """
        self.smtp.sendmail(self.username,
                           address.split(','),
                           'To: {0}\r\nSubject: {1}\r\n\r\n{2}'.format(address,
                                                                       subject,
                                                                       body))
