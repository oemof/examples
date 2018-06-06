# -*- coding: utf-8 -*-

"""
General description
-------------------
This example shows how to perform a capacity optimization for
an energy system with storage. The following energy system is modeled:

                input/output  bgas     bel
                     |          |        |       |
                     |          |        |       |
 wind(FixedSource)   |------------------>|       |
                     |          |        |       |
 pv(FixedSource)     |------------------>|       |
                     |          |        |       |
 gas_resource        |--------->|        |       |
 (Commodity)         |          |        |       |
                     |          |        |       |
 demand(Sink)        |<------------------|       |
                     |          |        |       |
                     |          |        |       |
 pp_gas(Transformer) |<---------|        |       |
                     |------------------>|       |
                     |          |        |       |
 storage1(Storage)   |<------------------|       |
                     |------------------>|       |
 storage2(Storage)   |<------------------|       |
                     |------------------>|       |

The example exists in four variations. The following parameters describe
the main setting for the optimization variation 1:

    - optimize wind, pv, gas_resource and storage
    - set investment cost for wind, pv and storage
    - set gas price for kWh

    Results show an installation of wind and the use of the gas resource.
    A renewable energy share of 51% is achieved.

    Have a look at different parameter settings. There are four variations
    of this example in the same folder.

Data
----
storage_investment.csv

Installation requirements
-------------------------
This example requires oemof v0.2. Install by:

    pip install oemof

"""

###############################################################################
# Imports
###############################################################################

# Default logger of oemof
from oemof.tools import logger
from oemof.tools import economics
import oemof.solph as solph
from oemof.outputlib import processing, views
import logging
import os
import pandas as pd
import pprint as pp

number_timesteps = 8760

##########################################################################
# Initialize the energy system and read/calculate necessary parameters
##########################################################################

logger.define_logging()
logging.info('Initialize the energy system')
date_time_index = pd.date_range('1/1/2012', periods=number_timesteps,
                                freq='H')

energysystem = solph.EnergySystem(timeindex=date_time_index)

# Read data file
full_filename = os.path.join(os.path.dirname(__file__),
    'storage_investment.csv')
data = pd.read_csv(full_filename, sep=",")

price_gas = 0.06

# If the period is one year the equivalent periodical costs (epc) of an
# investment are equal to the annuity. Use oemof's economic tools.
epc_wind = economics.annuity(capex=1000, n=20, wacc=0.05)
epc_pv = economics.annuity(capex=1000, n=20, wacc=0.05)
epc_storage = economics.annuity(capex=75, n=20, wacc=0.05)

##########################################################################
# Create oemof objects
##########################################################################

logging.info('Create oemof objects')
# create natural gas bus
bgas = solph.Bus(label="natural_gas")

# create electricity bus
bel = solph.Bus(label="electricity")

energysystem.add(bgas, bel)

# create excess component for the electricity bus to allow overproduction
excess = solph.Sink(label='excess_bel', inputs={bel: solph.Flow()})

# create source object representing the natural gas commodity (annual limit)
gas_resource = solph.Source(label='rgas', outputs={bgas: solph.Flow(
    variable_costs=price_gas)})

# create fixed source object representing wind power plants
wind = solph.Source(label='wind', outputs={bel: solph.Flow(
    actual_value=data['wind'], fixed=True,
    investment=solph.Investment(ep_costs=epc_wind))})

# create fixed source object representing pv power plants
pv = solph.Source(label='pv', outputs={bel: solph.Flow(
    actual_value=data['pv'], fixed=True,
    investment=solph.Investment(ep_costs=epc_pv))})

# create simple sink object representing the electrical demand
demand = solph.Sink(label='demand', inputs={bel: solph.Flow(
    actual_value=data['demand_el'], fixed=True, nominal_value=1)})

# create simple transformer object representing a gas power plant
pp_gas = solph.Transformer(
    label="pp_gas",
    inputs={bgas: solph.Flow()},
    outputs={bel: solph.Flow(nominal_value=10e10, variable_costs=0)},
    conversion_factors={bel: 0.58})

# create storage object representing a battery

# create storage object representing a storage with flow coupled to the storage capacity
# The flow investment can be specified with costs, but do not have to. Default value is '0'.
# The 'maximum' investment for the input flow is 100 000. This sets the boundary for the capacity investment
# and thus also for the output flow.

storage1 = solph.components.GenericStorage(
    label='storage1',
    inputs={bel: solph.Flow(investment = solph.Investment(ep_costs=epc_storage, maximum=100000))},
    outputs={bel: solph.Flow(investment = solph.Investment(ep_costs=0))},
    capacity_loss=0.00, initial_capacity=0,
    invest_relation_input_capacity=1/6,
    invest_relation_output_capacity=1/6,
    inflow_conversion_factor=1, outflow_conversion_factor=0.8,
    investment=solph.Investment(ep_costs=epc_storage),
)

# create storage object representing a storage with the input flow coupled
#to the output flow with a ratio of 4 : 6. The input flow is also coupled to
#the capacity with a ratio of 1 : 6 - thus also coupling the outflow.

storage2 = solph.components.GenericStorage(
    label='storage2',
    inputs={bel: solph.Flow(investment = solph.Investment(ep_costs=epc_storage))},
    outputs={bel: solph.Flow(variable_costs=0.0001, investment = solph.Investment(ep_costs=0))},
    capacity_loss=0.00, initial_capacity=0,
    invest_relation_input_capacity=1/6,
    invest_relation_input_output = 4/6,
    inflow_conversion_factor=1, outflow_conversion_factor=0.8,
    investment=solph.Investment(ep_costs=epc_storage),
)

energysystem.add(excess, gas_resource, wind, pv, demand, pp_gas, storage1, storage2)

##########################################################################
# Optimise the energy system
##########################################################################

logging.info('Optimise the energy system')

# initialise the operational model
om = solph.Model(energysystem)

# if tee_switch is true solver messages will be displayed
logging.info('Solve the optimization problem')
om.solve(solver='cbc', solve_kwargs={'tee': True})

##########################################################################
# Check and plot the results
##########################################################################

# check if the new result object is working for custom components
results = processing.results(om)

custom_storage = views.node(results, 'storage1')
custom_storage = views.node(results, 'storage2')

electricity_bus = views.node(results, 'electricity')

meta_results = processing.meta_results(om)
pp.pprint(meta_results)

my_results = electricity_bus['scalars']

# installed capacity of storage in GWh
my_results['storage1_invest_GWh'] = (results[(storage1, None)]
                            ['scalars']['invest']/1e6)

my_results['storage2_invest_GWh'] = (results[(storage2, None)]
                            ['scalars']['invest']/1e6)

# installed capacity of wind power plant in MW
my_results['wind_invest_MW'] = (results[(wind, bel)]
                            ['scalars']['invest']/1e3)

# resulting renewable energy share
my_results['res_share'] = (1 - results[(pp_gas, bel)]
                            ['sequences'].sum()/results[(bel, demand)]
                            ['sequences'].sum())

pp.pprint(my_results)

