"""Test of examples for annuity."""
import os
import pandas as pd
import logging
import unittest

import annuity

# Define the logging function
logger = logging.getLogger(__name__)


def main_VDI_example(pprint=True):
    """Run the main VDI example.

    This main method implements the example from VDI 2067 Annex B.
    A small difference between the results may result from rounding.

    This shows the most basic way to add ``parts`` to an energy system,
    define some demands and calculate the annuities.
    """
    # Define output format of logging function
    logging.basicConfig(format='%(asctime)-15s %(message)s')
    logger.setLevel(level='DEBUG')  # Set a default level for the logger

    sys = annuity.System()  # Create energy system to add components (parts) to

    # Add part: Oil burner
    A_0 = 6045  # [€] purchase price
    T_N = 20  # service life (in years)
    f_Inst = 0.01  # Effort for maintenance
    f_W_Insp = 0.025  # Effort for servicing and inspection
    f_Op = 10  # Effort for operation [h/a]
    sys.add_part('oil boiler', A_0, T_N, f_Inst, f_W_Insp, f_Op)

    # Add all other parts:
    sys.add_part('burner', 2000, 12, 0.12, 0, 0)
    sys.add_part('remote', 75, 12, 0.025, 0, 0)
    sys.add_part('heating', 2800, 50, 0.02, 0, 0)
    sys.add_part('piping', 4426, 40, 0.01, 0, 0)
    sys.add_part('expansion tank', 40, 15, 0.02, 0, 0)
    sys.add_part('circulator pump', 286, 10, 0.03, 0, 0)
    sys.add_part('manual control', 50, 20, 0.025, 0, 0)
    sys.add_part('wall', 616, 40, 0, 0, 0)
    sys.add_part('planning', 500, 0, 0, 0, 0)  # service life = 0 years
    sys.add_part('radiators', 7551, 30, 0.01, 0, 0)
    sys.add_part('tank', 950, 25, 0.015, 0, 0)
    sys.add_part('smokestack', 2500, 50, 0.03, 0, 0)
    sys.add_part('smokestack con.', 100, 50, 0.03, 0, 0)
    sys.add_part('boiler assembly', 633, 20, 0.0, 0, 0)
    sys.add_part('circ. pump inst.', 250, 10, 0.03, 0, 0)
    sys.add_part('piping for circ.', 1920, 30, 0.02, 0, 0)
    sys.add_part('piping insulation', 684, 20, 0.01, 0, 0)

    # Define demands in first year
    Q_th = 14012  # kWh/a
    Q_el = 417  # kWh/a
    price_th = -0.06  # €/kWh
    price_el = -0.20  # €/kWh
    df_V1 = pd.DataFrame({'quantity': [Q_th, Q_el],
                          'price': [price_th, price_el]},
                         index=['Wärme', 'Strom'])
    df_V1['r'] = 1.03  # set same price change factor for all entries
    df_VSE = pd.concat([df_V1], keys=['Demand-related costs'])

    # Calculate the annuity of the energy system (with default r values)
    q = 1.07  # interest factor (which is an interest rate of 7 %)
    T = 30  # observation period
    A = sys.calc_annuities(T=T, q=q, df_VSE=df_VSE)  # Series of annuities

    if pprint:
        sys.pprint_parts()  # pretty-print a list of all parts of the system
        sys.pprint_annuities()  # pretty-print the annuities
        sys.pprint_VSE()

        A_VDI_example = -5633.44  # Result of total annuity in official example
        diff = A.sum() - A_VDI_example
        print('Difference to VDI Example:', round(diff, 5), '€ (',
              round(diff/A_VDI_example*100), '%)')

    return A.sum()


def main_database_example(pprint=True):
    """Run the main database example.

    Main function that shows an example for loading the parts of the
    energy system from a database.
    """
    # Define output format of logging function
    logging.basicConfig(format='%(asctime)-15s %(message)s')
    logger.setLevel(level='INFO')  # Set a default level for the logger

    sys = annuity.System()

    sys.load_cost_db(path=os.path.join(
        os.path.dirname(__file__), 'files', 'cost_database.xlsx'))

    fund = 0.5  # factor for funding
    sys.add_part_db('Photovoltaik', 'Dach', 'komplett', 5500)
    sys.add_part_db('Gebäude', 'Heizzentrale', 'komplett', 1, fund=fund)
    sys.add_part_db('Langzeitwärmespeicher', 'Behälter', 'komplett', 30900,
                    fund=fund)
    sys.add_part_db('Übergabestation', 'Fernwärme', 'komplett', 3954)
    sys.add_part_db('Wärmepumpe', 'Luft-Wasser HT', 'komplett', 2000)
    sys.add_part_db('Elektrolyse', 'PEM', 'Elektrolyseur', 1000)
    sys.add_part_db('Elektrolyse', 'PEM', 'H2-Reinigungsanlage', 1000)
    sys.add_part_db('Wärmenetz', 'Fernwärme', 'Trasse', 6565)
    sys.add_part_db('Wärmenetz', 'Fernwärme', 'Hausanschlüsse', 131)
    sys.add_part_db('Wärmenetz', 'Fernwärme', 'Hausübergabestationen', 131)

    # For planning, a percentage of the total investment cost is used
    invest = sys.calc_investment()
    sys.add_part('Planung', invest*0.15, 0, 0, 0, 0)
    sys.add_part('Sonstiges', invest*0.10, 0, 0, 0, 0)

    df_V1 = pd.DataFrame(
            {'quantity': [5410.9, 3954.4, 92],
             'price': [-20, -30, -237.4]},
            index=['Verbrauch 1', 'Verbrauch 2', 'Verbrauch 3'])
    df_E1 = pd.DataFrame(
            {'quantity': [494, 1811, 8098, 3954, 1852],
             'price': [100, 146, 60, 30, 220]},
            index=['Erlös 1', 'Erlös 2', 'Erlös 3', 'Erlös 4', 'Erlös 5'])

    df_V1['r'] = 1.03  # set same price change factor for all entries
    df_E1['r'] = 1.03  # set same price change factor for all entries
    df_VSE = pd.concat([df_V1, df_E1],
                       keys=['Demand-related costs', 'Proceeds'])

    # Calculate the annuity of the energy system
    q = 1.03  # interest factor (which is an interest rate of 3 %)
    T = 20  # observation period
    A = sys.calc_annuities(T=T, q=q, df_VSE=df_VSE)  # Series of annuities

    if pprint:
        sys.pprint_parts()  # convenience function
        sys.pprint_annuities()  # convenience function
        sys.pprint_VSE()

        sys.calc_investment()
        sys.calc_investment(include_funding=True)

        sys.calc_amortization(pprint=True)

    return A.sum()


class TestMethods(unittest.TestCase):
    """Define tests."""

    def test_vdi_example(self):
        """Test the calculated total annuity."""
        self.assertAlmostEqual(main_VDI_example(pprint=False),
                               -5632.5449037986)

    def test_database_example(self):
        """Test the calculated total annuity."""
        self.assertAlmostEqual(main_database_example(pprint=False),
                               -8.4087763815)


if __name__ == '__main__':
    unittest.main()
