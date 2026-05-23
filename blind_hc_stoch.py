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



def get_candidate_buses(net):
    return net.bus.index[~net.bus.index.isin(net.ext_grid.bus)]

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
    tolerance,
    max_iterations,
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

        if high - low <= tolerance:
            break

    return low, records

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

def check_violations(net,
                     max_voltage,
                     min_voltage,
                     max_line_loading,
                     max_transformer_loading):
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


#%% Params and mc loop

# Set mode of simulation (generation, loadage, or both... or none if you're feeling funny)
generation = True
loadage = False

rng = default_rng(seed=42)

n_monte_carlo = 100 # Number of Monte Carlo runs
tolerance = 0.01 # Tolerance for bisection search
max_iterations = 20 # Maximum number of iterations for bisection search

# Limits for the network
max_voltage = 1.10
min_voltage = 0.90
max_line_loading = 0.8
max_transformer_loading = 0.8

# Size of the PV and EV systemy for each bus they're installed on
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
        max_iterations=max_iterations
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

# Plot penetration on x-axis vs