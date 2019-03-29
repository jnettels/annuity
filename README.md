VDI 2067
================
This is an implementation of the calculation of economic efficiency
using the annuity method defined in the German VDI 2067.

**VDI 2067, Part 1**

**Economic efficiency of building installations**

**Fundamentals and economic calculation**

*September 2012 (ICS 91.140.01)*

Notes
-----
The basic usage consists of two main steps:

* Define an energy system ``sys`` with its components (called parts here)

* Call ``sys.calc_annuities()`` to receive the annuities. Afterwards, you
  may also call ``sys.pprint_parts()`` and ``sys.pprint_annuities()``,
  which are convenient pretty-print functions to view the results.

There are two main ways for adding parts to an energy system:

* Manually input each part with its purchase price, service life and
  factors for effort for maintenance, etc. Please refer to the main method
  ``main_VDI_example()`` for this approach, which implements the example
  provided in the VDI 2067 Annex B and serves as a test

* Select the parts from a database that contains all the properties. Here
  the only required inputs are name and size of a part (e.g. installed kW
  or kWh), all other information are derived from the database.

Deviations from the official calculations in VDI 2067:

* If the service life of a part is ``T_N = 0``, the number of replacements
  is set to ``n = 0``. This applies to e.g. 'planning'. This approach leads
  to the correct results in the VDI 2067 example, but is not precisely
  documented.

* VDI 2067 demands an observation period ``T > 0``, for which the annuity
  factor is calculated. In addition to that, this implementation supports
  a 'simplified' calculation with ``T = 0``, where the annuity factor for
  each part is calculated with its service life ``T_N``.

* This implementation includes the concept of funding, which is not part
  of VDI 2067. For each added ``part``, the optional parameter ``fund``
  can be given. The investment amout of the first year is reduced by that
  factor (``fund=0`` equals no funding, ``fund=1`` equals 100% funding).
  Investment for all following replacements are not affected, they have to
  be paid in full. This does also not affect the operation-related costs.
  They are always calculated with the original investment amount ``A_0``.
