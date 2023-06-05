# Copyright (C) 2020 Joris Zimmermann

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program. If not, see https://www.gnu.org/licenses/.

"""Define tests to run during build process."""

import unittest
import annuity


class TestMethods(unittest.TestCase):
    """Defines tests."""

    def test_example_1(self):
        """Test the calculated total annuity."""
        self.assertAlmostEqual(annuity.main_VDI_example(pprint=False),
                               -5632.5449037986)

    def test_example_2(self):
        """Test the calculated total annuity."""
        self.assertAlmostEqual(annuity.main_database_example(pprint=False),
                               -8.4087763815)


if __name__ == '__main__':
    unittest.main()
