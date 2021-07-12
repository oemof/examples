# -*- coding: utf-8 -*-
"""
General description
-------------------
Example from the SDEWES conference paper:

Simon Hilpert, Cord Kaldemeyer, Uwe Krien, Stephan Günther (2017).
'Solph - An Open Multi Purpose Optimisation Library for Flexible
         Energy System Analysis'. Paper presented at SDEWES Conference,
         Dubrovnik.


Data
----
timeseries.csv

Installation requirements
-------------------------
This example requires the latest version of oemof and others. Install by:

    pip install oemof matplotlib networkx pygraphviz

"""
import os
import pandas as pd
import networkx as nx
from matplotlib import pyplot as plt

from oemof.network import Node
from oemof.outputlib import processing, views
from oemof.solph import (EnergySystem, Bus, Source, Sink, Flow,
                         Model, Investment, components)
from oemof.tools import economics
from oemof.graph import create_nx_graph as create_graph


def draw_graph(grph, edge_labels=True, node_color='#AFAFAF',
               edge_color='#CFCFCF', plot=True, node_size=2000,
               with_labels=True, arrows=True, layout='neato'):
    """
    Draw a graph. This function will be removed in future versions.

    Parameters
    ----------
    grph : networkxGraph
        A graph to draw.
    edge_labels : boolean
        Use nominal values of flow as edge label
    node_color : dict or string
        Hex color code oder matplotlib color for each node. If string, all
        colors are the same.

    edge_color : string
        Hex color code oder matplotlib color for edge color.

    plot : boolean
        Show matplotlib plot.

    node_size : integer
        Size of nodes.

    with_labels : boolean
        Draw node labels.

    arrows : boolean
        Draw arrows on directed edges. Works only if an optimization_model has
        been passed.
    layout : string
        networkx graph layout, one of: neato, dot, twopi, circo, fdp, sfdp.
    """
    if type(node_color) is dict:
        node_color = [node_color.get(g, '#AFAFAF') for g in grph.nodes()]

    # set drawing options
    options = {
     'prog': 'dot',
     'with_labels': with_labels,
     'node_color': node_color,
     'edge_color': edge_color,
     'node_size': node_size,
     'arrows': arrows
    }

    # draw graph
    pos = nx.drawing.nx_agraph.graphviz_layout(grph, prog=layout)

    nx.draw(grph, pos=pos, **options)

    # add edge labels for all edges
    if edge_labels is True and plt:
        labels = nx.get_edge_attributes(grph, 'weight')
        nx.draw_networkx_edge_labels(grph, pos=pos, edge_labels=labels)

    # show output
    if plot is True:
        plt.show()


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
                     investment=Investment(ep_costs=costs['pp_diesel']['epc']))}
       )

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
    invest_relation_input_capacity=1/6,
    invest_relation_output_capacity=1/6,
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

plt.show()

graph = create_graph(energysystem, m)
draw_graph(graph, plot=True, layout='neato', node_size=3000, arrows=False,
           node_color={'micro_grid': '#7EC0EE'})
