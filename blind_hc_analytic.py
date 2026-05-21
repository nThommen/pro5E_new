#%% Imports
import pandas as pd
import pandapower as pp, pandapower.topology as top, pandapower.networks as pn
import matplotlib.pyplot as plt
import seaborn as sns
import kaleido

from pandapower.plotting.plotly import pf_res_plotly

#%% Functions
# Load a desired network (simbench for now)
def load_network():
    net = pp.from_excel('1055-1_0_4_grid.xlsx')
    return net

def check_violations(net, max_voltage, max_line_loading, max_transformer_loading):
    pp.runpp(net)
    if net.res_line.loading_percent.max() > max_line_loading * 100:
        return (True, "Line Overloading")
    elif net.res_trafo.loading_percent.max() > max_transformer_loading * 100:
        return (True, "Transformer Overloading")
    elif net.res_bus.vm_pu.max() > max_voltage:
        return (True, "Voltage Violation")
    elif net.res_bus.vm_pu.min() < min_voltage:
        return (True, "Voltage Violation")
    else:        return (False, None)

#%% Main

pv_size = 0.001 # Size of PV systems in MW
ev_size = 0.001 # Size of EVs in MW
hp_size = 0.001 # Size of heat pumps in MW

max_voltage = 1.03 # Maximum bus voltage in p.u.
min_voltage = 0.90
max_line_loading = 1.0 # Maximum line loading in p.u.
max_transformer_loading = 1.0 # Maximum transformer loading in p.u.

net = load_network()
lv_bus = net.trafo.at[0, 'lv_bus'] # Get the low voltage bus of the transformer
print("Low voltage bus: ", lv_bus)

n_of_branches = net.bus.zone.nunique() - 1 # Number of branches in the network
outgoing_lines = net.line[net.line['from_bus'] == lv_bus]
num_branches = len(outgoing_lines)
print("Number of branches: ", num_branches)

installed_pv = 0
installed_ev = 0
only_one_bus = [4]
pv_counter = 0

while True:
    violated, reason = check_violations(net, max_voltage, max_line_loading, max_transformer_loading)
    if violated:
        print("Violation detected: ", reason)
        break
    for bus in net.bus.index:
        #pp.create_sgen(net, bus, p_mw=pv_size, q_mvar=0.0)
        pp.create_load(net, bus, p_mw=hp_size, q_mvar=0.0)
        #installed_pv += pv_size
        installed_ev += hp_size


print("Installed PV capacity: ", installed_pv, " MW")
print("Installed EV capacity: ", installed_ev, " MW")
pp.plotting.pf_res_plotly(net)
#pp.plotting.simple_plot(net, respect_switches=True, plot_sgens=True, plot_loads=True)