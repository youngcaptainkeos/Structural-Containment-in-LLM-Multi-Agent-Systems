# README - Runtime FVS Formal Verification Replication Guide

This guide documents the environment, parameters, and procedure required to reproduce the formal verification results for the Runtime FVS (Runtime Feedback Vertex Set) Containment Protocol model.

## Environment Details
- **Java VM**: OpenJDK Runtime Environment Temurin-25.0.3+9 (LTS) or higher
- **TLC Model Checker**: TLC2 Version 2026.05.26.235334 (rev: 4ba7d88)
- **Java Classpath**: `specs/tla2tools.jar`
- **Execution Script Runtime**: Python 3.x with standard library

---

## Replication Procedure

### 1. Automated Verification (Recommended)
To run Protocol Verification across all Representative Topology abstractions (Topologies A, B, C, and D), compile the statistics, and generate the summary reports, run the automated experiment script from the project root:

```bash
python specs/run_tlc_experiments.py
```

This will automatically rewrite `specs/RuntimeFVS.cfg` for each topology, execute TLC, parse the outputs, and generate the following reports:
- `formal_verification_results.csv` (CSV format)
- `formal_verification_summary.md` (Markdown format)

### 2. Manual Verification (Single Run)
To manually model check a specific configuration, navigate to the `specs/` directory, update `RuntimeFVS.cfg` as needed, and execute TLC:

```bash
cd specs
java -cp tla2tools.jar tlc2.TLC RuntimeFVS.tla
```

---

## Observed Model Checking Statistics

| Topology | Agents Set | Boundary Set | Distinct States | Diameter | Result |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Topology A** | `{"A", "B", "C", "D"}` | `{"D"}` | 21 | 8 | Success, no violations |
| **Topology B** | `{"A", ... "F"}` | `{"F"}` | 55 | 10 | Success, no violations |
| **Topology C** | `{"A", ... "H"}` | `{"H"}` | 98 | 11 | Success, no violations |
| **Topology D** | `{"A", ... "J"}` | `{"J"}` | 225 | 14 | Success, no violations |

---

## Model Parameters & Topology Abstractions
- **`Spec`**: Defined as `Init /\ [][Next]_vars /\ WF_vars(Next)`. Weak fairness is required to satisfy temporal liveness properties.
- **`TopologyType`**: Configured as `"A"`, `"B"`, `"C"`, or `"D"`. Conditionally constructs the target graphs in `Init`.
- **`Tau`**: Symbolic FVS size budget. Set to `1` for Topology A and `2` for Topologies B, C, and D.
- **Topologies**:
  - **Topology A**: Single cyclic Runtime SCC (Tau = 1), representing the basic feedback configuration.
  - **Topology B**: Two cyclic Runtime SCCs connected through a bridge (Tau = 2), showing containment across disjoint cyclic loops.
  - **Topology C**: Nested Runtime SCC configuration (Tau = 2), representing hierarchical feedback dependencies.
  - **Topology D**: Cross-linked department cyclic workflows (Tau = 2), demonstrating containment in complex cyclic networks.
