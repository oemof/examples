# -*- coding: utf-8 -*-

"""
General description
--------------------
This example shows the usage of the plot module of oemof-visio.
The plot module focuses on a balance plot around one bus where all input flows
are stacked area/bar plots and all output flows stacked line plots. These plots
can be useful to test new components or debug complex energy systems.

Moreover there are functions that can be used with normal pandas plots as well.
Three examples show the pandas plot and how it can be easily manipulated using
the oemof-visio plot functions.

Installation requirements
-------------------------
The example is made for oemof v0.2.x.

    pip install "oemof>=0.2,<0.3"

The oemof-visio provides the base for the created i/o plot.

    pip install git+https://github.com/oemof/oemof_visio.git
"""

__copyright__ = "oemof developer group"
__license__ = "GPLv3"

import logging
import os
import pandas as pd
import matplotlib.pyplot as plt

from oemof import solph
from oemof.outputlib import processing, views
from oemof.tools import logger
from oemof.tools import economics
from oemof.network import Node

import oemof_visio as oev


def shape_legend(node, reverse=False, **kwargs):
    handels = kwargs['handles']
    labels = kwargs['labels']
    axes = kwargs['ax']
    parameter = {}

    new_labels = []
    for label in labels:
        label = label.replace('(', '')
        label = label.replace('), flow)', '')
        label = label.replace(node, '')
        label = label.replace(',', '')
        label = label.replace(' ', '')
        new_labels.append(label)
    labels = new_labels

    parameter['bbox_to_anchor'] = kwargs.get('bbox_to_anchor', (1, 0.5))
    parameter['loc'] = kwargs.get('loc', 'center left')
    parameter['ncol'] = kwargs.get('ncol', 1)
    plotshare = kwargs.get('plotshare', 0.9)

    if reverse:
        handels = handels.reverse()
        labels = labels.reverse()

    box = axes.get_position()
    axes.set_position([box.x0, box.y0, box.width * plotshare, box.height])

    parameter['handles'] = handels
    parameter['labels'] = labels
    axes.legend(**parameter)
    return axes


logger.define_logging()
logging.info('Initialize the energy system')

date_time_index = pd.date_range('1/1/2012', periods=24*7*8, freq='H')

energysystem = solph.EnergySystem(timeindex=date_time_index)
Node.registry = energysystem

full_filename = os.path.join(os.path.dirname(__file__),
                             'storage_investment.csv')
data = pd.read_csv(full_filename, sep=",")

logging.info('Create oemof objects')
bgas = solph.Bus(label="natural_gas")
bel = solph.Bus(label="electricity")

solph.Sink(label='excess_bel', inputs={bel: solph.Flow()})

solph.Source(label='rgas', outputs={bgas: solph.Flow(nominal_value=29825293,
                                                     summed_max=1)})

solph.Source(label='wind', outputs={bel: solph.Flow(
    actual_value=data['wind'], nominal_value=1000000, fixed=True)})

solph.Source(label='pv', outputs={bel: solph.Flow(
    actual_value=data['pv'], nominal_value=582000, fixed=True)})

solph.Sink(label='demand', inputs={bel: solph.Flow(
    actual_value=data['demand_el'], fixed=True, nominal_value=1)})

solph.Transformer(
    label="pp_gas",
    inputs={bgas: solph.Flow()},
    outputs={bel: solph.Flow(nominal_value=10e10, variable_costs=50)},
    conversion_factors={bel: 0.58})

epc = economics.annuity(capex=1000, n=20, wacc=0.05)
storage = solph.components.GenericStorage(
    label='storage',
    inputs={bel: solph.Flow(variable_costs=10e10)},
    outputs={bel: solph.Flow(variable_costs=10e10)},
    capacity_loss=0.00, initial_capacity=0,
    nominal_input_capacity_ratio=1/6,
    nominal_output_capacity_ratio=1/6,
    inflow_conversion_factor=1, outflow_conversion_factor=0.8
    investment=solph.Investment(ep_costs=epc),
)

logging.info('Optimise the energy system')

om = solph.Model(energysystem)

logging.info('Solve the optimization problem')
om.solve(solver='cbc')

##########################################################################
# Plotting
##########################################################################

# Getting results and views
results = processing.results(om)
custom_storage = views.node(results, 'storage')
electricity_bus = views.node(results, 'electricity')

# ***** 1. example ***************************************************
# Plot directly using pandas
custom_storage['sequences'].plot(kind='line', drawstyle='steps-post')

# Change the datetime ticks
ax = custom_storage['sequences'].reset_index(drop=True).plot(
    kind='line', drawstyle='steps-post')
ax.set_xlabel('2012')
ax.set_title('Change the xticks.')
oev.plot.set_datetime_ticks(ax, custom_storage['sequences'].index,
                            date_format='%d-%m', number_autoticks=6)
plt.show()

# ***** 2. example ***************************************************
cdict = {
    (('electricity', 'demand'), 'flow'): '#ce4aff',
    (('electricity', 'excess_bel'), 'flow'): '#555555',
    (('electricity', 'storage'), 'flow'): '#42c77a',
    (('pp_gas', 'electricity'), 'flow'): '#636f6b',
    (('pv', 'electricity'), 'flow'): '#ffde32',
    (('storage', 'electricity'), 'flow'): '#42c77a',
    (('wind', 'electricity'), 'flow'): '#5b5bae'}

# Plot directly using pandas
electricity_bus['sequences'].plot(kind='line', drawstyle='steps-post')

# Change the colors using the dictionary above to define the colors
colors = oev.plot.color_from_dict(cdict, electricity_bus['sequences'])
ax = electricity_bus['sequences'].plot(kind='line', drawstyle='steps-post',
                                       color=colors)
ax.set_title('Change the colors.')
plt.show()

# ***** 3. example ***************************************************
# Plot directly using pandas
electricity_bus['sequences'].plot(kind='line', drawstyle='steps-post')

# Plot only input flows
in_cols = oev.plot.divide_bus_columns(
    'electricity', electricity_bus['sequences'].columns)['in_cols']
ax = electricity_bus['sequences'][in_cols].plot(kind='line',
                                                drawstyle='steps-post')
ax.set_title('Show only input flows.')
plt.show()

# ***** 4. example ***************************************************
# Create a plot to show the balance around a bus.
# Order and colors are customisable.

inorder = [(('pv', 'electricity'), 'flow'),
           (('wind', 'electricity'), 'flow'),
           (('storage', 'electricity'), 'flow'),
           (('pp_gas', 'electricity'), 'flow')]

fig = plt.figure(figsize=(10, 5))
electricity_seq = views.node(results, 'electricity')['sequences']
plot_slice = oev.plot.slice_df(electricity_seq,
                               date_from=pd.datetime(2012, 2, 15))
my_plot = oev.plot.io_plot('electricity', plot_slice, cdict=cdict,
                           inorder=inorder, ax=fig.add_subplot(1, 1, 1),
                           smooth=False)
ax = shape_legend('electricity', **my_plot)
oev.plot.set_datetime_ticks(ax, plot_slice.index, tick_distance=48,
                            date_format='%d-%m-%H', offset=12)

ax.set_ylabel('Power in MW')
ax.set_xlabel('2012')
ax.set_title("Electricity bus")

# ***** 5. example ***************************************************
# Create a plot to show the balance around a bus.
# Make a smooth plot even though it is not scientifically correct.

inorder = [(('pv', 'electricity'), 'flow'),
           (('wind', 'electricity'), 'flow'),
           (('storage', 'electricity'), 'flow'),
           (('pp_gas', 'electricity'), 'flow')]

fig = plt.figure(figsize=(10, 5))
electricity_seq = views.node(results, 'electricity')['sequences']
plot_slice = oev.plot.slice_df(electricity_seq,
                               date_from=pd.datetime(2012, 2, 15))
my_plot = oev.plot.io_plot('electricity', plot_slice, cdict=cdict,
                           inorder=inorder, ax=fig.add_subplot(1, 1, 1),
                           smooth=True)
ax = shape_legend('electricity', **my_plot)
ax = oev.plot.set_datetime_ticks(ax, plot_slice.index, tick_distance=48,
                                 date_format='%d-%m-%H', offset=12)

ax.set_ylabel('Power in MW')
ax.set_xlabel('2012')
ax.set_title("Electricity bus")
plt.show()
