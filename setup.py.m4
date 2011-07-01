from setuptools import setup, find_packages

setup(name='pagerunit',
      version='__VERSION__',
      description='A simple Nagios alternative made to look like unit tests.',
      author='Richard Crowley',
      author_email='r@rcrowley.org',
      url='https://github.com/rcrowley/pagerunit',
      packages=find_packages(),
      scripts=['bin/pagerunit'],
      license='BSD',
      zip_safe=False)
