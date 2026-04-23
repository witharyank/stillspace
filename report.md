# TITLE PAGE

**PROJECT REPORT**
**STILLSPACE: ADAPTIVE MULTI-CRITERIA URBAN ROUTING SYSTEM**

Submitted in partial fulfillment of the requirements for the course
**Design and Analysis of Algorithms (DAA)**

Submitted By:
[Student Name]
[Roll Number / Scholar ID]

Under the Guidance of:
[Professor/Guide Name]
[Department Name]

[Institution Name]
[Academic Year]

---

# CERTIFICATE & DECLARATION

**CERTIFICATE**
This is to certify that the project report entitled "STILLSPACE: ADAPTIVE MULTI-CRITERIA URBAN ROUTING SYSTEM" submitted by [Student Name] is a bonafide record of the algorithmic implementation work carried out under my supervision during the academic year [Year] for the Design and Analysis of Algorithms course.

**DECLARATION**
I hereby declare that this project report, based on the implementation of advanced graph algorithms and state-space search architectures, is my original work and has not been submitted for the award of any other degree or diploma. 

---

# ACKNOWLEDGEMENT

I would like to express my sincere gratitude to my project guide, [Guide Name], for their invaluable algorithmic insights and constant motivation. I also extend my thanks to the Department of Computer Science for providing the resources to analyze and implement complex multi-modal graph search heuristics on real-world spatial models.

---

# ABSTRACT

Traditional routing applications calculate the mathematical shortest path using standard Edge-Weight algorithms, explicitly optimizing for minimal distance or Estimated Time of Arrival (ETA). However, human urban mobility requires subjective optimization metrics such as safety, calmness, environmental factors, and accessibility. 

The "StillSpace" project introduces a highly adaptable, multi-criteria route optimization system constructed on real-world OpenStreetMap graph topologies. By implementing a **Modified State-Space Dijkstra's Algorithm**, we compute paths that actively penalize high-traffic intersections, steep turn angles, dynamic danger zones (Geo-fenced polygons), and harsh weather conditions. This report breaks down the algorithmic design, complexity optimization using Min-Heaps (`PriorityQueue`), data structure alignment (Adjacency Matrix representations via MultiDiGraphs), and empirical Time/Space complexity comparisons against traditional routing matrices.

---

# TABLE OF CONTENTS

1. Introduction
2. Problem Statement
3. Objectives
4. Existing System vs Proposed System
5. Technologies Used
6. System Architecture
7. Modules Description
8. Algorithms Used
9. Flowcharts
10. Pseudocode
11. Time & Space Complexity Analysis
12. Screenshots
13. Advantages
14. Limitations
15. Future Scope
16. Conclusion
17. References

---

# 1. INTRODUCTION

Urban navigation is inherently represented as a Mathematical Graph Problem where geographic coordinates map to vertices ($V$), and physical roads map to edges ($E$). StillSpace transforms a standard mapping application into a heavily parameterized heuristic weighting engine. Instead of a uniform distance weight metric, StillSpace applies contextual factors mathematically mapped directly to continuous traversal equations (e.g., Dog Walking Mode, Accessibility Mode, Safe Mode).

# 2. PROBLEM STATEMENT

To design a highly efficient algorithmic engine capable of multi-variate single-source shortest path routing across dense spatial map grids. Standard search models are static; the engine must dynamically evaluate spatial-temporal constraints without incurring extreme $O(V^3)$ processing complexities, ensuring $O(E \log V)$ viability over large city chunks.

# 3. OBJECTIVES

- To implement efficient Graph theory traversal algorithms representing spatial nodes constraint variables.
- To execute dynamic edge-weight injection based on OpenStreetMap metadata tags (`highway`, `lit`, `surface`).
- To integrate a modified **State-Space Traversal System** that considers the `previous_edge` to compute angle-based turn penalties accurately.
- To manage Time Complexity scaling through optimized Priority Queues.

# 4. EXISTING SYSTEM VS PROPOSED SYSTEM

**Existing Systems:**
Current routing implementations (like standard Google Maps iterations) rely heavily on $A^*$ or Contraction Hierarchies optimizing exclusively for the lowest temporal delay (ETA constraints). They largely ignore environmental anxiety or accessibility constraints unless utilizing massive proprietary traffic vectors.

**Proposed System (StillSpace):**
StillSpace manipulates the base Dijkstra frontier by overlaying dynamic multipliers. If "Safe Mode" is engaged, lines intersecting geofenced unsafe polygons receive intense mathematical deterrence (`weight *= 100.0`). The user dictates the constraints; the continuous-time algorithm calculates the safest or calmest route, not just the fastest.

# 5. TECHNOLOGIES USED

- **Algorithm & Core Logic**: Python 3, NetworkX (Graph mathematics)
- **Spatial Topology Engine**: OSMnx (OpenStreetMap API abstraction)
- **Polygonal Intersections**: Shapely (Geospatial coordinate logic)
- **Frontend Architecture**: JavaScript, Leaflet.js, CSS Glassmorphism
- **Backend Application Layer**: Flask

# 6. SYSTEM ARCHITECTURE

The architecture separates the topological graph creation from constraint execution:
1. **Graph Serialization Layer**: Fetches OpenStreetMap data and stores it in memory as an Adjacency List within a `MultiDiGraph`.
2. **Context Evaluator Layer**: Reads Weather API and Mode States, instantiating the correct class (`CalmMode`, `SafeMode`) via Polymorphism.
3. **Algorithm Execution Layer**: Runs the modified Dijkstra loop (`_smart_edge_path`) mapping state variations.
4. **Coordinate Interpolation Layer**: Projects raw mathematical nodes back into Cartesian GPS strings (`[LAT, LNG]`) sent to the Leaflet UI.

# 7. MODULES DESCRIPTION

- **`app.py`**: The central controller coordinating spatial inputs, invoking the mathematical pathfinding iterations, and managing network payload parsing.
- **`route_modes.py`**: Provides the structural polymorphism for different routing constraints (`get_weight`, `get_turn_penalty`) decoupling pure math from business logic.
- **`safety_zones.py`**: Evaluates coordinate bounding geometry (`shapely.Polygon.intersects()`).
- **`weather_service.py`**: Conditionally scales terrain heuristic multipliers (e.g., avoiding dirt trails if `raining`).

---

# 8. ALGORITHMS USED (MAIN DAA HIGHLIGHT)

## 8.1 Base Graph Representation
We utilize a **Directed Multigraph** ($G = (V, E)$), implemented as an Adjacency Map in memory. Multigraphs are crucial because real-world roads can feature multiple parallel edges between two identical intersections (nodes $u, v$).

## 8.2 Standard Shortest Path (Baseline Comparison)
For the baseline path, standard **Dijkstra's Algorithm** is run with a simplistic scalar weight: `edge['length']`. 
Function invoked: `nx.shortest_path(G, origin, destination, weight="length")`

## 8.3 State-Space Augmented Dijkstra's Algorithm (Core Algorithmic Feat)
Classical Dijkstra computes minimum paths by storing the optimal cost to reach node $U$. However, this is insufficient for real-world navigation because **turning a vehicle or walking across complex intersections carries dynamic penalty costs** based heavily on the trajectory angle.

To solve this, we cannot just visit Node $U$. We must acknowledge *HOW* we arrived at Node $U$.
We expanded the classical algorithm into a **State-Space Search**:
- **State Representation**: $S = (Current\_Node, Previous\_Node, Previous\_Edge\_Key)$
- **Distance Dictionary**: Tracks minimal costs mapped to the tuple $S$ rather than scalar node index.

## 8.4 Greedy Min-Heap (Priority Queue) Implementation
To extract the next optimal traversal state efficiently, Python's `heapq` is utilized, which maintains the Min-Heap property explicitly guaranteeing $O(1)$ lookup for the minimal cost state, and $O(\log N)$ extraction. This is significantly more optimal than traversing linear search arrays during frontier evaluation.

## 8.5 Turn Penalty Heuristic Logic
As a state pops from the Min-Heap, we geometrically calculate the intersection Delta Angle between the incoming traversal and the outgoing edge bearing:
$Penalty = f(abs(outgoing\_bearing - incoming\_bearing))$
For Accessibility mode, sharp turns ($> 55^{\circ}$) inject intense positive scalar weight to dissuade wheelchairs from navigating awkward street corners.

---

# 9. FLOWCHARTS

**State Space Traversal Flow:**
[ START ROUTING ]
    --> Initialize dist[(Origin, NULL, NULL)] = 0
    --> Push to Min-Heap: (cost = 0, Node=Origin)
    --> [ WHILE HEAP NOT EMPTY ] -> Pop lowest cost State S
        --> If S.Node == Destination -> RETURN Path
        --> For Each Outward Edge from S.Node:
            --> Calculate Mode Weight (Weather, Safety)
            --> Calculate Penalty ($Angle\_Delta$)
            --> Total = Cost + Weight + Penalty
            --> If Total < dist[(Next\_Node, S.Node, Key)]:
                --> Update dist[]
                --> Update Parent[] Memory
                --> Push to Heap
    --> Retrace Parent Mapping Hash to Output Route
[ END ]

# 10. PSEUDOCODE

```text
Algorithm Smart_Edge_Path(Graph, Origin, Destination, Mode_Instance):
    Initialize Heap = []
    Initialize Dist = Hash Map
    Initialize Parent = Hash Map
    
    Start_State = (Origin, null, null)
    Dist[Start_State] = 0
    Heap.push((0, Origin, null, null))
    
    While Heap is not Empty:
        (curr_cost, curr_node, prev_node, prev_key) = Heap.pop()
        
        if curr_node == Destination:
            Break Loop
            
        For each (next_node, next_key, edge_data) in Graph.Neighbors(curr_node):
            // Multi-Criteria Heuristic Addition
            edge_weight = Mode_Instance.get_weight(curr_node, next_node, edge_data)
            turn_penalty = calculate_bearing_penalty(prev_node, curr_node, next_node)
            intersection_delay = Mode_Instance.get_intersection_penalty()
            
            step_cost = edge_weight + turn_penalty + intersection_delay
            new_cost = curr_cost + step_cost
            
            next_state = (next_node, curr_node, next_key)
            if new_cost < Dist.get_default(next_state, Infinity):
                Dist[next_state] = new_cost
                Parent[next_state] = (Current_State, edge_data)
                Heap.push((new_cost, next_node, curr_node, next_key))
                
    Return reconstruct_path(Parent, Destination)
```

# 11. TIME & SPACE COMPLEXITY ANALYSIS

## Standard Map Traversal (Shortest ETA)
- **Time Complexity:** $O((V + E) \log V)$
- **Space Complexity:** $O(V)$ (Storage of scalar array mappings for parent arrays)

## Modified State-Space Traversal (StillSpace Core)
- **Time Complexity:** 
  - **Best Case**: $O(K)$, tightly bound if the destination is functionally adjacent or entirely continuous without intersections.
  - **Worst Case**: Because the state space expands from scalar nodes ($V$) to tuples binding incoming edges ($V \times Degree_{num}$), the graph technically acts like an Edge-Graph. 
  - $O((E + E \times D) \log E)$ where $D$ is the maximum out-degree of an intersection. In real-world urban maps, out-degrees correlate to $\sim 4$ maximum (a standard 4-way crossroad), stabilizing runtime remarkably close to $O(E \log E)$.
- **Space Complexity:** $O(E)$ max frontier bound expansion, heavily mitigated by the greedy nature of the Priority Queue naturally culling severe scalar paths ($cost \rightarrow \infty$).

## Why Chosen
This expansion strictly resolves the logical impossibility of capturing dynamic path friction using a standard scalar $O(V \cdot \log V)$ matrix. Without state tracking, crossing penalties and geo-fenced safety intersections cannot be reliably calculated, thus State-Space expansion achieves real-world usability with a mathematically sound time trade-off.

---

# 12. SCREENSHOTS

[ PLACEHOLDER: Insert Screenshot of Dashboard Interface rendering Route Mode selections ]
[ PLACEHOLDER: Insert Screenshot of Route comparison dynamically separating Safe Mode from Baseline Shortest Path metrics ]

# 13. ADVANTAGES

1. **Deterministic Accuracy**: Mathematical superiority in tracking real-world constraints via constraint scaling geometry instead of guessing algorithms.
2. **Modular Adaptability**: $O(1)$ swapping of Route Contexts via Polymorphism dynamically updates constraints without recompiling network node geometry.
3. **Safety Critical Features**: Ability to map criminal danger-zones through Shapely intersection mathematics inherently protects user routing matrices actively.

# 14. LIMITATIONS

1. **State-Space Memory Scaling**: Searching a 100-kilometer cross-state map exponentially inflates the State-Space Min-Heap resulting in Memory Overflows natively inside Python.
2. **Missing Local Elevation Data**: Wheelchair accessibility currently implies road "Type". Hard mathematical incline tracking requires intensive DEM (Digital Elevation Model) cross-referencing which vastly alters API response times.

# 15. FUTURE SCOPE

Integrating native $A^*$ heuristics alongside the expanded Dijkstra logic to bind Euclidean vector scaling over the expanded search frontier, guaranteeing massive structural reductions in Priority Queue insertions. Porting the logic module structure natively into C++ (or Rust compiled binaries) for a 30x processing multiplier scale.

# 16. CONCLUSION

The StillSpace Routing platform proves that strict Academic Algorithmic theories—such as State Space Search constraints and dynamic Min-Heap memory tracking—can directly generate empathetic, usable software for modern mobility constraints. By heavily modifying routing heuristics, the software successfully transforms graph mathematics into an engine optimized for human well-being, accessibility, and safety.

# 17. REFERENCES

1. Cormen, T. H., Leiserson, C. E., Rivest, R. L., & Stein, C. (2009). *Introduction to Algorithms*. MIT press.
2. NetworkX Documentation. *Algorithms - Shortest Paths*. Retrieved from NetworkX library documentation.
3. Boeing, G. (2017). "OSMnx: New methods for acquiring, constructing, analyzing, and visualizing complex street networks." *Computers, Environment and Urban Systems*, 65, 126-139.
