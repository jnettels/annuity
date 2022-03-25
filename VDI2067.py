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

"""Calculation of economic efficiency using the VDI 2067 annuity method.

VDI 2067
========
This is an implementation of the calculation of economic efficiency
using the annuity method defined in the German VDI 2067.

    **VDI 2067, Part 1**

    **Economic efficiency of building installations**

    **Fundamentals and economic calculation**

    *September 2012 (ICS 91.140.01)*

Copyright:

    *Verein Deutscher Ingenieure e.V.*

    *VDI Standards Department*

    *VDI-Platz 1, 40468 Duesseldorf, Germany*

Reproduced with the permission of the Verein Deutscher Ingenieure e.V.,
for non-commercial use only.

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

import logging
import math
import locale
import pandas as pd

# Define the logging function
logger = logging.getLogger(__name__)


def main_VDI_example():
    """Run the main VDI example.

    This main method implements the example from VDI 2067 Annex B.
    A small difference between the results may result from rounding.

    This shows the most basic way to add ``parts`` to an energy system,
    define some demands and calculate the annuities.
    """
    # Define output format of logging function
    logging.basicConfig(format='%(asctime)-15s %(message)s')
    logger.setLevel(level='DEBUG')  # Set a default level for the logger

    sys = System()  # Create energy system to add components (parts) to

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

    sys.pprint_parts()  # pretty-print a list of all parts of the system
    sys.pprint_annuities()  # pretty-print the annuities
    sys.pprint_VSE()
    A_VDI_example = -5633.44  # Result of total annuity in official example
    diff = A.sum() - A_VDI_example
    print('Difference to VDI Example:', round(diff, 5), '€ (',
          round(diff/A_VDI_example*100), '%)')


def main_database_example():
    """Run the main database example.

    Main function that shows an example for loading the parts of the
    energy system from a database.
    """
    # Define output format of logging function
    logging.basicConfig(format='%(asctime)-15s %(message)s')
    logger.setLevel(level='INFO')  # Set a default level for the logger

    path = 'Kostendatenbank.xlsx'

    sys = System()
    sys.load_cost_db(path=path)
    # print(sys.cost_db)

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
    sys.calc_annuities(T=T, q=q, df_VSE=df_VSE)  # Series of annuities

    sys.pprint_parts()  # convenience function
    sys.pprint_annuities()  # convenience function
    sys.pprint_VSE()

    sys.calc_investment()
    sys.calc_investment(include_funding=True)

    sys.calc_amortization(pprint=True)


class System():
    """Class representing the energy system.

    Add ``Part`` objects to the energy system to be able to perform the
    economic calculation with ``calc_annuities()``.
    """

    def __init__(self):
        self.cost_db = None  # Cost database; set by load_cost_db()
        self.factors = None  # Constant factors; set by load_cost_db()
        self.parts = []  # List of part objects in system; set by add_parts()
        self.A = None  # Total annuity of the system; set by calc_annuities()
        self.T = 0  # observation period; set in calc_annuities()
        self.q = 1  # observation factor; set in calc_annuities()
        self.df_VSE = pd.DataFrame()  # demand, other, proc.; calc_annuities()
        self.A_N_K_name = 'Capital-related costs'
        self.A_N_B_name = 'Operation-related costs'

    def load_cost_db(self, path=r'Kostendatenbank.xlsx'):
        """Load a database with cost information.

        This function, as well as ``add_part_db()`` expect a certain
        structure and column headers.
        """
        db = pd.read_excel(path, sheet_name='Regressionen',
                           index_col=[0, 1, 2], header=0)
        factors = pd.read_excel(path, sheet_name='Konstanten', index_col=[0],
                                header=0, usecols=[0, 1]).squeeze("columns")
        self.cost_db = db
        self.factors = factors
        return db

    def add_part_db(self, technology, variant, component, size, fund=0,
                    raise_error=True):
        r"""Add a ``Part`` object to the energy system from the cost database.

        Investment cost ``A_0`` is determined with the formula

        .. math:: A_0 = a \cdot size^b \cdot size

        where factor ``a`` and exponent ``b`` are read from the cost database.
        This approach takes into account decreasing relative costs with
        larger installation size.

        Args:
            technology (str): The part's technology, as found in the database.

            variant (str): The part's technology, as found in the database.

            component (str): The part's technology, as found in the database.

            size (float): All required properties are derived from the ``size``
            of the new component. The ``size`` can also be zero, in which case
            there are simply no costs (this allows the use of empty
            placeholders).

            fund (float, optional): Factor for funding of investment amount in
            first year (``fund=0``: no funding, ``fund=1``: 100% funding)

            raise_error (bool, optional): If true, an error is raised if a
            part is not found. Otherwise the error is only logged.

        Returns:
            True (parts are added to ``self.parts``)
        """
        # Savety check
        if self.cost_db is None:
            self.load_cost_db()

        # Determine invest amount
        part_tuple = (technology, variant, component)
        try:
            df = self.cost_db.loc[part_tuple]
        except KeyError as ex:
            if raise_error:
                if logger.isEnabledFor(logging.DEBUG):
                    print(self.cost_db)
                raise IndexError('{} not found in index of database'
                                 .format(part_tuple)) from ex
            else:
                logger.error('%s not found in index of database', part_tuple)
                return False

        a = df['Reg. Faktor']
        b = df['Reg. Exponent']
        if 0 < size < df['Gültig min']:
            logger.warning('Size of part %s is below boundary: %s<%s %s',
                           part_tuple, size, df['Gültig min'],
                           df['Bezugseinheit'])
        elif size > df['Gültig max']:
            logger.warning('Size of part %s is above boundary: %s<%s %s',
                           part_tuple, size, df['Gültig max'],
                           df['Bezugseinheit'])

        if size > 0:
            A_0 = a * pow(size, b) * size  # Investment amount [€]
            f_Op = df['Bedienen']  # Effort for operation [h/a]

        else:  # Allows placeholder parts that have no actual costs
            A_0 = 0
            f_Op = 0

        T_N = df['Nutzungsdauer']  # service life (in years)
        f_Inst = df['Instandsetzung']  # Effort for maintenance
        f_W_Insp = df['Wartung']  # Effort for servicing and inspection

        part_str = ', '.join(part_tuple)
        self.add_part(part_str, A_0, T_N, f_Inst, f_W_Insp, f_Op, fund=fund,
                      size=size, unit=df['Bezugseinheit'])
        return True

    def add_part(self, name, A_0, T_N, f_Inst, f_W_Insp, f_Op, fund=0,
                 size=None, unit=None):
        """Create a new ``Part`` object and add it to the list of parts.

        The list of parts is contained in the energy system. The concept
        of funding (``fund``) is not part of the VDI 2067.

        Args:

            name (str): Name / identifier of the new part (component)

            A_0 (float): Investment amount [€]

            T_N  (int): service life (in years)

            f_Inst (float): Factor for effort for maintenance

            f_W_Insp (float): Factor for effort for servicing and inspection

            f_Op (float): Factor for effort for operation [h/a]

            fund (float): Factor for funding of investment amount in first
            year (``fund=0``: no funding, ``fund=1``: 100% funding)

            size (float): Size of the part when loaded from
            database (optional). Default = None.

            unit (str): Unit corresponding to size (optional)

        Returns:
            None
        """
        new_part = Part(name, A_0, T_N, f_Inst, f_W_Insp, f_Op, fund=fund,
                        size=size, unit=unit)
        self.parts.append(new_part)

    def list_parts(self):
        """Return a list of all parts in the energy system.

        Combine properties and all calculated values from the parts of
        the energy system into one DataFrame.
        """
        s_list = []
        for _part in self.parts:
            s = pd.Series(_part.__dict__)
            s_list.append(s)

        if len(s_list) > 0:  # Normal use (the system contains parts)
            df = pd.concat(s_list, axis=1).T

        else:  # No parts: Create an empty DataFrame with the correct columns
            fake_part = Part('Empty', 0, 0, 0, 0, 0, 0)  # create empty part
            df = pd.concat([pd.Series(fake_part.__dict__)], axis=1).T
            df.drop(0, inplace=True)  # Remove the row

        df.set_index(keys='name', append=True, inplace=True)
        return df

    def calc_investment(self, include_funding=False):
        """Calculate the total investment cost.

        Args:
            include_funding (bool, optional): Instead of the total investment,
            return the investment after applying funding (requires setting
            the argument ``fund`` for the parts in the system).

        Returns:
            A_0_sum (float): Investment cost of all parts
        """
        df_parts = self.list_parts()  # Get DataFrame with all parts
        A_0_sum = df_parts['A_0'].sum()  # Return sum of all investment costs

        if include_funding:
            A_0_sum = (df_parts['A_0']*(1-df_parts['fund'])).sum()

        return A_0_sum

    def calc_annuity(self, **kwargs):
        """Calculate the summed up annuity of total annual payments.

        VDI 2067:
        8.3 Annuity of total annual payments

        This is a simple wrapper around ``calc_annuities()``, returning
        the total annuity (sum) instead of the individual annuities.

        Args:
            See ``calc_annuities()`` for arguments.

        Returns:
            A_N (float): Total annuity of the energy system
        """
        A = self.calc_annuities(**kwargs)
        A_N = A.sum()

        return A_N

    def calc_annuities(self, T=30, q=1.07, r_K=1.03, r_B=1.02, r_I=1.03,
                       r_all=None,
                       price_op=30,
                       df_VSE=pd.DataFrame(),
                       A_N_K_name='Capital-related costs',
                       A_N_B_name='Operation-related costs',
                       ):
        """Calculate the indiviual annuities of total annual payments.

        VDI 2067:
        8 Calculation of economic efficiency using the annuity method

        Defaults for cost factors are picked from VDI 2067 Table B1 Example.
        The nested structure of ``VSE_dict`` may seem complicated at first,
        but allows an unlimitted number of cost types with their individual
        price change factors ``r``. The VDI only differentiates three types.
        'VSE' is for 'Verbrauch-Sonstiges-Erlöse'.

        .. note::
            In your input, define costs as negative and proceeds as positive
            values for the ``price`` of each ``quantity``.

        Args:
            T (int): observation period (in years) (Nutzungsdauer)

            q (float): interest factor (Zinsfaktor)

            r_* (float): price change factors (Preisänderungsfaktor)

            r_all (float): overwrite all other r_* values at once. Set to
            ``None`` or a negative value to ignore.

            price_op (float): price of operation in [€/h]

            df (DataFrame): DataFrame with input data for all annual
            cost types (demand, other, proceeds). Should typically
            consist of two columns "quantity" and "price"). All those
            columns are multiplied to calculate the annuity. The price
            should be negative for costs and positive for proceeds.
            Another required column is ``r``, containing the price change
            factor for each entry.
            The (multi-) index of the DataFrame is preserved in the result
            ``self.df_VSE``, so it can be as complex as necessary to describe
            the input. The results are grouped by index 0 for the return
            ``A`` (series of annuities) of this function.

            +-----------------------+-------------+----------+-------+------+
            | level 0               | level 1     | quantity | price | r    |
            +=======================+=============+==========+=======+======+
            | Demand-related costs  | Heat        | 14012    | -0.06 | 1.03 |
            +                       +-------------+----------+-------+------+
            |                       | Electricity | 417      | -0.20 | 1.03 |
            +-----------------------+-------------+----------+-------+------+
            | Proceeds              | Heat        | 15000    | 0.30  | 1.04 |
            +-----------------------+-------------+----------+-------+------+

            A_N_K_name (str, optional): Name for 'Capital-related costs'.
            If ``None``, skip output of capital-related costs.

            A_N_B_name (str, optional): Name for 'Operation-related costs'
            If ``None``, skip output of operation-related costs.

        Returns:
            A (Pandas Series): Series of all annuities
        """
        if r_all is not None:  # Overwrite all other r_* values at once
            if r_all >= 0:
                r_K = r_B = r_I = r_all

        # Calculate capital and operation annuities for all components (parts)
        for _part in self.parts:
            _part.calc_annuity_capital(T, q, r_K)  # calculate A_N_K
            _part.calc_annuity_operation(T, q, r_B, r_I, price_op)  # A_N_B

        # Get a DataFrame used to calculate the sums of the annuities
        df_parts = self.list_parts()

        # Create a Series of all annuities
        self.A = pd.Series(dtype='object')
        if A_N_K_name is not None:  # If None, skip output
            self.A[A_N_K_name] = df_parts['A_N_K'].sum()
        if A_N_B_name is not None:  # If None, skip output
            self.A[A_N_B_name] = df_parts['A_N_B'].sum()

        if r_all is not None:  # Overwrite all other r_* values at once
            if r_all >= 0:
                df_VSE['r'] = r_all

        # Calculate demand, "other costs" and proceeds for the whole system
        if len(df_VSE) > 0:
            self.df_VSE = self.calc_annuity_cost_template(T, q, df_VSE)
            df_VSE_grouped = self.df_VSE.groupby(level=[0]).sum()
            self.A = pd.concat([self.A, df_VSE_grouped['product']])

        self.T = T
        self.q = q
        self.A_N_K_name = A_N_K_name
        self.A_N_B_name = A_N_B_name
        return self.A

    def calc_annuity_cost_template(self, T, q, df):
        """Calculate annuity of various costs types with the same template.

        Covers the following parts of the VDI, since they all use
        the same formulas:

        - 8.1.2 Demand-related costs (Bedarfsgebundene Kosten)
        - 8.1.4 Other costs (Sonstige Kosten)
        - 8.2 Proceeds (Erlöse)

        Args:
            T (int): observation period (in years) (Nutzungsdauer)

            q (float): interest factor (Zinsfaktor)

            r (float): price change factor (Preisänderungsfaktor)

            df (DataFrame): DataFrame consisting of two columns
            (e.g. quantity and price in first year) that will be
            multiplied to calculate the annual costs. Another
            required column is ``r``, containing the price change
            factor for each entry.

        Returns:
            df (DataFrame): Results with annuities stored in column 'product'
        """
        try:
            df_r = df.pop('r')  # Remove r here to allow use of df.prod()
        except KeyError as ex:
            raise KeyError('The given DataFrame is missing a column "r" '
                           'with the price change factor for each entry'
                           ) from ex
        if df_r.hasnans:
            raise ValueError('The column "r" of the given DataFrame has '
                             'missing values. Make sure to set the price '
                             'change factor "r" for all entries')
        for idx in df.index:
            r = df_r.loc[idx]

            if T > 0:  # Official VDI calculation
                a = calc_annuity_factor(T, q)  # annuity factor
                b = calc_cash_value_factor(T, r, q)  # price-dynamic cash value

            else:  # Calculate without observation period (Not part of VDI!)
                a = b = 1

            df.loc[idx, 'a'] = a  # store annuity factor
            df.loc[idx, 'b'] = b  # store cash value factor
            # Annuity: multiply columns row-wise
            df.loc[idx, 'product'] = df.loc[idx].prod()
            # Fill in other used values
            df.loc[idx, 'T'] = T  # store observation period
            df.loc[idx, 'q'] = q  # store interest factor

        df['r'] = df_r  # restore column with price change factor

        return df

    def calc_amortization(self, pprint=False):
        r"""Calculate the amortization time, including the residual value.

        .. note::
            This calculation is not part of VDI 2067.

        Amortization time is the total invest throughout the observation
        period ``T`` divided by the annual return on invest:

        .. math::
            t_{amort} = \frac{total\ invest}{return\ on\ invest}
            = \frac{-A_{N,K} * T}{A_N - A_{N,K}}

        The total invest includes the initial investments, the replacements
        and the residual value. It is not a present/cash value, but this
        works fine nonetheless.

        If the total annuity :math:`A_N` is zero, the amortization time will be
        equal to the observation period `T`. If ``return on invest`` is
        equal zero or negative, amorisation is not possible and ``NaN`` is
        returned.

        For an alternative calculation with the same result,
        divide the present value of the total invest by the mean
        of all discounted "return on invest" annuities.
        Here `a` is the annuity factor and `q` is the interest factor.

        .. math::
            t_{amort} = \frac{present\ value\ of\ total\ invest}
            {mean\ of\ discounted\ return\ on\ invest}
            = \frac{-A_{N,K} \cdot \frac{1}{a}}
            {\overline{\sum_{i=1}^T{\frac{A_N - A_{N,K}}{(1+q)^i}}}}

        Both approaches include the residual value. This leads to an early
        amortisation compared to an approach where the residual value is
        not included.

        """
        total_invest = self.A[self.A_N_K_name] * self.T * (-1)
        return_on_invest = self.A.sum() - self.A[self.A_N_K_name]

        if return_on_invest > 0:
            t_amort = total_invest / return_on_invest
            if pprint:
                print('Amortization time is {:.1f} years'.format(t_amort))
        else:
            t_amort = float('NaN')
            if pprint:
                print('Amortization is not possible due to negative return '
                      'on invest')

        # Just for reference, an implementation of the alternative formula:
        # a = calc_annuity_factor(self.T, self.q)
        # total_invest = self.A[self.A_N_K_name] * 1/a * (-1)
        # return_on_invest = 0
        # for i in range(1, int(self.T)+1):
        #      r = (self.A.sum() - self.A[self.A_N_K_name]) / pow(self.q, i)
        #      return_on_invest += r/self.T  # build sum and calculate mean
        # t_amort_alt = total_invest / return_on_invest
        # print(t_amort, t_amort_alt, t_amort-t_amort_alt)

        return t_amort

    def calc_NPV(self):
        r"""Calculate net present value of the total annuity.

        (German: Netto-Kapitalwert)

        .. note::
            This calculation is not part of VDI 2067.

        .. math::
            NPV = \frac{annuity}{annuity\ factor}
            = \frac{A_N}{a}
        """
        A = self.A.sum()  # sum of annuities
        a = calc_annuity_factor(self.T, self.q)
        NPV = A / a
        return NPV

    def pprint_parts(self):
        """Pretty print the parts of the energy system to the console."""
        df_parts = self.list_parts()  # Get DataFrame with all parts

        A = self.calc_investment()
        A_funding = self.calc_investment(include_funding=True)

        pd.set_option('display.precision', 2)  # Set number of decimal points
        pd.set_option('display.float_format', self.f_space)
        print('------------- List of parts -------------')
        print(df_parts.to_string())
        print('-----------------------------------------')
        print('Total investment costs:   ', self.f_space(A))
        if A != A_funding:
            print('Investment after funding: ', self.f_space(A_funding))
        print('-----------------------------------------')
        pd.reset_option('display.precision')  # ...reset the setting from above
        pd.reset_option('display.float_format')

        return df_parts

    def pprint_annuities(self):
        """Pretty print the annuities to the console."""
        pd.set_option('display.precision', 2)  # Set number of decimal points
        pd.set_option('display.float_format', self.f_space)
        print('--------------- Annuities ---------------')
        print(self.A.to_string())
        print('-----------------------------------------')
        print('Total annuity:            ', self.f_space(self.A.sum()))
        print('-----------------------------------------')
        pd.reset_option('display.precision')  # ...reset the setting from above
        pd.reset_option('display.float_format')

        return self.A

    def pprint_VSE(self):
        """Pretty-print operation, demand and other costs to the console."""
        pd.set_option('display.precision', 2)  # Set number of decimal points
        pd.set_option('display.float_format', self.f_space)
        print('------------ Annuity details ------------')
        if not self.df_VSE.empty:
            print(self.df_VSE.to_string())
        print('-----------------------------------------')
        pd.reset_option('display.precision')  # ...reset the setting from above
        pd.reset_option('display.float_format')

        return self.df_VSE

    def f_space(self, x):
        """Format and return a float with space as thousands separator."""
        locale.setlocale(locale.LC_ALL, '')
        return locale.format_string('%14.2f', x, grouping=True)


class Part():
    """Representation of a component of an energy system.

    Stores all properties of the component and can calculate its own
    capital-related costs and operation-related costs.
    """

    def __init__(self, name, A_0, T_N, f_Inst, f_W_Insp, f_Op, fund=0,
                 size=None, unit=None):
        self.name = name  # Name of the component
        self.size = size  # Size of the part when loaded from database
        self.unit = unit  # Unit corresponding to size
        self.A_0 = A_0  # Investment amount [€]
        self.T_N = T_N  # service life (in years)
        self.f_Inst = f_Inst  # Effort for maintenance
        self.f_W_Insp = f_W_Insp  # Effort for servicing and inspection
        self.f_Op = f_Op  # Effort for operation [h/a]
        self.fund = fund  # factor for funding

        # To be calculated by calc_annuity_capital()
        self.A = []  # list of cash values for all procured replacements
        self.n = None  # number of replacements
        self.R_W = None  # residual value
        self.A_N_K = None  # annuity of the capital-related costs

        # To be calculated by calc_annuity_operation()
        self.A_N_B = None  # annuity of the operation-related costs

    def calc_annuity_capital(self, T, q, r):
        """Calculate annuity of capital-related costs.

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
        """
        if T <= 0:  # Calc without observation period (Not part of VDI 2067!)
            T = self.T_N  # Calculate each part with its own service life time

        # Calculation as defined in VDI 2067:
        a = calc_annuity_factor(T, q)  # annuity factor

        # number of replacements procured within the observation period
        if self.T_N == 0:
            n = 0  # for one-time expenses, like "planning"
        else:
            n = math.ceil(T/self.T_N) - 1
        # print(T, self.T_N, n)

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

        # annuity of the capital-related costs with negative sign applied
        A_N_K = (sum(A) - R_W) * a * (-1)

        # Store values
        self.A = A  # list of cash values for all procured replacements
        self.n = n  # number of replacements
        self.R_W = R_W  # residual value
        self.A_N_K = A_N_K  # annuity of the capital-related costs

    def calc_annuity_operation(self, T, q, r_B, r_I, price_op):
        """Calculate annuity of operation-related costs.

        8.1.3 Operation-related costs (Betriebsgebundene Kosten)

        Args:
            T (int): observation period (in years) (Nutzungsdauer)

            q (float): interest factor (Zinsfaktor)

            r (float): price change factor (Preisänderungsfaktor)

            price_op (float): price of operation [€/h]

        Returns:
            None
        """
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

        # annuity of the operation-related costs with negative sign applied
        A_N_B = (A_B1 * a * b_B + A_IN * a * b_IN) * (-1)

        # Store values
        self.A_N_B = A_N_B


def calc_annuity_factor(T, q):
    """Calculate annuity factor ``a``.

    VDI 2067, section 8.1.1, equation (4)

    Args:
        T (int): observation period (in years) (Nutzungsdauer)

        q (float): interest factor (Zinsfaktor)

    Returns:
        a (float): annuity factor

    """
    if T <= 0:  # Not part of VDI 2067!
        return 1

    if q == 1.0:  # Interest rate zero
        a = 1/T
    else:
        try:
            a = (q-1) / (1-pow(q, -T))  # annuity factor
        except ZeroDivisionError as ex:
            raise ValueError('Cannot calculate annuity factor from observation'
                             ' period T={} years and interest '
                             'factor q={}'.format(T, q)) from ex
    return a


def calc_cash_value_factor(T, r, q):
    """Calculate price-dynamic cash value factor ``b``.

    VDI 2067, section 8.1.1, equation (5)

    Args:
        T (int): observation period (in years) (Nutzungsdauer)

        r (float): price change factor (Preisänderungsfaktor)

        q (float): interest factor (Zinsfaktor)

    Returns:
        b (float): price-dynamic cash value factor

    """
    if T <= 0:  # Not part of VDI 2067!
        return 1

    if r == q:
        b = T/q
    else:
        b = (1 - pow(r/q, T))/(q-r)
    return b


if __name__ == "__main__":
    # If this imported as a module, this part will be skipped.
    # If this script is executed directly, we call our main method from here.
    main_VDI_example()
    # main_database_example()
