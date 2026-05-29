# %%
# Import necessary libraries
import os, copy, numpy as np, pandas as pd, matplotlib.pyplot as plt, geopandas as gpd, networkx as nx, contextily as cx, warnings #, pygraphviz
# import PandaPower-Packages
import pandapower as pp, pandapower.networks as pn, pandapower.topology as top, pandapower.control as control
from pandapower.plotting.plotly import pf_res_plotly, simple_plotly
warnings.filterwarnings("ignore")
parent_path = os.path.abspath('../.')

# %%
# Create an example network based on the Kerber-Dorfnetz
net = pn.create_kerber_dorfnetz()

# setting parameters of ext_grid
net.ext_grid['vm_pu'], net.ext_grid['va_degree'], net.ext_grid['s_sc_max_mva'] = 1.02, 150, 10000
line_data = {"c_nf_per_km": 155, "r_ohm_per_km": 0.145, "x_ohm_per_km": 0.076, "max_i_ka": 0.339, "type": "cs", "q_mm2": 240}
pp.create_std_type(net, line_data, "GKN 240/150 ALse", element='line')
# setting zones
net.bus['zone'] = net.bus['name'].str.split('_').str[-2]
net.line['zone'] = net.line['name'].str.split('_').str[-2]
net.trafo['zone'] = 'Trafostation'
dist = top.calc_distance_to_bus(net, 1, respect_switches=True)
dist.name = 'distance2ts'
net.bus = net.bus.merge(dist.to_frame(), left_index=True, right_index=True, how='left')
net.load.scaling = 0.3
active_controller = False

# %%
'''insert grid solutions here'''
# Solution 1: second line to the has


# Solution 3: installing a rONT


'''-------------------------'''
# %%
# Erstellen des Plot
# ax = pp.plotting.simple_plot(net, plot_sgens=True, plot_loads=True, ext_grid_size=1, bus_size=0.5, load_size=1, sgen_size=1)
simple_plotly(net)#, plot_sgens=True, plot_loads=True, ext_grid_size=1, bus_size=0.5, load_size=1, sgen_size=1)

# first power flow calculation for getting the voltage magnitude at the PV bus
pp.runpp(net)
print('Trafostufen-Position: ', net.trafo.tap_pos[0])
vm_pu_original = net.res_bus.vm_pu.copy()

# %%
'''EXERCISE PARAMETERS'''
# Exersecise 3: Basics: connect a PV with 70 kW at the last load_bus of feeder 4
pv_bus_id = 93


''' -------------------'''
# %%
''' Insert here solutions at the device level'''
# Solution 4: peak shaving to 70%

# Solution 5: reactive power control


'''--------------------'''

# %%
'''Running the power flow calculation and plotting the results'''
pp.runpp(net, run_control=active_controller)
# Print results
print("Bus Results:")
bus_results = net.bus[['name', 'zone', 'distance2ts']].merge(net.res_bus[['vm_pu', 'p_mw', 'q_mvar']], how='left', left_index=True, right_index=True)
critical_bus_results = bus_results[(bus_results['vm_pu'] < 0.95) | (bus_results['vm_pu'] > 1.05)]
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

vm_pu_wo_pv = vm_pu_original[pv_bus_id]
vm_pu_new = net.res_bus.vm_pu.copy()
vm_pu_pv = vm_pu_new[pv_bus_id]
dach_cz_delta_v = vm_pu_pv - vm_pu_wo_pv
print('Spannungshub nach DACH-CZ: Δu =', round(dach_cz_delta_v *100, 2), ' %')
print('Trafostufen-Position: ', net.trafo.tap_pos[0])
# Ergebnisplot anzeigen
pp.plotting.plotly.pf_res_plotly(net)

# Erstellen einer Farbpalette für die Zonen
colors_buses = {'Trafostation':'grey', 'main':'grey', 
          '1':'darkred', '2':'green', '3':'darkorange', 
          '4':'darkviolet', '5':'steelblue', '6': 'aqua'}#, '7': 'khaki'
colors_lines = dict(list(colors_buses.items())[-6:])
# Plotten der Daten
fig, ax = plt.subplots(1, 2, figsize=(12, 6))
ax[0].plot(net.bus.distance2ts[pv_bus_id], vm_pu_wo_pv, color='gray', marker='o')
# Spannungsgrenzen
ax[0].fill_between(np.linspace(0, round(net.bus.distance2ts.max(), 51)), 1.05, 1.1, color = 'sandybrown', alpha =0.4)
ax[0].fill_between(np.linspace(0, round(net.bus.distance2ts.max(), 51)), 0.9, 0.95, color = 'sandybrown', alpha =0.4)
# Zeichnen des Pfeils
ax[0].annotate('',  # Leerer Text, da wir nur den Pfeil benötigen
    xy=(net.bus.distance2ts[pv_bus_id], vm_pu_pv),  # Position der Pfeilspitze
    xytext=(net.bus.distance2ts[pv_bus_id], vm_pu_wo_pv),  # Position des Startpunkts
    arrowprops=dict(arrowstyle='->', color='gray', linestyle='--'))  # Pfeilstil und Farbe)
ax[0].annotate(f'Δu = {round(dach_cz_delta_v *100, 2)} %',  # Text der Beschriftung
    xy=(net.bus.distance2ts[pv_bus_id], (vm_pu_pv + vm_pu_wo_pv) / 2),  # Position des Textes
    xytext=(net.bus.distance2ts[pv_bus_id] + 0.01, (vm_pu_pv + vm_pu_wo_pv) / 2),  # Text leicht nach rechts verschieben
    rotation='vertical', va='center',  ha='left', color='gray')  # # Text parallel zum Pfeil (senkrecht), Vertikale Ausrichtung des Textes, Horizontale Ausrichtung des Textes, Textfarbe

# ax[0].axhline(y=1.03, color='r', linestyle='--')#, label='Voltage Limit')
for zone in bus_results['zone'].unique():
    zone_data = bus_results[bus_results['zone'] == zone]
    ax[0].scatter(zone_data['distance2ts'], zone_data['vm_pu'], c=colors_buses[zone], label=zone)

# Titel und Achsenbeschriftungen hinzufügen
ax[0].set_xlabel('Distance to substation')
ax[0].set_ylabel('Voltage Magnitude (pu)')
ax[0].set_ylim(0.9, 1.1)
# Legende hinzufügen
ax[0].legend( loc = 'lower left')

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
