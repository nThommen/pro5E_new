#%% Imports
import pandas as pd
import pandapower as pp
import matplotlib.pyplot as plt
import seaborn as sns

from pandapower.plotting.plotly import pf_res_plotly
from numpy.random import default_rng

#%% Functions
# Load a desired network (simbench for now)
def load_network():
    net = pp.from_excel('1055-1_0_4_grid.xlsx')
    return net

# Maximum number of PV systems at end of planning horizon should be 80% of the number of load points in the network
def get_pv_ev_number(net, factor):
    buses = 0
    for i in net.bus.index:
        buses += 1
    print("Number of buses: ", buses)
    number = int(buses * factor)
    print("Maximum number of PV or EV systems: ", number)
    return number

# Create array reflecting the number of PV systems in each year of the planning horizon
def get_pv_array(iterations, pv_number):
    pv_array = []
    for i in range(iterations):
        pv_array.append(int(pv_number / iterations * (i + 1)))
    print("PV array: ", pv_array)
    return pv_array

# Check for network violations and return the number of violations for each year of the planning horizon
def check_violations(net, max_voltage, max_line_loading, max_transformer_loading):
    pp.runpp(net)
    if net.res_line.loading_percent.max() > max_line_loading * 100:
        return (True, "Line Overloading")
    elif net.res_trafo.loading_percent.max() > max_transformer_loading * 100:
        return (True, "Transformer Overloading")
    elif net.res_bus.vm_pu.max() > max_voltage:
        return (True, "Voltage Violation")
    else:        return (False, None)


#%% Params
# Set the boundary conditions for the optimization problem and the max network parameters
rng = default_rng(seed=42)  # For reproducibility
max_voltage = 1.03 # Maximum bus voltage in p.u.
max_line_loading = 0.8 # Maximum line loading in p.u.
max_transformer_loading = 0.8 # Maximum transformer loading in p.u.
pv_size = 0.035 # Size of each PV system in MW
ev_size = 0.010 # Size of each EV in MW

# Number of iterations for the stochastic optimization
iterations = 5

# Set up pandas dataframe to store the results
results = pd.DataFrame(columns=['Iteration', 'Installed PV', 'Installed EV', 'Violation Type'])

#%% Execution and Plot
# Distribute the PV systems randomly in the network for each year of the planning horizon and run power flow calculations
for j in range(iterations):
        net = load_network()
        installed_pv = 0
        installed_ev = 0
        pv_ev_number = get_pv_ev_number(net, 0.8)
        available_buses = net.bus.index.to_numpy()
        random_buses = rng.choice(available_buses, size=pv_ev_number, replace=False)
        print("Which buses: ", random_buses)
        # Randomly distribute PV systems in the network without repeats in the same iteration
        for bus in random_buses:
            pp.create_sgen(net, bus, p_mw=pv_size, q_mvar=0.0)
            installed_pv += pv_size
            #pp.create_load(net, bus, p_mw=ev_size, q_mvar=0.0)
            #installed_ev += ev_size
            violation, reason = check_violations(net, max_voltage, max_line_loading, max_transformer_loading)
            if violation:
                print(f"Violation in iteration {j + 1} at bus {bus}: {reason}")
                results.loc[len(results)] = [j + 1, installed_pv, installed_ev, reason]
                pf_res_plotly(net)
                break        

results.to_csv('results.csv', index=False)
# Boxplot of installed PV capacity
plt.rc('xtick', labelsize=18)    # fontsize of the tick labels
plt.rc('ytick', labelsize=18)    # fontsize of the tick labels
plt.rc('legend', fontsize=18)    # fontsize of the tick labels
plt.rc('axes', labelsize=20)    # fontsize of the tick labels
plt.rcParams['font.size'] = 20
sns.set_style("whitegrid", {'axes.grid' : False})
fig, ax = plt.subplots(figsize=(10,5))
sns.boxplot(results['Installed PV'], width=.1, ax=ax, orient="v")
ax.set_ylabel("Installed PV Capacity [MW]")
plt.show()