# -*- coding: utf-8 -*-
"""
VDI2067
=======
Setup for the package ``VDI2067``, based on the German VDI 2067:

    **VDI 2067, Part 1**

    **Economic efficiency of building installations**

    **Fundamentals and economic calculation**

    *September 2012 (ICS 91.140.01)*

To install, run the following command:

.. code::

    python setup.py install

You can then import the module with:

.. code::

    import VDI2067

"""

from distutils.core import setup

setup(name='VDI2067',
      version='0.1.0',
      description='VDI 2067: Calculation of economic efficiency using the annuity method',
      author='Joris Nettelstroth',
      author_email='joris.nettelstroth@stw.de',
      url='https://github.com/jnettels/VDI2067',
      py_modules=['VDI2067'],
      )
