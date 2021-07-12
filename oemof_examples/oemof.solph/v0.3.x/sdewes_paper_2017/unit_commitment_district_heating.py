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
from oemof.solph import (EnergySystem, Bus, Source, Sink, Flow, NonConvex,
                         Model, Transformer, components)
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


timeindex = pd.date_range('1/1/2017', periods=168, freq='H')

energysystem = EnergySystem(timeindex=timeindex)
Node.registry = energysystem
##########################################################################
# data
##########################################################################
# Read data file
full_filename = os.path.join(os.path.dirname(__file__),
                             "timeseries.csv")
timeseries = pd.read_csv(full_filename, sep=",")

##########################################################################
# Create oemof objects
##########################################################################

bel = Bus(label="bel")

bgas = Bus(label="bgas")

bth = Bus(label="bth")

Source(label="gas",
       outputs={bgas: Flow(variable_costs=35)})

Transformer(label='boiler',
            inputs={
                bgas: Flow()},
            outputs={
                bth: Flow(nominal_value=500,
                          variable_cost=50,
                          nonconvex=NonConvex())},
            conversion_factors={bth: 0.9})

Transformer(label='chp',
            inputs={
                bgas: Flow()},
            outputs={
                bel: Flow(nominal_value=300, min=0.5,
                          nonconvex=NonConvex()),
                bth: Flow()},
            conversion_factors={bth: 0.3, bel: 0.45})


Sink(label='demand_th',
     inputs={
         bth: Flow(actual_value=timeseries['demand_th'],
                   fixed=True, nominal_value=500)})

Sink(label='spot_el',
     inputs={
         bel: Flow(variable_costs=timeseries['price_el'])})


components.GenericStorage(
    label='storage_th',
    inputs={
        bth: Flow(nominal_value=1500/6)},
    outputs={
        bth: Flow(nominal_value=1500/6)},
    nominal_capacity=1500,
    capacity_loss=0.00,
    initial_capacity=0.5)

##########################################################################
# Create model and solve
##########################################################################

m = Model(energysystem)
# om.write(filename, io_options={'symbolic_solver_labels': True})

m.solve(solver='cbc', solve_kwargs={'tee': True})

results = processing.results(m)

views.node(results, 'bth')['sequences'][1:168].plot(drawstyle='steps')
plt.show()

graph = create_graph(energysystem, m)
draw_graph(graph, plot=True)
