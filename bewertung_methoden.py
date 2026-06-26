import numpy as np
import matplotlib.pyplot as plt
import os

# Disclaimer: Script AI-generated

# Data from the table
methods = [
    "Deterministic",
    "Time series",
    "Stochastic",
    "Optimization",
    "Streamlined",
    "Risk-based",
    "Generalized deterministic"
]

# Criteria: Data availability, Computation time, Accuracy
# 4 = Best/High, 1 = Worst/Low
data = np.array([
    [4, 4, 2], # Deterministic
    [1, 1, 4], # Time series
    [4, 2, 3], # Stochastic
    [2, 3, 3], # Optimization
    [4, 3, 2], # Streamlined
    [4, 2, 3], # Risk-based
    [4, 4, 1], # Generalized deterministic
])

def is_pareto_efficient(costs):
    """
    Find the pareto-efficient points
    :param costs: An (n_points, n_costs) array
    :return: A (n_points, ) boolean array indicating whether each point is Pareto efficient
    """
    is_efficient = np.ones(costs.shape[0], dtype=bool)
    for i, c in enumerate(costs):
        if is_efficient[i]:
            # Keep points that are better in at least one dimension or equal
            # costs are 'better' if they are higher here
            is_efficient[is_efficient] = np.any(costs[is_efficient] > c, axis=1) | np.all(costs[is_efficient] == c, axis=1)
            # This logic is for minimization. For maximization:
            # A point is dominated if there exists another point that is better or equal in all dimensions 
            # and strictly better in at least one.
    
    # Simple Pareto for maximization
    efficient = np.ones(costs.shape[0], dtype=bool)
    for i, c in enumerate(costs):
        for j, other in enumerate(costs):
            if i == j:
                continue
            # other dominates c if other >= c in all and other > c in at least one
            if np.all(other >= c) and np.any(other > c):
                efficient[i] = False
                break
    return efficient

# Determination of Pareto-efficient methods
is_efficient = is_pareto_efficient(data)

# Check: "best in at least one category AND not beaten out by any others in the other ones"
# This corresponds to Pareto efficiency for points that reach at least one maximum.
max_vals = np.max(data, axis=0)
best_in_any = np.any(data == max_vals, axis=1)
highlight = is_efficient & best_in_any

fig = plt.figure(figsize=(12, 8))
ax = fig.add_subplot(111, projection='3d')

# Axis labels
ax.set_xlabel('Data Availability')
ax.set_ylabel('Computation Time')
ax.set_zlabel('Accuracy')

# Plotting the points
# Grouping methods by position to avoid overlapping labels
unique_positions = {}
for i, pos in enumerate(data):
    pos_tuple = tuple(pos)
    if pos_tuple not in unique_positions:
        unique_positions[pos_tuple] = []
    unique_positions[pos_tuple].append(i)

for pos_tuple, indices in unique_positions.items():
    is_any_highlight = any(highlight[i] for i in indices)
    
    if is_any_highlight:
        color = 'seagreen'
        marker = 'o'
        size = 100
    else:
        color = 'darkred'
        marker = 'x'
        size = 50
    
    pos = np.array(pos_tuple)
    ax.scatter(pos[0], pos[1], pos[2], c=color, marker=marker, s=size)
    
    # Combined label for methods at the same position
    combined_label = ", ".join([methods[i] for i in indices])
    ax.text(pos[0], pos[1], pos[2], f" {combined_label}", size=9)

# Create legend manually
from matplotlib.lines import Line2D
legend_elements = [
    Line2D([0], [0], marker='o', color='w', label='Highlighted (qualitative optimum & best value)',
           markerfacecolor='seagreen', markersize=10),
    Line2D([0], [0], marker='x', color='w', label='Other methods',
           markerfacecolor='darkred', markersize=10, markeredgecolor='darkred')
]
ax.legend(handles=legend_elements, loc='best')
ax.set_xticks([1, 2, 3, 4])
ax.set_yticks([1, 2, 3, 4])
ax.set_zticks([1, 2, 3, 4])

plt.tight_layout()

# Ensure output directory exists
if not os.path.exists('Plots'):
    os.makedirs('Plots')

output_path = 'Plots/methoden_bewertung_3d.png'
plt.savefig(output_path)

print(f"Plot saved at: {output_path}")

# Display highlighted methods
print("\nHighlighted methods:")
for i, h in enumerate(highlight):
    if h:
        print(f"- {methods[i]} {data[i]}")
