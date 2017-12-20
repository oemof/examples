# -*- coding: utf-8 -*-
"""
General description:
---------------------
Example from the SDEWES conference paper:

Simon Hilpert, Cord Kaldemeyer, Uwe Krien, Stephan Günther (2017).
'Solph - An Open Multi Purpose Optimisation Library for Flexible
         Energy System Analysis'. Paper presented at SDEWES Conference,
         Dubrovnik.

Installation requirements:
---------------------------
This example requires the latest version of oemof. Install by:

    pip install oemof

"""
import os
import pandas as pd

from oemof.network import Node
from oemof.outputlib.graph_tools import graph
from oemof.outputlib import processing, views
from oemof.solph import (EnergySystem, Bus, Source, Sink, Flow,
                         Model, Investment, components)
from oemof.tools import economics

timeindex = pd.date_range('1/1/2017', periods=8760, freq='H')

energysystem = EnergySystem(timeindex=timeindex)
Node.registry = energysystem
#################################################################
# data
#################################################################
# Read data file
full_filename = os.path.join(os.path.dirname(__file__),
                             'timeseries.csv')
timeseries = pd.read_csv(full_filename, sep=',')

costs = {'pp_wind': {
             'epc': economics.annuity(capex=1000, n=20, wacc=0.05)},
         'pp_pv': {
             'epc': economics.annuity(capex=750, n=20, wacc=0.05)},
         'pp_diesel': {
             'epc': economics.annuity(capex=300, n=10, wacc=0.05),
             'var': 30},
         'pp_bio': {
             'epc': economics.annuity(capex=1000, n=10, wacc=0.05),
             'var': 50},
         'storage': {
             'epc': economics.annuity(capex=1500, n=10, wacc=0.05),
             'var': 0}}
#################################################################
# Create oemof object
#################################################################

bel = Bus(label='micro_grid')

Sink(label='excess',
     inputs={bel: Flow(variable_costs=10e3)})

Source(label='pp_wind',
       outputs={
           bel: Flow(nominal_value=None, fixed=True,
                     actual_value=timeseries['wind'],
                     investment=Investment(ep_costs=costs['pp_wind']['epc']))})

Source(label='pp_pv',
       outputs={
           bel: Flow(nominal_value=None, fixed=True,
                     actual_value=timeseries['pv'],
                     investment=Investment(ep_costs=costs['pp_wind']['epc']))})

Source(label='pp_diesel',
       outputs={
           bel: Flow(nominal_value=None,
                     variable_costs=costs['pp_diesel']['var'],
                     investment=Investment(ep_costs=costs['pp_diesel']['epc']))})

Source(label='pp_bio',
       outputs={
           bel: Flow(nominal_value=None,
                     variable_costs=costs['pp_bio']['var'],
                     summed_max=300e3,
                     investment=Investment(ep_costs=costs['pp_bio']['epc']))})

Sink(label='demand_el',
     inputs={
         bel: Flow(actual_value=timeseries['demand_el'],
                   fixed=True, nominal_value=500)})

components.GenericStorage(
    label='storage',
    inputs={
        bel: Flow()},
    outputs={
        bel: Flow()},
    capacity_loss=0.00,
    initial_capacity=0.5,
    nominal_input_capacity_ratio=1/6,
    nominal_output_capacity_ratio=1/6,
    inflow_conversion_factor=0.95,
    outflow_conversion_factor=0.95,
    investment=Investment(ep_costs=costs['storage']['epc']))

#################################################################
# Create model and solve
#################################################################

m = Model(energysystem)

# om.write(filename, io_options={'symbolic_solver_labels': True})

m.solve(solver='cbc', solve_kwargs={'tee': True})

results = processing.results(m)

views.node(results, 'storage')

views.node(results, 'micro_grid')['sequences'].plot(drawstyle='steps')

graph = graph(energysystem, m, plot=True, layout='neato', node_size=3000,
              node_color={'micro_grid': '#7EC0EE'})
