# MAS Simulator Changes Log

This file records all architectural and logic changes implemented in the Runtime Trust Graph Containment Framework to extend department collaboration, run before/after evaluations, track comparative containment metrics, and build a reproducible large-scale experimental pipeline.

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
- **Configuration**: Implemented reading from [experiment_config.json](file:///c:/PDocuments/ccbd/langchain%20internals/langgraph-fvs-test/experiment_config.json) to set number of runs, seed, rotation, and size parameter.
- **Fixed Prompt Dataset**: Integrates loading prompts dynamically from [enterprise_prompts.csv](file:///c:/PDocuments/ccbd/langchain%20internals/langgraph-fvs-test/datasets/enterprise_prompts.csv), running them in a reproducible sequence.
- **Systematic Rotation**: Rotates the compromised node deterministically among active nodes across cycles of the prompt list.
- **Execution Time**: Added timing calculations measuring elapsed time per run in seconds.

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

## 5. Publication-Quality Figures
- **File**: [experiment_runner.py](file:///c:/PDocuments/ccbd/langchain%20internals/langgraph-fvs-test/experiment_runner.py)
- **Change**: Automatically creates and outputs five charts under `figures/`:
  - `runtime_tau_histogram.png`
  - `containment_efficiency_histogram.png`
  - `k_before_after_boxplot.png`
  - `runtime_tau_vs_messages.png`
  - `runtime_tau_vs_kbefore.png`
