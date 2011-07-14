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
import traceback
import types

import smtp

# ConfigParser defaults are a bit limited so PagerUnit rolls its own.  These
# are placed before the config files are opened.
DEFAULTS = {'mail': {'batch': False,
                     'batch_subject': '{problems} PROBLEMS, {recoveries} RECOVERIES on {fqdn}',
                     'heartbeat': False,
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
            'state': {'dirname': '/var/lib/pagerunit'}}

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

    def __call__(self):
        """
        Run all of the tests once and send batch messages.
        """
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
        self.batch(results)
        return results

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
    def smtp(self):
        """
        Lazy-create the SMTP gateway.
        """
        if not hasattr(self, '_smtp'):
            self._smtp = smtp.SMTP(self.cfg.get('smtp', 'server'),
                                   self.cfg.getint('smtp', 'port'),
                                   self.cfg.get('smtp', 'username'),
                                   self.cfg.get('smtp', 'password'))
        return self._smtp

    def batch(self, results):
        """
        Send batch messages for this list of results.
        """
        self.batch_mail(results)
        self.batch_sms(results)

    def batch_mail(self, results):
        """
        Send this list of results as a batch mail message.
        """
        if not self.cfg.getboolean('mail', 'batch'):
            return None
        if not self.cfg.has_option('mail', 'address'):
            return None
        if not len(results) and not self.cfg.getboolean('mail', 'heartbeat'):
            return None

        # Create a batch MIMEJSON part and a MIMEText part for each
        # problem or recovery result.
        bodies = [smtp.MIMEJSON(results)]
        for r in results:
            if 'exc' in r:
                s, b = ('problem_subject', 'problem_body')
            else:
                s, b = ('recovery_subject', 'recovery_body')
            bodies.append(smtp.mime_text(
                self.cfg.get('mail', s) + '\n\n' + \
                self.cfg.get('mail', b) + '\n\n', **r))

        # Count the total number of problems and recoveries.
        problems = len([r for r in results if 'exc' in r])
        recoveries = len([r for r in results if 'exc' not in r])

        # Send the batch as a single multipart message.
        return self.smtp.send_multipart(self.cfg.get('mail', 'address'),
                                        self.cfg.get('mail', 'batch_subject'),
                                        *bodies,
                                        fqdn=socket.getfqdn(),
                                        problems=problems,
                                        recoveries=recoveries)

    def batch_sms(self, results):
        """
        Send this list of results as a batch SMS message.
        """
        if not self.cfg.getboolean('sms', 'batch'):
            return None
        if not self.cfg.has_option('sms', 'address'):
            return None
        if not len(results):
            return None

        # Split the results into problems and recoveries.
        problems = ', '.join([r['name'] for r in results
                              if 'exc' in r]) or '(none)'
        recoveries = ', '.join([r['name'] for r in results
                                if 'exc' not in r]) or '(none)'

        # Send the batch as a single message.
        return self.smtp.send(self.cfg.get('sms', 'address'),
                              None,
                              self.cfg.get('sms', 'batch_body'),
                              fqdn=socket.getfqdn(),
                              problems=problems,
                              recoveries=recoveries)

    def problem(self, f, exc, tb):
        """
        Add this problem to the runtime state and send a problem message.
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
        result = dict(name=f.__name__,
                      fqdn=socket.getfqdn(),
                      exc=str(exc) or '(no explanation)',
                      line=traceback.extract_tb(tb)[-1][-1],
                      doc=_strip(f.__doc__))
        self.problem_mail(result)
        self.problem_sms(result)
        return result

    def problem_mail(self, result):
        """
        Send this problem as a mail message.
        """
        if self.cfg.getboolean('mail', 'batch'):
            return None
        if not self.cfg.has_option('mail', 'address'):
            return None
        return self.smtp.send_json(self.cfg.get('mail', 'address'),
                                   self.cfg.get('mail', 'problem_subject'),
                                   self.cfg.get('mail', 'problem_body'),
                                   **result)

    def problem_sms(self, result):
        """
        Send this problem as an SMS message.
        """
        if self.cfg.getboolean('sms', 'batch'):
            return None
        if not self.cfg.has_option('sms', 'address'):
            return None
        return self.smtp.send(self.cfg.get('sms', 'address'),
                              None,
                              self.cfg.get('sms', 'problem_body'),
                              **result)

    def recovery(self, f):
        """
        Remove this now-recovered problem from the runtime state and send
        a recovery message.
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
        result = dict(name=f.__name__,
                      fqdn=socket.getfqdn(),
                      doc=_strip(f.__doc__))
        self.recovery_mail(result)
        self.recovery_sms(result)
        return result

    def recovery_mail(self, result):
        """
        Send this recovery as a mail message.
        """
        if self.cfg.getboolean('mail', 'batch'):
            return None
        if not self.cfg.has_option('mail', 'address'):
            return None
        return self.smtp.send_json(self.cfg.get('mail', 'address'),
                                   self.cfg.get('mail', 'recovery_subject'),
                                   self.cfg.get('mail', 'recovery_body'),
                                   **result)

    def recovery_sms(self, result):
        """
        Send this recovery as an SMS message.
        """
        if self.cfg.getboolean('sms', 'batch'):
            return None
        if not self.cfg.has_option('sms', 'address'):
            return None
        return self.smtp.send(self.cfg.get('sms', 'address'),
                              None,
                              self.cfg.get('sms', 'recovery_body'),
                              **result)

    def unit(self, f):
        """
        Run a single test and send problem/recovery messages as appropriate.
        """
        try:
            f()
            return self.recovery(f)
        except AssertionError as e:
            return self.problem(f, e, sys.exc_info()[2])
        except Exception as e:
            return self.problem(f, e, sys.exc_info()[2])
