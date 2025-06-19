import pandas as pd
import numpy as np
import networkx as nx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm

# Load data
df = pd.read_csv("data/flight.csv")
# # data = pd.DataFrame({
# #     'depaAirport': ['DOMU','AAHN','HZPW','VOXP','HZPW','ZJCG','FVJZ','OXSQ','AAHN','PNNF','KKME','FVJZ','XLHA','HIUP','EYWR','BBZB','PZYH','HZPW'],
# #     'arriAirport': ['HIUP','NLLA','VOXP','XCHB','NLLA','LFOL','HZPW','OKJK','PNNF','AAHN','HZPW','KDAX','DOMU','OETZ','OETZ','OXSQ','HEJY','MPYS']
# # })
#
# # Compute departure counts
# dep_counts = data['depaAirport'].value_counts().reset_index()
# dep_counts.columns = ['airport', 'count']
#
# # Compute flight pair counts
# pair_counts = data.groupby(['depaAirport', 'arriAirport']).size().reset_index(name='count')
#
# # Create graph and positions
# G = nx.DiGraph()
# for airport in dep_counts['airport']:
#     G.add_node(airport)
#
# for _, row in pair_counts.iterrows():
#     G.add_edge(row['depaAirport'], row['arriAirport'], weight=row['count'])
#
# pos_2d = nx.spring_layout(G, seed=42)
#
# # Prepare 3D plot
# fig = plt.figure(figsize=(12, 8))
# ax = fig.add_subplot(111, projection='3d')
#
# # Plot 3D bars for departure counts
# x_vals = []
# y_vals = []
# dz_vals = []
# for _, row in dep_counts.iterrows():
#     airport = row['airport']
#     count = row['count']
#     x, y = pos_2d[airport]
#     x_vals.append(x)
#     y_vals.append(y)
#     dz_vals.append(count)
#
# # Base positions and sizes
# x_vals = np.array(x_vals)
# y_vals = np.array(y_vals)
# z_vals = np.zeros_like(x_vals)
# dx = dy = 0.05
#
# ax.bar3d(x_vals, y_vals, z_vals, dx, dy, dz_vals, alpha=0.7)
#
# # Plot arcs for flight pairs
# max_count = pair_counts['count'].max()
# norm = plt.Normalize(0, max_count)
# cmap = cm.viridis
#
# for _, row in pair_counts.iterrows():
#     src = row['depaAirport']
#     dst = row['arriAirport']
#     count = row['count']
#     x1, y1 = pos_2d[src]
#     x2, y2 = pos_2d[dst]
#
#     # Parametric curve
#     t = np.linspace(0, 1, 100)
#     x_curve = x1 + (x2 - x1) * t
#     y_curve = y1 + (y2 - y1) * t
#     z_curve = np.sin(np.pi * t) * (max(dz_vals) * 0.7)  # elevate arc
#
#     color = cmap(norm(count))
#     ax.plot(x_curve, y_curve, z_curve, linewidth=2, color=color)
#
# # Labels and colorbar
# ax.set_xlabel('X')
# ax.set_ylabel('Y')
# ax.set_zlabel('Departure Flight Count')
# mappable = cm.ScalarMappable(norm=norm, cmap=cmap)
# mappable.set_array([])
# cb = plt.colorbar(mappable, ax=ax, pad=0.1)
# cb.set_label('Flights from A to B')
#
# plt.title('3D Departure Counts and Flight Curves')
# plt.show()
# import pandas as pd
# import networkx as nx
# import matplotlib.pyplot as plt

# Sample data
# df = pd.DataFrame({
#     'depaAirport': ['DOMU','AAHN','HZPW','VOXP','HZPW','ZJCG','FVJZ','OXSQ','AAHN','PNNF','KKME','FVJZ','XLHA','HIUP','EYWR','BBZB','PZYH','HZPW'],
#     'arriAirport': ['HIUP','NLLA','VOXP','XCHB','NLLA','LFOL','HZPW','OKJK','PNNF','AAHN','HZPW','KDAX','DOMU','OETZ','OETZ','OXSQ','HEJY','MPYS']
# })

# Identify all airports

# Compute counts
dep_counts = df['depaAirport'].value_counts().to_dict()
pair_counts = df.groupby(['depaAirport', 'arriAirport']).size().reset_index(name='count')

# Build directed graph
G = nx.DiGraph()
airports = set(df['depaAirport']).union(df['arriAirport'])
for airport in airports:
    G.add_node(airport, departures=dep_counts.get(airport, 0))
for _, row in pair_counts.iterrows():
    G.add_edge(row['depaAirport'], row['arriAirport'], weight=row['count'])

# Layout
pos = nx.spring_layout(G, seed=42)

# Normalizations
departures = [G.nodes[n]['departures'] for n in G.nodes()]
norm_nodes = plt.Normalize(min(departures), max(departures))
edges = list(G.edges())
weights = [G[u][v]['weight'] for u, v in edges]
norm_edges = plt.Normalize(min(weights), max(weights))

fig, ax = plt.subplots(figsize=(10, 8))

# Draw nodes
nodes = nx.draw_networkx_nodes(
    G, pos, ax=ax,
    node_size=[100 + 200 * norm_nodes(G.nodes[n]['departures']) for n in G.nodes()],
    node_color=departures,
    cmap=plt.cm.OrRd,
    vmin=min(departures),
    vmax=max(departures)
)
nx.draw_networkx_labels(G, pos, ax=ax, font_size=8)

# Draw curved directed edges
for u, v in G.edges():
    rad = 0.2 if G.has_edge(v, u) and u < v else -0.2 if G.has_edge(v, u) else 0.0
    nx.draw_networkx_edges(
        G, pos, ax=ax,
        edgelist=[(u, v)],
        arrowstyle='-|>',
        arrowsize=12,
        connectionstyle=f'arc3,rad={rad}',
        edge_color=[G[u][v]['weight']],
        edge_cmap=plt.cm.Blues,
        edge_vmin=min(weights),
        edge_vmax=max(weights),
        width=2,
        alpha=0.8
    )

# Colorbars
cbar_nodes = fig.colorbar(nodes, ax=ax, pad=0.02)
cbar_nodes.set_label('Departures per Airport')
sm_edges = plt.cm.ScalarMappable(cmap=plt.cm.Blues, norm=norm_edges)
sm_edges.set_array([])
cbar_edges = fig.colorbar(sm_edges, ax=ax, pad=0.02, fraction=0.046)
cbar_edges.set_label('Flights on Route')

ax.set_title('Directed Flight Network with Curved Edges')
ax.axis('off')
plt.tight_layout()
fig.savefig('flight_network.png', dpi=300, bbox_inches='tight')
# plt.show()