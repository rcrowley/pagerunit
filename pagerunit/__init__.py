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
import time
import traceback
import types

import mail

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
            self._cfg = ConfigParser(defaults={'dirname': '/var/run/pagerunit',
                                               'port': str(587),
                                               'server': 'smtp.gmail.com'})
            self._cfg.read(['/etc/pagerunit.cfg',
                            os.path.expanduser('~/.pagerunit.cfg')])
            for section, option in (('mail', 'address'),
                                    ('mail', 'password'),
                                    ('mail', 'port'),
                                    ('mail', 'server'),
                                    ('mail', 'username'),
                                    ('state', 'dirname')):
                self._cfg.get(section, option)
        return self._cfg

    @property
    def mail(self):
        """
        Lazy-create the SMTP gateway.
        """
        if not hasattr(self, '_mail'):
            self._mail = mail.Mail(self.cfg.get('mail', 'server'),
                                   self.cfg.getint('mail', 'port'),
                                   self.cfg.get('mail', 'username'),
                                   self.cfg.get('mail', 'password'))
        return self._mail

    def loop(self, secs=10):
        """
        Run the tests on an interval forever.
        """
        while True:
            self.run()
            time.sleep(secs)

    def problem(self, f, exc):
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
            os.write(fd, traceback.format_exc(exc))
            os.close(fd)
            logging.info('{0} has a problem'.format(f.__name__))
            self.mail.problem(self.cfg.get('mail', 'address'),
                              f.__name__,
                              f.__doc__,
                              exc)
        except OSError as e:
            if errno.EEXIST != e.errno:
                raise e

    def recovery(self, f):
        """
        Remove this now-recovered problem from the runtime state and send
        a recovery email.
        """
        try:
            os.unlink(os.path.join(self.cfg.get('state', 'dirname'),
                                   f.__name__))
            logging.info('{0} recovered'.format(f.__name__))
            self.mail.recovery(self.cfg.get('mail', 'address'),
                               f.__name__,
                               f.__doc__)
        except OSError as e:
            if errno.ENOENT != e.errno:
                raise e

    def run(self):
        """
        Run all of the tests once.
        """
        for pathname in self.pathnames:
            units = imp.load_source('units', pathname)
            for attr in (getattr(units, attrname) for attrname in dir(units)):
                if types.FunctionType != type(attr):
                    continue
                if 'units' != attr.__module__:
                    continue
                spec = inspect.getargspec(attr)
                if 0 < len(spec[0]) or spec[1] is not None or spec[2] is not None:
                    continue
                self.unit(attr)

    def unit(self, f):
        """
        Run a single test and send problem/recovery emails as appropriate.
        """
        try:
            f()
            self.recovery(f)
        except AssertionError as e:
            self.problem(f, e)
        except Exception as e:
            self.problem(f, e)
