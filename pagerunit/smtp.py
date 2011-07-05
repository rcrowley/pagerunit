"""
Send problem and recovery messages through the configured SMTP gateway.
"""

import email
from email.mime.multipart import MIMEMultipart
from email.mime.nonmultipart import MIMENonMultipart
from email.mime.text import MIMEText
import json
import smtplib

class MIMEJSON(MIMENonMultipart):
    """
    A JSON-serialized object as an email.
    """

    def __init__(self, *args, **kwargs):
        """
        Create a MIME part, JSON-serializing the given object.  The object
        may be given as the only positional argument or as keyword arguments.
        The object may be a list or a dict.  If it is a list, the assumption
        is that this is a batch and the filename reflects that.
        """
        MIMENonMultipart.__init__(self, 'application', 'json', charset='utf-8')
        try:
            obj = args[0]
        except IndexError:
            obj = kwargs
        try:
            name = obj['name']
        except TypeError:
            name = 'batch'
        self.add_header('Content-Disposition',
                        'attachment',
                        filename='{0}.json'.format(name))
        self.set_payload(json.dumps(obj))

def mime_json(*args, **kwargs):
    return MIMEJSON(*args, **kwargs)

def mime_text(body, **kwargs):
    return MIMEText(body.format(**kwargs))

class SMTP(object):
    """
    An SMTP gateway instance that knows how to format PagerUnit messages.

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

    def send(self, address, subject, body, **kwargs):
        """
        Send a message through the configured SMTP gateway.
        """
        addresses = [a.strip() for a in address.split(',')]
        m = mime_text(body, **kwargs)
        m['From'] = self.username
        m['Reply-To'] = addresses[0]
        m['To'] = address
        if subject is not None:
            m['Subject'] = subject.format(**kwargs)
        self.smtp.sendmail(self.username, addresses, m.as_string())
        return m

    def send_json(self, address, subject, body, **kwargs):
        """
        Send a MIME multipart message with two parts, one human-readable
        and the other the JSON-encoded raw data used to generated the
        human-readable part.
        """
        return self.send_multipart(address,
                                   subject,
                                   mime_text(body, **kwargs),
                                   mime_json(**kwargs),
                                   **kwargs)

    def send_multipart(self, address, subject, *args, **kwargs):
        """
        Send a MIME multipart message through the configured SMTP gateway.
        """
        addresses = [a.strip() for a in address.split(',')]
        m = MIMEMultipart(_subparts=args)
        m['From'] = self.username
        m['Reply-To'] = addresses[0]
        m['To'] = address
        if subject is not None:
            m['Subject'] = subject.format(**kwargs)
        self.smtp.sendmail(self.username, addresses, m.as_string())
        return m
