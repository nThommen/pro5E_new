#%% Imports
import pandas as pd
import pandapower as pp, pandapower.topology as top, pandapower.networks as pn
import matplotlib.pyplot as plt
import seaborn as sns
import kaleido

from pandapower.plotting.plotly import pf_res_plotly

#%% Functions
# Load a desired network and set each bus-load to zero
def load_network(generation):
    net = pp.from_excel('1055-1_0_4_grid.xlsx')
    if generation:
        net.load.p_mw = 0.0
        net.load.q_mvar = 0.0
    net.sgen.p_mw = 0.0
    net.sgen.q_mvar = 0.0
    return net


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

#%% Params and Loop

pv_size = 1e-4 # Size of PV systems in MW
ev_size = 1e-4 # Size of EVs in MW

max_voltage = 1.10 # Maximum bus voltage in p.u.
min_voltage = 0.90 # Minimum bus voltage in p.u.
max_line_loading = 1.0 # Maximum line loading in p.u.
max_transformer_loading = 1.0 # Maximum transformer loading in p.u.

max_voltages = []
min_voltages = []
loadings = []
load_capacities = []
gen_capacities = []

# Initialize the network with no PV or EV systems. For generation pass argument True, for no generation pass False
generation = False
net = load_network(generation)

# Exclude the external grid from the optimization
busses_to_test = net.bus.index[~net.bus.index.isin(net.ext_grid.bus)]
busses_to_exclude = net.bus.index[net.bus.index.isin(net.ext_grid.bus)]
net.bus.loc[busses_to_exclude, "vm_pu"] = 1.02
for bus in net.bus.index:
    pp.create_sgen(net, bus, p_mw=0.0, q_mvar=0.0)
    pp.create_load(net, bus, p_mw=0.0, q_mvar=0.0)
installed_pv = 0
installed_ev = 0

pp.runpp(net)
pp.plotting.pf_res_plotly(net, auto_open=False)

#%% Main Loop
while True:
    violated, reason, index = check_violations(net, max_voltage, min_voltage, max_line_loading, max_transformer_loading)
    if violated:
        print(f"Violation detected: {reason} at index {index}")
        break
    # Update all buses in the test set simultaneously for a uniform growth baseline
    net.sgen.loc[net.sgen.bus.isin(busses_to_test), "p_mw"] += pv_size
    #net.load.loc[net.load.bus.isin(busses_to_test), "p_mw"] += ev_size

    installed_pv += pv_size * len(busses_to_test)
    installed_ev += ev_size * len(busses_to_test)

    max_voltages.append(net.res_bus.vm_pu.max())
    min_voltages.append(net.res_bus.vm_pu.min())
    loadings.append(net.res_line.loading_percent.max())
    load_capacities.append(installed_pv + installed_ev)
    gen_capacities.append(installed_pv)

fig, ax1 = plt.subplots()
ax1.scatter(load_capacities, min_voltages, color='b', label='Max Voltage')
ax2 = ax1.twinx()
ax2.scatter(load_capacities, loadings, color='r', label='Max Loading')
plt.legend()
plt.title("Grid Load-Stress Evolution")
plt.show()

print("Installed PV capacity: ", installed_pv, " MW")
print("Installed EV capacity: ", installed_ev, " MW")
print("Trafo loading: ", net.res_trafo.loading_percent.max(), "%")
pp.plotting.pf_res_plotly(net, auto_open=False)
#pp.plotting.simple_plot(net, respect_switches=True, plot_sgens=True, plot_loads=True)
