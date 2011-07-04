"""
PagerUnit, a simple Nagios alternative made to look like unit tests.
"""

from ConfigParser import ConfigParser
import errno
import imp
import inspect
import logging
import os
import os.path
import socket
import sys
import time
import traceback
import types

import mail

# ConfigParser defaults are a bit limited so PagerUnit rolls its own.  These
# are placed before the config files are opened.
DEFAULTS = {'mail': {'batch': False,
                     'batch_subject': '{problems} PROBLEMS, {recoveries} RECOVERIES on {fqdn}',
                     'problem_body': '{exc}\n\n\t{line}\n\n{doc}',
                     'problem_subject': 'PROBLEM {name} on {fqdn}',
                     'recovery_body': '{doc}',
                     'recovery_subject': 'RECOVERY {name} on {fqdn}'},
            'sms': {'batch': False,
                    'batch_body': 'PROBLEMS: {problems}; RECOVERIES: {recoveries} on {fqdn}',
                    'problem_body': 'PROBLEM {name} on {fqdn}',
                    'recovery_body': 'RECOVERY {name} on {fqdn}'},
            'smtp': {'port': 587,
                     'server': 'smtp.gmail.com'},
            'state': {'dirname': '/var/run/pagerunit'}}

def _strip(s):
    """
    Strip whitespace from a multiline string.
    """
    if s is None:
        return ''
    return ''.join([line.strip() + '\n' for line in s.strip().splitlines()])

class PagerUnit(object):
    """
    A PagerUnit instance, which is initialized with a set of tests to run,
    possibly in an infinite loop.
    """

    def __init__(self, pathnames):
        """
        Initialize this PagerUnit.  Save the list of test files and initialize
        the directory used to store runtime state.
        """
        try:
            os.makedirs(self.cfg.get('state', 'dirname'))
        except OSError as e:
            if errno.EEXIST != e.errno:
                raise e
        self.pathnames = pathnames

    @property
    def cfg(self):
        """
        Lazy-load the PagerUnit configuration file(s).
        """
        if not hasattr(self, '_cfg'):
            self._cfg = ConfigParser()
            for section, options in DEFAULTS.iteritems():
                self._cfg.add_section(section)
                for option, value in options.iteritems():
                    self._cfg.set(section, option, str(value))
            self._cfg.read(['/etc/pagerunit.cfg',
                            os.path.expanduser('~/.pagerunit.cfg')])
        return self._cfg

    @property
    def mail(self):
        """
        Lazy-create the SMTP gateway.
        """
        if not hasattr(self, '_mail'):
            self._mail = mail.Mail(self.cfg.get('smtp', 'server'),
                                   self.cfg.getint('smtp', 'port'),
                                   self.cfg.get('smtp', 'username'),
                                   self.cfg.get('smtp', 'password'))
        return self._mail

    def loop(self, secs=10):
        """
        Run the tests on an interval forever.
        """
        while True:
            self.run()
            time.sleep(secs)

    def problem(self, f, exc, tb):
        """
        Add this problem to the runtime state and send a problem email.
        If the state file already exists, let the failure pass silently
        since it is a pre-existing condition.
        """
        try:
            fd = os.open(os.path.join(self.cfg.get('state', 'dirname'),
                                      f.__name__),
                         os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                         0o644)
            os.close(fd)
        except OSError as e:
            if errno.EEXIST == e.errno:
                return
            elif errno.ENOSPC == e.errno:
                pass
            else:
                raise e
        logging.info('{0} has a problem'.format(f.__name__))
        kwargs = dict(name=f.__name__,
                      fqdn=socket.getfqdn(),
                      exc=str(exc) or '(no explanation)',
                      line=traceback.extract_tb(tb)[-1][-1],
                      doc=_strip(f.__doc__))
        if self.cfg.has_option('mail', 'address'):
            self.mail.send_json(self.cfg.get('mail', 'address'),
                                self.cfg.get('mail', 'problem_subject'),
                                self.cfg.get('mail', 'problem_body'),
                                **kwargs)
        if self.cfg.has_option('sms', 'address'):
            self.mail.send(self.cfg.get('sms', 'address'),
                           None,
                           self.cfg.get('sms', 'problem_body'),
                           **kwargs)
        return kwargs

    def recovery(self, f):
        """
        Remove this now-recovered problem from the runtime state and send
        a recovery email.
        """
        try:
            os.unlink(os.path.join(self.cfg.get('state', 'dirname'),
                                   f.__name__))
        except OSError as e:
            if errno.ENOENT == e.errno:
                return
            else:
                raise e
        logging.info('{0} recovered'.format(f.__name__))
        kwargs = dict(name=f.__name__,
                      fqdn=socket.getfqdn(),
                      doc=_strip(f.__doc__))
        if self.cfg.has_option('mail', 'address'):
            self.mail.send_json(self.cfg.get('mail', 'address'),
                                self.cfg.get('mail', 'recovery_subject'),
                                self.cfg.get('mail', 'recovery_body'),
                                **kwargs)
        if self.cfg.has_option('sms', 'address'):
            self.mail.send(self.cfg.get('sms', 'address'),
                           None,
                           self.cfg.get('sms', 'recovery_body'),
                           **kwargs)
        return kwargs

    def run(self):
        """
        Run all of the tests once.  If batching is enabled for mail or SMS,
        send the batch.
        """

        # Run all of the tests once.  Gather all non-None results.
        results = []
        for pathname in self.pathnames:
            units = imp.load_source('units', pathname)
            for attr in (getattr(units, attrname) for attrname in dir(units)):
                if types.FunctionType != type(attr):
                    continue
                if 'units' != attr.__module__:
                    continue
                spec = inspect.getargspec(attr)
                if 0 < len(spec[0]) \
                    or spec[1] is not None \
                    or spec[2] is not None:
                    continue
                result = self.unit(attr)
                if result:
                    results.append(result)

        # If mail batching is requested and there is an address.
        if self.cfg.getboolean('mail', 'batch') \
            and self.cfg.has_option('mail', 'address'):

            # Create a batch MIMEJSON part and a MIMEText part for each
            # problem or recovery result.
            bodies = [mail.MIMEJSON(results, name='batch')]
            for r in results:
                if 'exc' in r:
                    s, b = ('problem_subject', 'problem_body')
                else:
                    s, b = ('recovery_subject', 'recovery_body')
                bodies.append(mail.mime_text(
                    self.cfg.get('mail', s) + '\n\n' + \
                    self.cfg.get('mail', b) + '\n\n', **r))

            # Count the total number of problems and recoveries.
            problems = len([r for r in results if 'exc' in r])
            recoveries = len([r for r in results if 'exc' not in r])

            # Send the batch as a single multipart message.
            self.mail.send_multipart(self.cfg.get('mail', 'address'),
                                     self.cfg.get('mail', 'batch_subject'),
                                     *bodies,
                                     fqdn=socket.getfqdn(),
                                     problems=problems,
                                     recoveries=recoveries)

        # If SMS batching is requested and there is an address.
        if self.cfg.getboolean('sms', 'batch') \
            and self.cfg.has_option('sms', 'address'):

            # Split the results into problems and recoveries.
            problems = ', '.join([r['name'] for r in results
                                  if 'exc' in r]) or '(none)'
            recoveries = ', '.join([r['name'] for r in results
                                    if 'exc' not in r]) or '(none)'

            # Send the batch as a single message.
            self.mail.send(self.cfg.get('sms', 'address'),
                           None,
                           self.cfg.get('sms', 'batch_body'),
                           fqdn=socket.getfqdn(),
                           problems=problems,
                           recoveries=recoveries)

    def unit(self, f):
        """
        Run a single test and send problem/recovery emails as appropriate.
        """
        try:
            f()
            return self.recovery(f)
        except AssertionError as e:
            return self.problem(f, e, sys.exc_info()[2])
        except Exception as e:
            return self.problem(f, e, sys.exc_info()[2])
