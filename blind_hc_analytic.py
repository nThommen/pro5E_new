import pandas as pd
import pandapower as pp, pandapower.topology as top, pandapower.networks as pn
import simbench as sb
import matplotlib.pyplot as plt
import seaborn as sns

from pandapower.plotting.plotly import pf_res_plotly

# Load a desired network (simbench for now)
def load_network():
    net = pn.create_kerber_dorfnetz()
    return net

def check_violations(net, max_voltage, max_line_loading, max_transformer_loading):
    pp.runpp(net)
    if net.res_line.loading_percent.max() > max_line_loading * 100:
        return (True, "Line Overloading")
    elif net.res_trafo.loading_percent.max() > max_transformer_loading * 100:
        return (True, "Transformer Overloading")
    elif net.res_bus.vm_pu.max() > max_voltage:
        return (True, "Voltage Violation")
    else:        return (False, None)

pv_size = 0.035 # Size of PV systems in MW
ev_size = 0.01 # Size of EVs in MW
hp_size = 0.01 # Size of heat pumps in MW

max_voltage = 1.03 # Maximum bus voltage in p.u.
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

iterations = 1

for i in range(iterations):
    violated, reason = check_violations(net, max_voltage, max_line_loading, max_transformer_loading)
    if violated:
        print("Violation detected: ", reason)
        break
    
    for i in range(net.bus.index.min(), net.bus.index.max() + 1):
        pp.create_load(net, i, p_mw=ev_size, q_mvar=0, name="EV_" + str(i))
        installed_ev += ev_size

    for i in range(net.bus.index.min(), net.bus.index.max() + 1):
        pp.create_sgen(net, i, p_mw=pv_size, q_mvar=0, name="PV_" + str(i))
        installed_pv += pv_size

print("Installed PV capacity: ", installed_pv, " MW")
print("Installed EV capacity: ", installed_ev, " MW")
pf_res_plotly(net)