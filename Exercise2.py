# %%
# Import necessary libraries
import os, copy, numpy as np, pandas as pd, matplotlib.pyplot as plt, geopandas as gpd, networkx as nx, contextily as cx, warnings #, pygraphviz
# import PandaPower-Packages
import pandapower as pp, pandapower.networks as pn, pandapower.topology as top
from pandapower.plotting.plotly import pf_res_plotly, simple_plotly
warnings.filterwarnings("ignore")
parent_path = os.path.abspath('../.')

# %%
# Create an example network based on the Kerber-Dorfnetz
net = pn.create_kerber_dorfnetz()
# net = pn.create_kerber_landnetz_freileitung_2()

net.bus['zone'] = net.bus['name'].str.split('_').str[-2]
net.line['zone'] = net.line['name'].str.split('_').str[-2]
net.trafo['zone'] = 'Trafostation'
dist = top.calc_distance_to_bus(net, 1, respect_switches=True)
dist.name = 'distance2ts'
net.bus = net.bus.merge(dist.to_frame(), left_index=True, right_index=True, how='left')
# Erstellen des Plot
ax = pp.plotting.simple_plot(net, plot_sgens=True, plot_loads=True, ext_grid_size=1, bus_size=0.5, load_size=1, sgen_size=1)
# simple_plotly(net)#, plot_sgens=True, plot_loads=True, ext_grid_size=1, bus_size=0.5, load_size=1, sgen_size=1)

# %%
'''EXERCISE PARAMETERS'''
# Exersecise 1: Basics: no load, no generation
net.load.scaling = 0
net.sgen.scaling = 0

# Exersecise 2.1: Basics: connect one load with 100 kW the last bus of feeder 3

#pp.create_load(net, bus=net.bus[net.bus['zone'] == '3'].index[-1], p_mw=0.1, q_mvar=0, name='Load_100kW')
#pp.create_load(net, bus=69, p_mw=0.1, q_mvar=0, name='Load_100kW')


# Exersecise 2.2: Basics: connect one load with 100 kW the first bus of feeder 3

#pp.create_load(net, bus=39, p_mw=0.1, q_mvar=0, name='Load_100kW')


# Exersecise 2.3: Basics: connect a PV with 100 kW the last bus of feeder 3
#pp.create_sgen(net, bus=69, p_mw=0.1, q_mvar=0, name='PV_100kW')

# Exersecise 2.4: Basics: connect a PV with 100 kW the last bus of feeder 3

"""for idx, row in net.bus.iterrows():
    if row['zone'] == '3' and "loadbus" in row['name']:
        pp.create_sgen(net, bus=idx, p_mw=0.01, q_mvar=0, name='PV_10kW')
    if row['zone'] == '1' and "loadbus" in row['name']:
        pp.create_load(net, bus=idx, p_mw=0.01, q_mvar=0, name='Load_10kW')
"""
# Exersecise 2.5: Basics: connect one load with 100 kW the first bus of feeder 3
# B)

# C)
#pp.create_sgen(net, bus=69, p_mw=0.1, q_mvar=-0.1, name='PV_100kW')

#TAG-Exercise
pp.create_sgen(net, bus=93, p_mw=0.035, q_mvar=0, name='PV_35kW')
pp.create_sgen(net, bus=93, p_mw=0.035, q_mvar=0, name='PV_35kW_2')

# %%
'''Running the power flow calculation and plotting the results'''
pp.runpp(net)
# Print results
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
pp.plotting.plotly.pf_res_plotly(net)

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
# %%
