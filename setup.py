# -*- coding: utf-8 -*-
"""Define setup for the package ``annuity``, based on the German VDI 2067.

    **VDI 2067, Part 1**

    **Economic efficiency of building installations**

    **Fundamentals and economic calculation**

    *September 2012 (ICS 91.140.01)*
"""
from setuptools import setup
from setuptools_scm import get_version


try:
    version = get_version(version_scheme='post-release')
except LookupError:
    version = '0.0.0'
    print('Warning: setuptools-scm requires an intact git repository to detect'
          ' the version number for this build.')

setup(name='annuity',
      version=version,
      description='Calculation of economic efficiency using the annuity method',
      long_description=open('README.md').read(),
      license='MIT',
      author='Joris Zimmermann',
      author_email='joris.zimmermann@stw.de',
      url='https://github.com/jnettels/annuity',
      )
