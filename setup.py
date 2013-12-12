#!/usr/bin/env python

import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand

class PyTest(TestCommand):
    extra_kwargs = {'tests_require': ['pytest', 'mock']}

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        sys.exit(pytest.main(self.test_args))


setup(name='isort',
      version='2.6.0',
      description='A Python utility / library to sort Python imports.',
      author='Timothy Crosley',
      author_email='timothy.crosley@gmail.com',
      url='https://github.com/timothycrosley/isort',
      download_url='https://github.com/timothycrosley/isort/archive/2.6.0.tar.gz',
      license='MIT',
      entry_points={'console_scripts': ['isort = isort:main']},
      py_modules=['isort'],
      cmdclass={'test': PyTest},
      **PyTest.extra_kwargs)
