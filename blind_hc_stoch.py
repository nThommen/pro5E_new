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
def load_network():
    #net = pn.kb_extrem_vorstadtnetz_1()
    #net = pn.create_kerber_landnetz_kabel_1()
    net = pn.create_kerber_dorfnetz()
    #net = pn.create_kerber_vorstadtnetz_kabel_1()
    net.bus['zone'] = net.bus['name'].str.split('_').str[-2]
    net.line['zone'] = net.line['name'].str.split('_').str[-2]
    net.trafo['zone'] = 'Trafostation'
    dist = top.calc_distance_to_bus(net, 1, respect_switches=True)
    dist.name = 'distance2ts'
    net.bus = net.bus.merge(dist.to_frame(), left_index=True, right_index=True, how='left')
    return net

def get_candidate_buses(net):
    candidate_buses = []
    for idx, row in net.bus.iterrows():
        if 'loadbus' in row['name']:
            candidate_buses.append(idx)
    return candidate_buses

def find_hosting_capacity_bisection(
    selected_buses,
    pv_size,
    ev_size,
    generation,
    max_voltage,
    min_voltage,
    max_line_loading,
    max_transformer_loading,
    tolerance,
    max_iterations,
):
    first_run = True
    low = 0.0
    high = 1.0
    records = []
    best_feasible_result = None

    for search_step in range(max_iterations):
        if first_run:
            penetration = 1.0 * (low + high)
            first_run = False
        else:
            penetration = 0.5 * (low + high)

        result = test_penetration(
            selected_buses,
            penetration,
            pv_size,
            ev_size,
            generation,
            max_voltage,
            min_voltage,
            max_line_loading,
            max_transformer_loading
        )

        result["search_step"] = search_step
        records.append(result)

        if result["violation"]:
            high = penetration
        else:
            low = penetration
            best_feasible_result = result

        if high - low <= tolerance:
            break

    if best_feasible_result is None:
        hosting_capacity = 0.0
    elif generation == True:
        hosting_capacity = best_feasible_result["installed_pv"]
    elif generation == False:
        hosting_capacity = best_feasible_result["installed_ev"]
    else:
        hosting_capacity = 0.0

    return hosting_capacity, records

def test_penetration(
        selected_busses,
        penetration,
        pv_size,
        ev_size,
        generation,
        max_voltage,
        min_voltage,
        max_line_loading,
        max_transformer_loading,
):

    net = load_network()

    installed_pv, installed_ev = apply_penetration(
        net,
        selected_busses,
        penetration,
        pv_size,
        ev_size,
        generation
    )

    violation, reason, location, value = check_violations(net,
        max_voltage,
        min_voltage,
        max_line_loading,
        max_transformer_loading
    )

    return {
        "penetration": penetration,
        "installed_ev": installed_ev,
        "installed_pv": installed_pv,
        "violation": violation,
        "reason": reason,
        "location": location,
        "value": value
    }

def apply_penetration(net, selected_busses, penetration, pv_size, ev_size, generation):
    n_active = int(round(len(selected_busses) * penetration))
    active_busses = selected_busses[:n_active]
    #Debugging snipped to verify bisection
    #print(f"Active buses: {active_busses}")

    installed_pv = 0
    installed_ev = 0

    for bus in active_busses:
        if generation:
            pp.create_sgen(net, bus, p_mw=pv_size, q_mvar=0.0)
            installed_pv += pv_size
        else:
            pp.create_load(net, bus, p_mw=ev_size, q_mvar=0.0)
            installed_ev += ev_size

    return installed_pv, installed_ev

def check_violations(net,
                     max_voltage,
                     min_voltage,
                     max_line_loading,
                     max_transformer_loading):
    try:
        pp.runpp(net)
    except:
        return True, "No Convergence", None, None

    if net.res_line.loading_percent.max() > max_line_loading * 100:
        return True, "Line Overloading", net.line.index[net.res_line.loading_percent.idxmax()], net.res_line.loading_percent.max()

    elif net.res_trafo.loading_percent.max() > max_transformer_loading * 100:
        return True, "Transformer Overloading", net.trafo.index[net.res_trafo.loading_percent.idxmax()], net.res_trafo.loading_percent.max()

    elif net.res_bus.vm_pu.max() > max_voltage:
        return True, "Voltage Violation", net.bus.index[net.res_bus.vm_pu.idxmax()], net.res_bus.vm_pu.max()

    elif net.res_bus.vm_pu.min() < min_voltage:
        return True, "Voltage Violation", net.bus.index[net.res_bus.vm_pu.idxmin()], net.res_bus.vm_pu.min()

    return False, None, None, None


#%% Params and mc loop

# Set mode of simulation (generation, or both... or none if you're feeling funny)
generation = False

rng = default_rng(seed=42)

# Limits for the network
max_voltage = 1.03 #Applicable for generation of pv panels
min_voltage = 0.90
max_line_loading = 1.0
max_transformer_loading = 1.0

# Size of the PV and EV systemy for each bus they're installed on
pv_size = 0.030   # 30kW PV - change back to 10kW later
ev_size = 0.011   # 11kW EV charger

all_records = []
hosting_capacities = []

base_net = load_network()
candidate_buses = get_candidate_buses(base_net)

n_monte_carlo = 100 # Number of Monte Carlo runs
tolerance = 1/len(candidate_buses) # Tolerance for bisection search depending on grid size - currently +-1 bus
max_iterations = 20 # Maximum number of iterations for bisection search

for mc_run in range(n_monte_carlo):
    selected_buses = rng.permutation(candidate_buses)
    print(f"MC Run {mc_run + 1} of {n_monte_carlo}")

    hosting_capacity, records = find_hosting_capacity_bisection(
        selected_buses,
        pv_size,
        ev_size,
        generation,
        max_voltage,
        min_voltage,
        max_line_loading,
        max_transformer_loading,
        tolerance=tolerance,
        max_iterations=max_iterations
    )

    hosting_capacities.append({
        "mc_run": mc_run,
        "hosting_capacity": hosting_capacity,
    })

    for record in records:
        record["mc_run"] = mc_run
        all_records.append(record)

results = pd.DataFrame(all_records)
hosting_capacity_results = pd.DataFrame(hosting_capacities)

results.to_csv("monte_carlo_violation_results.csv", index=False)
hosting_capacity_results.to_csv("monte_carlo_hosting_capacity.csv", index=False)


#%% Call analytic HC for comparison

from blind_hc_analytic import calculate_analytic_hc, step_size
PV_hc, EV_hc = calculate_analytic_hc(generation, step_size, max_voltage, min_voltage, max_line_loading, max_transformer_loading)

#%% Plot type of violation in cake diagram

x = results["reason"].value_counts()
labels = results["reason"].value_counts().index
if generation:
    colors = matplotlib.color_sequences['Set2']
else:
    colors = matplotlib.color_sequences['tab20']

fig, ax = plt.subplots()
ax.pie(x, labels=labels, autopct='%1.1f%%', colors=colors, startangle=90)
plt.title('Violation Distribution')
plt.savefig("violation_distr.png")
plt.show()

# Boxplot of hosting capacities
# Get previously calculated hosting capacity from other script
if generation:
    analytic_hc = np.round(PV_hc, decimals=3) # Example value from blind_hc_analytic.py
    color = ""
else:
    analytic_hc = np.round(EV_hc, decimals=3)
    color = "blue"
plt.figure(figsize=(5, 10))
sns.boxplot(data=hosting_capacity_results, y="hosting_capacity")
plt.axhline(y=analytic_hc, color='r', linestyle='--', label=f'Deterministic HC ({analytic_hc} MW)')
#lim only needed for comparing iteration numbers, comment out for other sims
plt.ylim(0.0, 0.1)
plt.ylabel("Hosting Capacity [MW]")
plt.title("Hosting Capacity Distribution")
plt.legend()
plt.grid(True)
plt.savefig("hc_distr.png")
plt.show()
