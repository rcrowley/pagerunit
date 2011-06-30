"""
Trivial examples for Pager Unit.
"""

from pagerunit.decorators import *


def foo():
    """
    Docstring for foo.
    """
    assert True, 'Assertion for foo.'


def bar():
    """
    Docstring for bar.
    """
    assert False, 'Assertion for bar.'
