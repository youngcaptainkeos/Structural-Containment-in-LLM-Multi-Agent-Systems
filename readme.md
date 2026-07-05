# Runtime Feedback Vertex Set (Runtime FVS) Containment for Enterprise Multi-Agent Systems

Official implementation, experimental artifacts, and formal verification accompanying the paper:

> **Structural Containment in LLM Multi-Agent Systems: Detection Is Behavioral. Containment Is Structural**

---

# Overview

Large Language Model (LLM) Multi-Agent Systems (MAS) increasingly coordinate enterprise workflows through dynamic communication between specialized agents. While existing approaches primarily focus on detecting compromised agents through behavioral monitoring, this repository investigates a complementary question:

> **How can compromise propagation be structurally contained once malicious behavior has already been detected?**

This repository implements the **Runtime Feedback Vertex Set (Runtime FVS)** containment framework, a graph-theoretic approach that computes containment actions directly from the runtime communication topology rather than relying on behavioral heuristics.

The repository contains both

- the complete empirical evaluation framework,
- and the formal TLA+ verification of the Runtime FVS protocol.

---

# Repository Contents

```
.
├── langgraph-fvs-test/
│   ├── experiment_runner.py
│   ├── enterprise_topology.py
│   ├── enterprise_prompts.py
│   ├── fvs_analysis.py
│   ├── datasets/
│   └── experiment sample data/
│
├── tla/
│   ├── specs/
│   │     RuntimeFVS.tla
│   │     RuntimeFVS.cfg
│   │     run_tlc_experiments.py
│   │
│   ├── results/
│   │     formal_verification_results.csv
│   │     formal_verification_summary.md
│   │
│   └── README.md
│
├── paper/
│
├── LICENSE
└── README.md
```

---

# Repository Components

## 1. Empirical Runtime Containment Framework

Directory

```
langgraph-fvs-test/
```

This component implements the complete enterprise simulator used throughout the paper.

The simulator constructs dynamic runtime trust graphs from enterprise workflows, injects compromise into runtime agents, executes multiple containment strategies, and evaluates containment effectiveness under identical experimental conditions.

Major capabilities include

- Dynamic runtime trust graph generation
- Enterprise workflow simulation
- Runtime SCC extraction
- Runtime Feedback Vertex Set computation
- Compromise propagation simulation
- Statistical evaluation
- Publication-quality visualization generation

---

## 2. Formal Verification

Directory

```
tla/
```

The repository also contains a complete formal specification of the Runtime FVS protocol using **TLA+** and the **TLC Model Checker**.

The specification models the protocol independently from the simulator implementation and exhaustively verifies protocol correctness across representative runtime trust graph topologies.

The verified protocol consists of five stages:

```
Build
   ↓
Propagate
   ↓
Contain
   ↓
Verify
   ↓
Finished
```

Safety and temporal properties including containment, termination, runtime cycle breaking, and boundary isolation are exhaustively model checked.

---

# Runtime FVS Pipeline

The overall containment workflow implemented by this repository is

```
Enterprise Workflow
          │
          ▼
Runtime Trust Graph Construction
          │
          ▼
Strongly Connected Component Detection
          │
          ▼
Runtime Feedback Vertex Set Computation
          │
          ▼
Selective Runtime Revocation
          │
          ▼
Compromise Containment Evaluation
```

---

# Experimental Evaluation

The empirical evaluation compares Runtime FVS against multiple containment baselines.

The implemented baselines include

- No Containment
- Random Revocation
- Degree Centrality
- Betweenness Centrality
- PageRank
- Supervisor Only
- Department Isolation
- Static FVS
- Oracle (Perfect Detection)
- Runtime FVS (proposed)

The evaluation reports

- Containment Ratio
- Compromise Footprint
- Propagation Depth
- Revocation Cost
- Runtime
- Message Reduction
- Pareto Trade-off Analysis
- SCC Structural Analysis
- Statistical Significance
- Confidence Intervals
- Effect Sizes

---

# Formal Verification

The TLA+ specification verifies representative Runtime FVS protocol configurations.

Verified protocol properties include

- Type Safety
- Runtime FVS Correctness
- Boundary Isolation
- Runtime Cycle Breaking
- Revocation Correctness
- Containment Safety
- Eventual Containment
- Protocol Termination
- Phase Ordering
- Monotonic Compromise Propagation

Verification is performed over multiple representative enterprise trust graph topologies of increasing structural complexity.

---

# Running the Empirical Evaluation

Install dependencies

```bash
pip install -r langgraph-fvs-test/requirements.txt
```

Execute the simulator

```bash
cd langgraph-fvs-test

python experiment_runner.py
```

Experimental outputs include

- CSV summaries
- Statistical reports
- Publication-ready figures
- Significance analyses

---

# Running the Formal Verification

Navigate to

```bash
cd tla/specs
```

Run automated verification

```bash
python run_tlc_experiments.py
```

or execute TLC manually

```bash
java -cp tla2tools.jar tlc2.TLC RuntimeFVS.tla
```

Generated outputs include

```
formal_verification_results.csv

formal_verification_summary.md
```

---

# Reproducing the Paper

The repository reproduces both the empirical and formal verification components presented in the accompanying paper.

To reproduce the complete artifact:

1. Execute the empirical simulator.
2. Generate experimental figures and statistical analyses.
3. Execute the TLA+ verification suite.
4. Compare the generated outputs with the paper's reported tables and figures.

---

# Citation

If you use this repository in academic work, please cite:

```
@article{runtimefvs2026,
  title={Structural Containment in LLM Multi-Agent Systems: Detection Is Behavioral. Containment Is Structural},
  author={...},
  journal={Under Review},
  year={2026}
}
```

---

# License

This repository is released under the MIT License.