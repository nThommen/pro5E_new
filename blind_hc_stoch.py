#%% Imports
import pandas as pd
import pandapower as pp
import matplotlib.pyplot as plt
import seaborn as sns

from numpy.random import default_rng

from blind_hc_analytic import generation


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

# Check for network violations and return the number of violations for each year of the planning horizon
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

    return False, None, None

def get_candidate_buses(net):
    return net.bus.index[~net.bus.index.isin(net.ext_grid.bus)]

def apply_penetration(net, selected_busses, penetration, pv_size, ev_size, generation, loadage):
    n_active = int(round(len(selected_busses) * penetration))
    active_busses = selected_busses[:n_active]

    installed_pv = 0
    installed_ev = 0

    for bus in active_busses:
        if generation:
            pp.create_sgen(net, bus, p_mw=pv_size, q_mvar=0.0)
            installed_pv += pv_size
        if loadage:
            pp.create_load(net, bus, p_mw=ev_size, q_mvar=0.0)
            installed_ev += ev_size

    return installed_pv, installed_ev

def test_penetration(
        selected_busses,
        penetration,
        pv_size,
        ev_size,
        generation,
        loadage,
        max_voltage,
        min_voltage,
        max_line_loading,
        max_transformer_loading,
):

    net = load_network(generation)

    installed_pv, installed_ev = apply_penetration(
        net,
        selected_busses,
        penetration,
        pv_size,
        ev_size,
        generation,
        loadage
    )

    violation, reason, location = check_violations(net,
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
        "location": location
    }

def find_hosting_capacity_bisection(
    selected_buses,
    pv_size,
    ev_size,
    generation,
    loadage,
    max_voltage,
    min_voltage,
    max_line_loading,
    max_transformer_loading,
    tolerance=0.01,
    max_iterations=20,
):
    low = 0.0
    high = 1.0
    records = []

    for search_step in range(max_iterations):
        mid = 0.5 * (low + high)

        result = test_penetration(
            selected_buses,
            mid,
            pv_size,
            ev_size,
            generation,
            loadage,
            max_voltage,
            min_voltage,
            max_line_loading,
            max_transformer_loading
        )

        result["search_step"] = search_step
        records.append(result)

        if result["violation"]:
            high = mid
        else:
            low = mid

        if high - low < tolerance:
            break

    return low, records


#%% Params and mc loop
generation = True
loadage = False

rng = default_rng(seed=42)

n_monte_carlo = 100
tolerance = 0.01

max_voltage = 1.10
min_voltage = 0.90
max_line_loading = 0.8
max_transformer_loading = 0.8

pv_size = 0.035
ev_size = 0.010

all_records = []
hosting_capacities = []

base_net = load_network(generation=generation)
candidate_buses = get_candidate_buses(base_net)

for mc_run in range(n_monte_carlo):
    selected_buses = rng.permutation(candidate_buses)

    hosting_capacity, records = find_hosting_capacity_bisection(
        selected_buses,
        pv_size,
        ev_size,
        generation,
        loadage,
        max_voltage,
        min_voltage,
        max_line_loading,
        max_transformer_loading,
        tolerance=tolerance,
        max_iterations=20,
    )

    hosting_capacities.append({
        "mc_run": mc_run,
        "hosting_capacity_penetration": hosting_capacity,
    })

    for record in records:
        record["mc_run"] = mc_run
        all_records.append(record)

results = pd.DataFrame(all_records)
hosting_capacity_results = pd.DataFrame(hosting_capacities)

results.to_csv("monte_carlo_violation_results.csv", index=False)
hosting_capacity_results.to_csv("monte_carlo_hosting_capacity.csv", index=False)

"""
#%% Params
# Set the boundary conditions for the optimization problem and the max network parameters
rng = default_rng(seed=42)  # For reproducibility
max_voltage = 1.10 # Maximum bus voltage in p.u.
min_voltage = 0.90
max_line_loading = 0.8 # Maximum line loading in p.u.
max_transformer_loading = 0.8 # Maximum transformer loading in p.u.
pv_size = 0.035 # Size of each PV system in MW
ev_size = 0.010 # Size of each EV in MW

# Number of iterations for the stochastic optimization
iterations = 5

# Set up pandas dataframe to store the results
results = pd.DataFrame(columns=['Iteration', 'Installed PV', 'Installed EV', 'Violation Type', 'Violation Location'])

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
            violation, reason, location = check_violations(net, max_voltage, min_voltage, max_line_loading, max_transformer_loading)
            if violation:
                print(f"Violation in iteration {j + 1} at bus {bus} at location {location}: {reason}")
                results.loc[len(results)] = [j + 1, installed_pv, installed_ev, reason, location]
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
plt.show()"""