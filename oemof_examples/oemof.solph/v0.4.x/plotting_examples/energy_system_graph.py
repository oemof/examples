# -*- coding: utf-8 -*-

"""
General description
-------------------

A basic example to show how to create a graph of an energy system with oemof_visio.ESGraphRenderer


Installation requirements
-------------------------

The oemof-visio provides the base for the created energy system graph.

    pip install git+https://github.com/oemof/oemof_visio.git

On windows the installation of pygraphviz might not work, you can install the package from conda

    conda install -c alubbock graphviz pygraphviz

You then need to initialize the plugins of the "dot" language by running

    dot -c

in a terminal
"""

__copyright__ = "oemof developer group"
__license__ = "GPLv3"

from oemof.solph import (
    EnergySystem,
    Sink,
    Source,
    Transformer,
    Bus,
    Flow,
    GenericStorage,
)
from oemof_visio import ESGraphRenderer

es = EnergySystem()
bus_ac = Bus(label="AC")
bus_dc = Bus(label="DC")
wind = Source(label="wind", outputs={bus_ac: Flow()})
pv = Source(label="pv", outputs={bus_dc: Flow()})
demand_el = Sink(label="demand_el", inputs={bus_ac: Flow()})
storage_el = GenericStorage(
    label="storage_el",
    inputs={bus_ac: Flow()},
    outputs={bus_ac: Flow()},
)
pv_converter = Transformer(
    label="chp_gas", inputs={bus_dc: Flow()}, outputs={bus_ac: Flow()}
)
excess_el = Sink(label="excess_el", inputs={bus_ac: Flow()})
es.add(bus_ac, bus_dc, wind, pv, demand_el, storage_el, excess_el, pv_converter)
gr = ESGraphRenderer(energy_system=es, filepath="energy_system", img_format="png")
gr.view()
