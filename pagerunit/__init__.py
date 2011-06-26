"""
PagerUnit, a simple Nagios alternative made to look like unit tests.
"""

import errno
import imp
import logging
import os
import os.path
import time
import traceback
import types

import cfg
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
        self._pathnames = pathnames
        try:
            os.makedirs(cfg.dirname())
        except OSError as e:
            if errno.EEXIST != e.errno:
                raise e

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
        """
        try:
            fd = os.open(os.path.join(cfg.dirname(), f.__name__),
                         os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                         0o644)
            os.write(fd, traceback.format_exc(exc))
            os.close(fd)
            logging.info('{0} has a problem'.format(f.__name__))
            mail.problem(f.__name__, f.__doc__, exc)
        except OSError as e:
            if errno.EEXIST != e.errno:
                raise e

    def recovery(self, f):
        """
        Remove this now-recovered problem from the runtime state and send
        a recovery email.
        """
        try:
            os.unlink(os.path.join(cfg.dirname(), f.__name__))
            logging.info('{0} recovered'.format(f.__name__))
            mail.recovery(f.__name__, f.__doc__)
        except OSError as e:
            if errno.ENOENT != e.errno:
                raise e

    def run(self):
        """
        Run all of the tests once.
        """
        for pathname in self._pathnames:
            units = imp.load_source('units', pathname)
            for attr in (getattr(units, attrname) for attrname in dir(units)):
                if types.FunctionType != type(attr):
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
