#%% Imports
import pandas as pd
import pandapower as pp, pandapower.topology as top, pandapower.networks as pn
import matplotlib.pyplot as plt
import seaborn as sns
import kaleido

from pandapower.plotting.plotly import pf_res_plotly

#%% Functions
# Load a desired network and set each bus-load to zero
def load_network():
    #net = pn.create_kerber_landnetz_kabel_2()
    #net = pn.create_kerber_vorstadtnetz_kabel_1()
    net = pn.kb_extrem_vorstadtnetz_1()
    #net = pn.kb_extrem_dorfnetz()
    net.bus['zone'] = net.bus['name'].str.split('_').str[-2]
    net.line['zone'] = net.line['name'].str.split('_').str[-2]
    net.trafo['zone'] = 'Trafostation'
    dist = top.calc_distance_to_bus(net, 1, respect_switches=True)
    dist.name = 'distance2ts'
    net.bus = net.bus.merge(dist.to_frame(), left_index=True, right_index=True, how='left')
    busses_to_test = []
    for idx, row in net.bus.iterrows():
        if 'loadbus' in row['name']:
            busses_to_test.append(idx)
    return net, busses_to_test


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

max_voltage = 1.03 # Maximum bus voltage in p.u.
min_voltage = 0.90 # Minimum bus voltage in p.u.
max_line_loading = 1.0 # Maximum line loading in p.u.
max_transformer_loading = 1.0 # Maximum transformer loading in p.u.

# Initialize the network with no PV or EV systems. For generation pass argument True, for no generation pass False
generation = True
net, busses_to_test = load_network()

for bus in busses_to_test:
    if generation:
        pp.create_sgen(net, bus, p_mw=0.0, q_mvar=0.0)
    else:
        pp.create_load(net, bus, p_mw=0.0, q_mvar=0.0)

installed_pv = 0
installed_ev = 0

#pp.runpp(net)

#%% Main Loop
while True:
    violated, reason, index = check_violations(net, max_voltage, min_voltage, max_line_loading, max_transformer_loading)
    if violated:
        print(f"Violation detected: {reason} at index {index}")
        break
    # Update all buses in the test set simultaneously for a uniform growth baseline
    if generation:
        net.sgen.loc[net.sgen.bus.isin(busses_to_test), "p_mw"] += pv_size
        installed_pv += pv_size * len(busses_to_test)
    else:
        net.load.loc[net.load.bus.isin(busses_to_test), "p_mw"] += ev_size
        installed_ev += ev_size * len(busses_to_test)

pp.runpp(net)
pp.plotting.pf_res_plotly(net, auto_open=False)

print("Installed PV: ", installed_pv-len(busses_to_test)*pv_size, "MW")
print("Installed EV: ", installed_ev-len(busses_to_test)*ev_size, "MW")

print("Bus Results:")
bus_results = net.bus[['name', 'zone', 'distance2ts']].merge(net.res_bus[['vm_pu', 'p_mw', 'q_mvar']], how='left', left_index=True, right_index=True)
critical_bus_results = bus_results[(bus_results['vm_pu'] < 0.97) | (bus_results['vm_pu'] > 1.03)]
if critical_bus_results.empty:
    critical_bus_results = 'no bus voltage violation'
print(critical_bus_results)

print("\nLine Results:")
line_results = net.line[['name', 'zone']].merge(net.res_line[['p_from_mw', 'i_ka', 'loading_percent']], how='left', left_index=True, right_index=True)
critical_line_results = line_results[line_results['loading_percent'] > 80]
if critical_line_results.empty:
    critical_line_results = 'no line overload'
print(critical_line_results)

print("\nTransformers Results:")
trafo_results = net.trafo[['name', 'zone']].merge(net.res_trafo[['p_hv_mw', 'p_lv_mw', 'loading_percent']], how='left', left_index=True, right_index=True)
element_results = pd.concat([trafo_results, line_results], axis=0).reset_index(drop=True)
critical_trafo_results = trafo_results[trafo_results['loading_percent'] > 80]
if critical_trafo_results.empty:
    critical_trafo_results = 'no transformer overload'
print(critical_trafo_results)

# Ergebnisplot anzeigen
pp.plotting.pf_res_plotly(net)
pp.plotting.simple_plot(net, plot_sgens=True, plot_loads=True, ext_grid_size=1, bus_size=0.5, load_size=1,
                                 sgen_size=1)
"""
# Erstellen einer Farbpalette für die Zonen
colors_buses = {'Trafostation':'grey', 'main':'grey',
          '1':'darkred', '2':'green', '3':'darkorange',
          '4':'darkviolet', '5':'steelblue', '6': 'aqua'}
colors_lines = dict(list(colors_buses.items())[-6:])
# Plotten der Daten
fig, ax = plt.subplots(1, 2, figsize=(12, 6))
ax[0].axhline(y=0.97, color='r', linestyle='--')#, label='Voltage Limit')
ax[0].axhline(y=1.03, color='r', linestyle='--')#, label='Voltage Limit')
for zone in bus_results['zone'].unique():
    zone_data = bus_results[bus_results['zone'] == zone]
    ax[0].scatter(zone_data['distance2ts'], zone_data['vm_pu'], c=colors_buses[zone], label=zone)

# Titel und Achsenbeschriftungen hinzufügen
ax[0].set_xlabel('Distance to substation')
ax[0].set_ylabel('Voltage Magnitude (pu)')
ax[0].set_ylim(0.9, 1.1)
# Legende hinzufügen
ax[0].legend()

ax[1].axhline(y=80, color='r', linestyle='--')#, label='Loading Limit')
for zone in element_results['zone'].unique():
    zone_data = element_results[element_results['zone'] == zone]
    ax[1].bar(zone_data.name, zone_data['loading_percent'], color=colors_buses[zone], label=zone)
#  Horizontale Gitterlinien hinzufügen
ax[1].grid(True, which='both', axis='y', linestyle='--', linewidth=0.2)
# Achsen-Beschriftungen ausblenden
ax[1].tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=False)
ax[1].set_ylabel('Loading (%)')
ax[1].legend()
# Plot anzeigen
plt.show()
"""