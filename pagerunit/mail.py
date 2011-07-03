"""
Send problem and recovery emails through the configured SMTP gateway.
"""

import email
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import smtplib

class MIMEJSON(MIMEBase):
    """
    """

    def __init__(self, **kwargs):
        MIMEBase.__init__(self, 'application', 'json', charset='utf-8')
        self.add_header('Content-Disposition',
                        'attachment',
                        filename='{name}.json'.format(**kwargs))
        self.set_payload(json.dumps(kwargs))

class Mail(object):
    """
    An SMTP gateway instance that knows how to format PagerUnit emails.

    Based on <http://exchange.nagios.org/directory/Plugins/Uncategorized/Operating-Systems/Linux/Nagios-Alerts-via-gmail-and-python/details>.
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
        """
        m = MIMEText(body)
        m['From'] = self.username
        m['To'] = address
        m['Subject'] = subject
        self.smtp.sendmail(self.username, address.split(','), m.as_string())

    def send_multipart(self, address, subject, *args):
        m = MIMEMultipart(_subparts=args)
        m['From'] = self.username
        m['To'] = address
        m['Subject'] = subject
        self.smtp.sendmail(self.username, address.split(','), m.as_string())

    def send_template(self, address, subject, body, **kwargs):
        self.send_multipart(address,
                            subject.format(**kwargs),
                            MIMEText(body.format(**kwargs)),
                            MIMEJSON(**kwargs))
