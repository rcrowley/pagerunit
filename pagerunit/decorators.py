"""
Useful decorators for PagerUnit tests.
"""

def disabled(f):
    """
    Mark the decorated function as disabled, which has the effect of skipping
    running it altogether.
    """
    def decorated(*args, **kwargs):
        pass
    decorated.__name__ = f.__name__
    decorated.__doc__ = f.__doc__
    return decorated

def silent(f):
    """
    Mark the decorated function as silent, which has the effect of running
    it but ignoring `AssertionError`.
    """
    def decorated(*args, **kwargs):
        try:
            f(*args, **kwargs)
        except AssertionError:
            pass
    decorated.__name__ = f.__name__
    decorated.__doc__ = f.__doc__
    return decorated
