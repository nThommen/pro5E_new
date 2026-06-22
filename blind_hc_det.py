#%% Imports
import matplotlib
import pandas as pd
import pandapower as pp, pandapower.topology as top, pandapower.networks as pn
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from numpy.random import default_rng

#%% Functions
# Load a desired network and set each bus-load to zero
# Load network- and print-methods by Dirk Schmidt
def load_network(generation):
    #net = pn.kb_extrem_vorstadtnetz_1()
    #net = pn.create_kerber_landnetz_kabel_1()
    #net = pn.create_kerber_dorfnetz()
    net = pn.create_kerber_vorstadtnetz_kabel_1()
    net.bus['zone'] = net.bus['name'].str.split('_').str[-2]
    net.line['zone'] = net.line['name'].str.split('_').str[-2]
    net.trafo['zone'] = 'Trafostation'
    dist = top.calc_distance_to_bus(net, 1, respect_switches=True)
    dist.name = 'distance2ts'
    net.bus = net.bus.merge(dist.to_frame(), left_index=True, right_index=True, how='left')
    if generation:
        net.load.scaling = 0.1
    if not generation:
        net.load.scaling = 0.8
    buses_to_test = []

    for idx, row in net.bus.iterrows():
        name = row.get("name")
        if isinstance(name, str) and "loadbus" in name:
            buses_to_test.append(idx)

            loads_at_bus = net.load[net.load["bus"] == idx]
            p_mw = loads_at_bus["p_mw"].sum()
            q_mvar = loads_at_bus["q_mvar"].sum()

            print("Wirkleistung am Bus ", idx, ": ", p_mw)
            print("Blindleistung am Bus ", idx, ": ", q_mvar)
    return net, buses_to_test


def check_violations(net, max_voltage, min_voltage, max_line_loading, max_transformer_loading):
    try:
        pp.runpp(net)
    except:
        return True, "No Convergence", None
    if net.res_line.loading_percent.max() > max_line_loading * 100:
        return True, "Line Overloading", net.line.index[net.res_line.loading_percent.idxmax()]
    elif net.res_trafo.loading_percent.max() > max_transformer_loading * 100:
        return True, "Transformer Overloading", net.trafo.index[net.res_trafo.loading_percent.idxmax()]
    elif net.res_bus.vm_pu.max() > max_voltage:
        return True, "Voltage Violation", net.bus.index[net.res_bus.vm_pu.idxmax()]
    elif net.res_bus.vm_pu.min() < min_voltage:
        return True, "Voltage Violation", net.bus.index[net.res_bus.vm_pu.idxmin()]
    else:
        return False, None, None


def calculate_deterministic_hc(generation,
                               step_size,
                               max_voltage,
                               min_voltage,
                               max_line_loading,
                               max_transformer_loading):
    net, buses_to_test = load_network(generation)
    installed_pv = 0
    installed_ev = 0
    run_nrs = 0
    for bus in buses_to_test:
        if generation:
            pp.create_sgen(net, bus, p_mw=0.0, q_mvar=0.0)
        else:
            pp.create_load(net, bus, p_mw=0.0, q_mvar=0.0)
    while True:
        run_nrs += 1
        violated, reason, index = check_violations(net, max_voltage, min_voltage, max_line_loading,
                                                   max_transformer_loading)
        if violated:
            print(f"Violation detected: {reason} at index {index}")
            break
        # Update all buses in the test set simultaneously for a uniform growth baseline
        if generation:
            net.sgen.loc[net.sgen.bus.isin(buses_to_test), "p_mw"] += step_size
            installed_pv += step_size * len(buses_to_test)
        else:
            net.load.loc[net.load.bus.isin(buses_to_test), "p_mw"] += step_size
            installed_ev += step_size * len(buses_to_test)
    PV_hc = installed_pv - len(buses_to_test) * step_size
    EV_hc = installed_ev - len(buses_to_test) * step_size
    print("Number of runs: ", run_nrs)

    print("Bus Results:")
    bus_results = net.bus[['name', 'zone', 'distance2ts']].merge(net.res_bus[['vm_pu', 'p_mw', 'q_mvar']], how='left',
                                                                 left_index=True, right_index=True)
    critical_bus_results = bus_results[(bus_results['vm_pu'] < 0.90) | (bus_results['vm_pu'] > 1.03)]
    if critical_bus_results.empty:
        critical_bus_results = 'no bus voltage violation'
    print(critical_bus_results)

    print("\nLine Results:")
    line_results = net.line[['name', 'zone']].merge(net.res_line[['p_from_mw', 'i_ka', 'loading_percent']], how='left',
                                                    left_index=True, right_index=True)
    critical_line_results = line_results[line_results['loading_percent'] > 100]
    if critical_line_results.empty:
        critical_line_results = 'no line overload'
    print(critical_line_results)

    print("\nTransformers Results:")
    trafo_results = net.trafo[['name', 'zone']].merge(net.res_trafo[['p_hv_mw', 'p_lv_mw', 'loading_percent']],
                                                      how='left', left_index=True, right_index=True)
    element_results = pd.concat([trafo_results, line_results], axis=0).reset_index(drop=True)
    critical_trafo_results = trafo_results[trafo_results['loading_percent'] > 100]
    if critical_trafo_results.empty:
        critical_trafo_results = 'no transformer overload'
    print(critical_trafo_results)

    # Ergebnisplot anzeigen
    pp.plotting.pf_res_plotly(net)
    pp.plotting.simple_plot(net, plot_sgens=True, plot_loads=True, ext_grid_size=1, bus_size=0.5, load_size=1,
                            sgen_size=1)

    return PV_hc, EV_hc

#%% Run
step_size = 1e-4 # Size of PV systems in MW

max_voltage = 1.03 # Maximum bus voltage in p.u.
min_voltage = 0.90 # Minimum bus voltage in p.u.
max_line_loading = 1.0 # Maximum line loading in p.u.
max_transformer_loading = 1.0 # Maximum transformer loading in p.u.

# For generation pass argument True, for no generation pass False
generation = False

PV_hc, EV_hc = calculate_deterministic_hc(generation,
                                          step_size,
                                          max_voltage,
                                          min_voltage,
                                          max_line_loading,
                                          max_transformer_loading)

print("Installed PV: ", PV_hc, "MW")
print("Installed EV: ", EV_hc, "MW")
