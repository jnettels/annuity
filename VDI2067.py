# -*- coding: utf-8 -*-
"""
**VDI 2067: Calculation of economic efficiency using the annuity method**

Copyright (C) 2019 Joris Nettelstroth

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see https://www.gnu.org/licenses/.


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

"""

import pandas as pd
import logging
import math

# Define the logging function
logger = logging.getLogger(__name__)


def main_VDI_example():
    '''
    This main method implements the example from VDI 2067 Annex B.
    A small difference between the results may result from rounding.

    This shows the most basic way to add ``parts`` to an energy system,
    define some demands and calculate the annuities.
    '''
    # Define output format of logging function
    logging.basicConfig(format='%(asctime)-15s %(message)s')
    logger.setLevel(level='DEBUG')  # Set a default level for the logger

    sys = system()  # Create energy system to add components (parts) to

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
    sys.add_part('boilder assembly', 633, 20, 0.0, 0, 0)
    sys.add_part('circ. pump inst.', 250, 10, 0.03, 0, 0)
    sys.add_part('piping for circ.', 1920, 30, 0.02, 0, 0)
    sys.add_part('piping insulation', 684, 20, 0.01, 0, 0)

    # Define demands in first year
    Q_th = 14012  # kWh/a
    Q_el = 417  # kWh/a
    price_th = 0.06  # €/kWh
    price_el = 0.20  # €/kWh
    df_V1 = pd.DataFrame({'Q': [Q_th, Q_el], 'price': [price_th, price_el]})

    # Calculate the annuity of the energy system (with default r values)
    q = 1.07  # interest factor
    T = 30  # observation period
    A = sys.calc_annuities(T=T, q=q, df_V1=df_V1)  # Get Series of annuities

    sys.pprint_parts()  # pretty-print a list of all parts of the system
    sys.pprint_annuities()  # pretty-print the annuities
    A_VDI_example = -5633.44  # Result of total annuity in official example
    diff = A.sum() - A_VDI_example
    print('Difference to VDI Example:', round(diff, 2), '€ (',
          round(diff/A_VDI_example*100), '%)')


def main_database_example():
    ''' Main function that shows an example for loading the parts of the
    energy system from a database.
    '''
    # Define output format of logging function
    logging.basicConfig(format='%(asctime)-15s %(message)s')
    logger.setLevel(level='INFO')  # Set a default level for the logger

    path = 'Kostendatenbank.xlsx'

    sys = system()
    sys.load_cost_db(path=path)
#    print(sys.cost_db)

    fund = 0.5  # factor for funding
    sys.add_part_db('Photovoltaik', 'Dach', 'komplett', 5500)
    sys.add_part_db('Heizzentrale', 'futureSuN', 'komplett', 1, fund=fund)
    sys.add_part_db('Langzeitwärmespeicher', 'Behälter', 'komplett', 30900,
                    fund=fund)
    sys.add_part_db('Übergabestation', 'Fernwärme', 'komplett', 3954)
    sys.add_part_db('Wärmepumpe', 'Luft-Wasser HT', 'komplett', 2000)
    sys.add_part_db('Elektrolyse', 'PEM', 'Elektrolyseur', 1000)
    sys.add_part_db('Elektrolyse', 'PEM', 'H2-Reinigungsanlage', 1000)
    sys.add_part_db('Wärmenetz', 'Fernwärme', 'Trasse', 6565)
    sys.add_part_db('Wärmenetz', 'Fernwärme', 'Hausanschlüsse', 131)
    sys.add_part_db('Wärmenetz', 'Fernwärme', 'Hausübergabestationen', 131)

    # For planning, 2% of the total investment cost is used
    invest = sys.calc_investment()
    sys.add_part('Planung', invest*0.15, 0, 0, 0, 0)
    sys.add_part('Sonstiges', invest*0.10, 0, 0, 0, 0)

    df_V1 = pd.DataFrame(
            {'Q': [5410.9, 3954.4, 92],
             'price': [20, 30, 237.4]})
    df_E1 = pd.DataFrame(
            {'Q': [494, 1811, 8098, 3954, 1852],
             'price': [100, 146, 60, 30, 220]})

    # Calculate the annuity of the energy system
    q = 1.03  # interest factor
    T = 20  # observation period
    A = sys.calc_annuities(T=T, q=q,
#                           r_all=1,
                           df_V1=df_V1,
                           df_E1=df_E1,
                           )  # Get Series of annuities

    sys.pprint_parts()  # convenience function
    sys.pprint_annuities()  # convenience function

    sys.calc_investment()
    sys.calc_investment(include_funding=True)


class system():
    '''
    Class representing the energy system. Add ``part`` objects to the
    energy system to be able to perform the economic calculation with
    ``calc_annuities()``.
    '''
    def __init__(self):
        self.cost_db = None  # Cost database; set by load_cost_db()
        self.factors = None  # Constant factors; set by load_cost_db()
        self.parts = []
        self.A = None  # Total annuity of the system; set by calc_annuities()

    def load_cost_db(self, path=r'Kostendatenbank.xlsx'):
        '''Load a database with cost information. This function, as well as
        ``add_part_db()`` expect a certain structure and column headers.
        '''
        db = pd.read_excel(path, sheet_name='Datenbank', index_col=[0, 1, 2],
                           header=0)
        factors = pd.read_excel(path, sheet_name='Konstanten', index_col=[0],
                                header=0, usecols=[0, 1], squeeze=True)
        self.cost_db = db
        self.factors = factors
        return db

    def add_part_db(self, technology, variant, component, size, fund=0):
        '''Add a "part" object to the energy system by using the cost
        database. All required properties are derived from the ``size``
        of the new component.

        The ``size`` can also be zero, in which case there are simply no
        costs (this allows the use of empty placeholders).
        '''
        # Savety check
        if self.cost_db is None:
            self.load_cost_db()

        # Determine invest amount
        part_tuple = (technology, variant, component)
        try:
            df = self.cost_db.loc[part_tuple]
        except pd.core.indexing.IndexingError:
            print(self.cost_db)
            raise pd.core.indexing.IndexingError(
                    str(part_tuple) + ' not found in index of database')

        a = df['Reg. Faktor']
        b = df['Reg. Exponent']
        if 0 < size and size < df['Gültig min']:
            logger.warning('Size of part '+str(part_tuple)+' is below '
                           'boundary: '+str(size)+'<'+str(df['Gültig min'])
                           + ' '+df['Bezugseinheit'])
        elif size > df['Gültig max']:
            logger.warning('Size of part '+str(part_tuple)+' is above '
                           'boundary: '+str(size)+'>'+str(df['Gültig max'])
                           + ' '+df['Bezugseinheit'])

        if size > 0:
            A_0 = a * pow(size, b) * size  # Investment amount [€]
            f_Op = df['Bedienen']  # Effort for operation [h/a]

        else:  # Allows placeholder parts that have no actual costs
            A_0 = 0
            f_Op = 0

        T_N = df['Nutzungsdauer']  # service life (in years)
        f_Inst = df['Instandsetzung']  # Effort for maintenance
        f_W_Insp = df['Wartung']  # Effort for servicing and inspection

        self.add_part(part_tuple, A_0, T_N, f_Inst, f_W_Insp, f_Op, fund=fund)

    def add_part(self, name, A_0, T_N, f_Inst, f_W_Insp, f_Op, fund=0):
        '''
        Create a new object of the class ``part`` and add it to the list
        of parts contained in the energy system. The concept of funding
        (``fund``) is not part of the VDI 2067.

        Args:

            name (str): Name / identifier of the new part (component)

            A_0 (float): Investment amount [€]

            T_N  (int): service life (in years)

            f_Inst (float): Factor for effort for maintenance

            f_W_Insp (float): Factor for effort for servicing and inspection

            f_Op (float): Factor for effort for operation [h/a]

            fund (float): Factor for funding of investment amount in first
            year (``fund=0``: no funding, ``fund=1``: 100% funding)

        Returns:
            None
        '''
        new_part = part(name, A_0, T_N, f_Inst, f_W_Insp, f_Op, fund=fund)
        self.parts.append(new_part)

    def list_parts(self):
        '''Combine properties and all calculated values from the parts of
        the energy system into one DataFrame
        '''
        s_list = []
        for part in self.parts:
            s = pd.Series(part.__dict__)
            s_list.append(s)
        df = pd.concat(s_list, axis=1).T
        df.set_index(keys='name', append=True, inplace=True)
        return df

    def calc_investment(self, include_funding=False):
        '''Convenience function for total investment cost

        Args:
            include_funding (bool, optional): Instead of the total investment,
            return the investment after applying funding (requires setting
            the argument ``fund`` for the parts in the system).

        Returns:
            A_0_sum (float): Investment cost of all parts
        '''
        df_parts = self.list_parts()  # Get DataFrame with all parts
        A_0_sum = df_parts['A_0'].sum()  # Return sum of all investment costs

        if include_funding:
            A_0_sum = (df_parts['A_0']*(1-df_parts['fund'])).sum()

        return A_0_sum

    def calc_annuities(self, T=30, q=1.07, r_K=1.03, r_V=1.03,
                       r_B=1.02, r_S=1.02, r_I=1.03, r_E=1.03,
                       r_all=None,
                       price_op=30,
                       df_V1=pd.DataFrame({'Q': [0], 'price': [0]}),
                       df_E1=None):
        '''
        VDI 2067:
        8 Calculation of economic efficiency using the annuity method

        Defaults for cost factors are picked from VDI 2067 Table B1 Example.

        Args:
            T (int): observation period (in years) (Nutzungsdauer)

            q (float): interest factor (Zinsfaktor)

            r_* (float): price change factors (Preisänderungsfaktor)

            r_all (float): overwrite all other r_* values at once. Set to
            ``None`` or a negative value to ignore.

            df_V1 (Pandas DataFrame): DataFrame consisting of two columns
            (e.g. energy and price) that will be multiplied to calculate the
            demand-related costs

            df_E1 (Pandas DataFrame): DataFrame consisting of two columns
            (e.g. energy and price) that will be multiplied to calculate the
            proceeds

            price_op (float): price of operation in [€/h]

        Returns:
            A (Pandas Series): Series of all annuities
        '''
        if r_all is not None:  # Overwrite all other r_* values at once
            if r_all >= 0:
                r_K = r_V = r_B = r_S = r_I = r_E = r_all

        # Calculate capital and operation annuities for all components (parts)
        for part in self.parts:
            part.calc_annuity_capital(T, q, r_K)  # calc A_N_K
            part.calc_annuity_operation(T, q, r_B, r_I, price_op)  # calc A_N_B

        # Get a DataFrame used to calculate the sums of the annuities
        df_parts = self.list_parts()

        # Create a Series of all annuities. Define expenses as negative
        # and income as positive values.
        A = pd.Series({
            'A_N_K': -1 * df_parts['A_N_K'].sum(),
            'A_N_B': -1 * df_parts['A_N_B'].sum(),
            # Calculate demand, "other costs" and proceeds for the whole system
            'A_N_V': -1 * self.calc_annuity_demand(T, q, r_V, df_V1),
            'A_N_S': -1 * self.calc_annuity_other_costs(T, q, r_S),
            'A_N_E': +1 * self.calc_annuity_proceeds(T, q, r_E, df_E1),
            })

        self.A = A

        return A

    def calc_annuity(self, **kwargs):
        '''
        VDI 2067:
        8.3 Annuity of total annual payments

        This is a simple wrapper around ``calc_annuities()``, returning
        the total annuity (sum) instead of the individual annuities.

        Args:
            See ``calc_annuities()`` for arguments.

        Returns:
            A_N (float): Total annuity of the energy system
        '''
        A = self.calc_annuities(**kwargs)
        A_N = A.sum()

        return A_N

    def calc_annuity_demand(self, T, q, r, df_V1):
        '''
        8.1.2 Demand-related costs (Bedarfsgebundene Kosten)

        Args:
            T (int): observation period (in years) (Nutzungsdauer)

            q (float): interest factor (Zinsfaktor)

            r (float): price change factor (Preisänderungsfaktor)

            df_V1 (Pandas DataFrame): DataFrame consisting of two columns
            (e.g. energy and price) that will be multiplied to calculate the
            demand-related costs

        Returns:
            A_N_V (float): annuity of the demand-related costs
        '''

        # Multiply all elements of first and second column
        costs = df_V1.iloc[:, 0] * df_V1.iloc[:, 1]
        # demand-related costs in the first year
        A_V1 = costs.sum()
#        print('A_V1', A_V1)

        if T > 0:  # Official calculation
            # price dynamic cash value factor for demand-related costs
            a = calc_annuity_factor(T, q)  # annuity factor
            b_V = calc_cash_value_factor(T, r, q)
#            print('b_V', b_V)
            A_N_V = A_V1 * a * b_V  # annuity of the demand-related costs

        else:  # Calculation without observation period (Not part of VDI 2067!)
            A_N_V = A_V1

        return A_N_V

    def calc_annuity_other_costs(self, T, q, r, A_S1=0):
        '''
        8.1.4 Other costs (Sonstige Kosten)

        Args:
            T (int): observation period (in years) (Nutzungsdauer)

            q (float): interest factor (Zinsfaktor)

            r (float): price change factor (Preisänderungsfaktor)

            A_S1 (float): other costs in the first year

        Returns:
            A_N_S (float): annuity of other costs
        '''
        if T > 0:  # Official calculation
            a = calc_annuity_factor(T, q)  # annuity factor
            # price dynamic cash value factor for other costs
            b_S = calc_cash_value_factor(T, r, q)
            A_N_S = A_S1 * a * b_S  # annuity of other costs

        else:  # Calculation without observation period (Not part of VDI 2067!)
            A_N_S = A_S1

        return A_N_S

    def calc_annuity_proceeds(self, T, q, r, df_E1=None):
        '''
        8.2 Proceeds (Erlöse)

        Project and operator dependent proceeds can arise in the same way
        as the costs described above. This applies to capital-related
        proceeds (investments, subsidies), to demand-related proceeds,
        and to operation-related proceeds.

        Args:
            T (int): observation period (in years) (Nutzungsdauer)

            q (float): interest factor (Zinsfaktor)

            r (float): price change factor (Preisänderungsfaktor)

            df_E1 (DataFrame): DataFrame with proceeds in the first year (two
            columns that are multiplied and then summed up)

        Returns:
            A_N_E (float): annuity of the proceeds
        '''

        if df_E1 is not None:
            # Multiply all elements of first and second column
            costs = df_E1.iloc[:, 0] * df_E1.iloc[:, 1]
            # proceeds in the first year
            E_1 = costs.sum()
        else:
            E_1 = 0

        if T > 0:  # Official calculation
            a = calc_annuity_factor(T, q)  # annuity factor
            # price dynamic cash value factor for proceeds
            b_E = calc_cash_value_factor(T, r, q)
            A_N_E = E_1 * a * b_E  # annuity of the proceeds

        else:  # Calculation without observation period (Not part of VDI 2067!)
            A_N_E = E_1

        return A_N_E

    def pprint_parts(self):
        '''
        Convenience function for pretty-printing the properties of all parts
        to the console.
        '''
        import locale
        locale.setlocale(locale.LC_ALL, '')  # Use space as thousands separator
        f_space = lambda x: locale.format_string('%14.2f', x, grouping=True)

        df_parts = self.list_parts()  # Get DataFrame with all parts

        A = self.calc_investment()
        A_funding = self.calc_investment(include_funding=True)

        pd.set_option('precision', 2)  # Set the number of decimal points
        pd.set_option('display.float_format', f_space)
        print('------------- List of parts -------------')
        print(df_parts.to_string())
        print('-----------------------------------------')
        print('Total investment costs:   ', f_space(A))
        if A != A_funding:
            print('Investment after funding: ', f_space(A_funding))
        print('-----------------------------------------')
        pd.reset_option('precision')  # ...and reset the setting from above
        pd.reset_option('display.float_format')

        return df_parts

    def pprint_annuities(self):
        '''
        Convenience function for pretty-printing the calculated annuities
        to the console.
        '''
        import locale
        locale.setlocale(locale.LC_ALL, '')  # Use space as thousands separator
        f_space = lambda x: locale.format_string('%14.2f', x, grouping=True)

        pp_A = self.A.rename(index={'A_N_K': 'Capital-related costs:',
                                    'A_N_B': 'Operation-related costs:',
                                    'A_N_V': 'Demand-related costs:',
                                    'A_N_S': 'Other costs:',
                                    'A_N_E': 'Proceeds:', })

        pd.set_option('precision', 2)  # Set the number of decimal points
        pd.set_option('display.float_format', f_space)
        print('--------------- Annuities ---------------')
        print(pp_A.to_string())
        print('-----------------------------------------')
        print('Total annuity:            ', f_space(pp_A.sum()))
        print('-----------------------------------------')
        pd.reset_option('precision')  # ...and reset the setting from above
        pd.reset_option('display.float_format')

        return pp_A


class part():
    '''Representation of a component of an energy system. Stores all
    properties of the component and can calculate its own capital-related
    costs and operation-related costs.
    '''
    def __init__(self, name, A_0, T_N, f_Inst, f_W_Insp, f_Op, fund=0):
        self.name = name
        self.A_0 = A_0  # Investment amount [€]
        self.T_N = T_N  # service life (in years)
        self.f_Inst = f_Inst  # Effort for maintenance
        self.f_W_Insp = f_W_Insp  # Effort for servicing and inspection
        self.f_Op = f_Op  # Effort for operation [h/a]
        self.fund = fund  # factor for funding

        # To be calculated by calc_annuity_capital()
        self.n = None  # number of replacements
        self.R_W = None  # residual value
        self.A_N_K = None  # annuity of the capital-related costs

        # To be calculated by calc_annuity_operation()
        self.A_N_B = None  # annuity of the operation-related costs

    def calc_annuity_capital(self, T, q, r):
        '''
        8.1.1 Capital-related costs (Kapitalgebundene Kosten)

        The observation period T is to be established and documented.
        The residual value is to be determined for the installation
        components. For longer observation periods, necessary replacement
        procurements will have to be taken into account.

        .. note::
            The concept of funding is not part of the original VDI 2067.
            If the property ``self.fund`` of a ``part`` is set, the
            investment amout of the first year is reduced by this factor.
            This does NOT affect the operation-related costs. They are
            always calculated with the original investment amount ``A_0``.

        Args:
            T (int): observation period (in years) (Nutzungsdauer)

            q (float): interest factor (Zinsfaktor)

            r (float): price change factor (Preisänderungsfaktor)

        Returns:
            None
        '''
        if T <= 0:  # Calc without observation period (Not part of VDI 2067!)
            T = self.T_N  # Calculate each part with its own service life time

        # Calculation as defined in VDI 2067:
        a = calc_annuity_factor(T, q)  # annuity factor

        # number of replacements procured within the observation period
        if self.T_N == 0:
            n = 0  # for one-time expenses, like "planning"
        else:
            n = math.ceil(T/self.T_N) - 1
#        print(T, self.T_N, n)

        A = []  # list of cash values for all procured replacements
        for i in range(0, n+1):
            A_i = self.A_0 * (pow(r, i*self.T_N))/(pow(q, i*self.T_N))
            A.append(A_i)

        # residual value
        if self.T_N == 0:
            R_W = 0
        else:
            R_W = (self.A_0
                   * pow(r, n*self.T_N)  # price at time of purchase
                   * ((n+1)*self.T_N-T)/self.T_N  # straight-line depriciation
                   * 1/pow(q, T)  # discounted to beginning (of review period)
                   )

        # The concept of funding is not part of the original VDI 2067!
        if self.fund > 0:
            # Investment amout of first year is reduced by factor for funding
            A[0] = A[0]*(1 - self.fund)
            # Note: The original investment 'self.A_0' is not changed, so as to
            # not affect the calculation of operation-related costs

        A_N_K = (sum(A) - R_W) * a  # annuity of the capital-related costs

        # Store values
        self.n = n
        self.R_W = R_W
        self.A_N_K = A_N_K

    def calc_annuity_operation(self, T, q, r_B, r_I, price_op):
        '''
        8.1.3 Operation-related costs (Betriebsgebundene Kosten)

        Args:
            T (int): observation period (in years) (Nutzungsdauer)

            q (float): interest factor (Zinsfaktor)

            r (float): price change factor (Preisänderungsfaktor)

            price_op (float): price of operation [€/h]

        Returns:
            None
        '''
        if T <= 0:  # Not part of VDI 2067!
            T = self.T_N  # Calculate each part with its own service life time

        a = calc_annuity_factor(T, q)  # annuity factor

        # operation-related costs in first year for maintenance
        A_IN = self.A_0 * (self.f_Inst + self.f_W_Insp)
        # operation-related costs in first year for actual operation
        A_B1 = self.f_Op * price_op
        # price dynamic cash value factor for operation-related costs
        b_B = calc_cash_value_factor(T, r_B, q)
        # price dynamic cash value factor for maintenance
        b_IN = calc_cash_value_factor(T, r_I, q)

        # annuity of the operation-related costs
        A_N_B = A_B1 * a * b_B + A_IN * a * b_IN
#        print('A_N_B', A_N_B)

        # Store values
#        self.A_B1 = A_B1
#        self.A_IN_1 = A_IN * b_IN
#        self.A_IN_2 = A_IN * b_IN * a
        self.A_N_B = A_N_B


def calc_annuity_factor(T, q):
    '''Calculation of annuity factor ``a``.

    VDI 2067, section 8.1.1, equation (4)

    Args:
        T (int): observation period (in years) (Nutzungsdauer)

        q (float): interest factor (Zinsfaktor)

    Returns:
        a (float): annuity factor

    '''
    try:
        a = (q-1) / (1-pow(q, -T))  # annuity factor
    except ZeroDivisionError:
        raise ValueError('Cannot calculate annuity factor from observation '
                         'period T=' + str(T) + ' years and interest factor q='
                         + str(q))
    return a


def calc_cash_value_factor(T, r, q):
    '''Calculation of price-dynamic cash value factor.

    VDI 2067, section 8.1.1, equation (5)

    Args:
        T (int): observation period (in years) (Nutzungsdauer)

        q (float): interest factor (Zinsfaktor)

        r (float): price change factor (Preisänderungsfaktor)

    Returns:
        b (float): price-dynamic cash value factor

    '''
    if r == q:
        b = T/q
    else:
        b = (1 - pow(r/q, T))/(q-r)
    return b


if __name__ == "__main__":
    '''If this imported as a module, this part will be skipped.
    If this script is executed directly, we call our main method from here.
    '''
    main_VDI_example()
#    main_database_example()
