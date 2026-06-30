# MAS Simulator Changes Log

This file records all architectural and logic changes implemented in the Runtime Trust Graph Containment Framework to extend department collaboration, run before/after evaluations, track comparative containment metrics, build a reproducible large-scale experimental pipeline, and support publication-quality visualization.

---

## 1. Role-Based Runtime Graph Construction
- **File**: [enterprise_topology.py](file:///c:/PDocuments/ccbd/langchain%20internals/langgraph-fvs-test/enterprise_topology.py)
- **Change**: Replaced static entrypoint edges with dynamic internal collaboration modeling.
- **Shortcutting Algorithm**: Implemented `contract_department_graph(dept, active_nodes)`. Starting with the department's full internal topology, it shortcuts inactive nodes (`u -> v -> w` becomes `u -> w`) and removes them, generating the active collaboration and review loops dynamically.
- **Integration**: Integrated `contract_department_graph` directly inside `build_enterprise_runtime_trust_graph`.

---

## 2. Before/After Containment Evaluation
- **File**: [experiment_runner.py](file:///c:/PDocuments/ccbd/langchain%20internals/langgraph-fvs-test/experiment_runner.py)
- **Change**: Integrated two separate compromise propagation runs for every scenario.
- **BFS Depth Propagation**: Implemented `propagate_compromise_depth(graph, compromised_node)` which performs BFS and calculates the maximum propagation depth (hops from the source) in linear time.
- **Comparative Execution**: Runs BFS on the initial graph, removes the calculated FVS set, runs BFS on the revoked graph, and compares outcomes.

---

## 3. Large-Scale Experimental Pipeline
- **File**: [experiment_runner.py](file:///c:/PDocuments/ccbd/langchain%20internals/langgraph-fvs-test/experiment_runner.py)
- **Change**: Scaled up to **200 runs** to fully cover the new unquoted CSV dataset `datasets/enterprise_prompts.csv` using a custom robust parsing routine `load_enterprise_prompts`. deterministic rotation and performance measurements are integrated.

---

## 4. Automated Statistical Summary Reports
- **File**: [experiment_runner.py](file:///c:/PDocuments/ccbd/langchain%20internals/langgraph-fvs-test/experiment_runner.py)
- **Change**: Added automated generation of 5 statistical report CSVs directly under the experiment folder:
  - `summary_statistics.csv`
  - `runtime_tau_distribution.csv`
  - `summary_by_workflow.csv`
  - `summary_by_compromise.csv`
  - `summary_by_size.csv`

---

## 5. Separated Visualization and Numerical Summaries
- **File**: [experiment_runner.py](file:///c:/PDocuments/ccbd/langchain%20internals/langgraph-fvs-test/experiment_runner.py)
- **Graph Cleanliness**: Removed all statistics/info box overlays from `save_trace_graph` and `save_before_after_comparison` figures to ensure graph layouts remain clean and uncluttered.
- **Clean Subplot Titles**: Renamed titles in the 4-panel theorem flow to:
  - `(a) Runtime Trust Graph`
  - `(b) SCC & Feedback Cycles`
  - `(c) Before Containment`
  - `(d) After FVS Containment`
- **Standalone Executive Summary Table Figures**:
  - Implemented `save_run_summary_table` to render a separate publication-quality summary table for every run.
  - The table cleanly summarizes 14 metrics: *Run ID, Workflow, Compromised Agent, Runtime τ_FVS, FVS Size, Active Agents, Active Edges, SCC Count, Largest SCC Size, Infected Before, Infected After, Containment Efficiency, Propagation Depth (Before -> After), and Graph Hash*.
  - Alternating light-grey row backgrounds and navy header colors are applied for premium legibility.
  - Exports each summary table as both **600 DPI PNG** and **vector PDF**.
